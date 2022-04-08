"""Define how Speedwagon starts up on the current system.

Use for loading and starting up the main application

Changes:
++++++++

    .. versionadded:: 0.1.4
       added a splash screen for logo

"""
import abc
import argparse
import collections
import contextlib
import io
import json
import logging
import os
import queue
import sys
import threading
import time
import typing
from typing import Dict, Union, Iterator, Tuple, List, cast, Optional, Type

try:
    from typing import Final
except ImportError:
    from typing_extensions import Final  # type: ignore

import webbrowser
import yaml

from PySide6 import QtWidgets  # type: ignore
import speedwagon.frontend.qtwidgets.runners
from speedwagon.frontend import qtwidgets
import speedwagon
import speedwagon.config
import speedwagon.exceptions
from speedwagon import worker, job, runner_strategies

try:  # pragma: no cover
    from importlib import metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore

__all__ = [
    "ApplicationLauncher",
    "FileFormatError",
    "SingleWorkflowLauncher",
    "SingleWorkflowJSON",
    "standalone_tab_editor",
]

CONFIG_INI_FILE_NAME: Final[str] = "config.ini"
TABS_YML_FILE_NAME:  Final[str] = "tabs.yml"


class FileFormatError(Exception):
    """Exception is thrown when Something wrong with the contents of a file."""


def parse_args() -> argparse.ArgumentParser:
    """Parse command line arguments."""
    return speedwagon.config.CliArgsSetter.get_arg_parser()


class CustomTabsFileReader:
    """Reads the tab file data."""

    def __init__(
            self, all_workflows: Dict[str, Type[speedwagon.Workflow]]) -> None:
        """Load all workflows supported.

        Args:
            all_workflows:
        """
        self.all_workflows = all_workflows

    @staticmethod
    def read_yml_file(yaml_file: str) -> Dict[str,  List[str]]:
        """Read the contents of the yml file."""
        with open(yaml_file, encoding="utf-8") as file_handler:
            tabs_config_data = yaml.load(file_handler.read(),
                                         Loader=yaml.SafeLoader)

        if not isinstance(tabs_config_data, dict):
            raise FileFormatError("Failed to parse file")
        return tabs_config_data

    def _get_tab_items(self,
                       tab: List[str],
                       tab_name: str) -> Dict[str, Type[job.Workflow]]:
        new_tab_items = {}
        for item_name in tab:
            try:
                workflow = self.all_workflows[item_name]
                if workflow.active is False:
                    print("workflow not active")
                new_tab_items[item_name] = workflow

            except LookupError:
                print(
                    f"Unable to load '{item_name}' in "
                    f"tab {tab_name}", file=sys.stderr)
        return new_tab_items

    def load_custom_tabs(self, yaml_file: str) -> Iterator[Tuple[str, dict]]:
        """Get custom tabs data from config yaml.

        Args:
            yaml_file: file path to a yaml file containing custom.

        Yields:
            Yields a tuple containing the name of the tab and the containing
                workflows.
        Notes:
            Failure to load will only a print message to standard error.

        """
        try:
            tabs_config_data = self.read_yml_file(yaml_file)
            if tabs_config_data:
                tabs_config_data = cast(Dict[str, List[str]], tabs_config_data)
                for tab_name in tabs_config_data:
                    try:
                        new_tab = tabs_config_data.get(tab_name)
                        if new_tab is not None:
                            yield tab_name, \
                                  self._get_tab_items(new_tab, tab_name)

                    except TypeError as tab_error:
                        print(
                            f"Error loading tab '{tab_name}'. "
                            f"Reason: {tab_error}",
                            file=sys.stderr
                        )
                        continue

        except FileNotFoundError as error:
            print(
                f"Custom tabs file not found. Reason: {error}",
                file=sys.stderr
            )
        except AttributeError as error:
            print(
                f"Custom tabs file failed to load. Reason: {error}",
                file=sys.stderr
            )

        except yaml.YAMLError as error:
            print(
                f"{yaml_file} file failed to load. Reason: {error}",
                file=sys.stderr
            )


def get_custom_tabs(
        all_workflows: Dict[str, Type[speedwagon.Workflow]],
        yaml_file: str
) -> Iterator[Tuple[str, dict]]:
    """Load custom tab yaml file."""
    getter = CustomTabsFileReader(all_workflows)
    yield from getter.load_custom_tabs(yaml_file)


class AbsStarter(metaclass=abc.ABCMeta):
    config_file: str
    tabs_file: str
    user_data_dir: str
    app_data_dir: str

    @abc.abstractmethod
    def run(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        """Run the application."""

    def initialize(self) -> None:
        """Initialize startup routine."""


class StartupDefault(AbsStarter):
    """Default startup.

    .. versionadded:: 0.2.0
       Added StartupDefault class for speedwagon with the normal Qt-based GUI.
    """

    def __init__(self, app: QtWidgets.QApplication = None) -> None:
        """Create a new default startup routine."""
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.DEBUG)

        self.handler = logging.StreamHandler(stream=sys.stderr)
        self.handler.setLevel(logging.DEBUG)
        self.platform_settings = speedwagon.config.get_platform_settings()

        self.config_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            CONFIG_INI_FILE_NAME
        )

        self.tabs_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            TABS_YML_FILE_NAME
        )

        # Make sure required directories exists
        self.user_data_dir = typing.cast(
            str, self.platform_settings.get("user_data_directory")
        )

        self.startup_settings: Dict[str, Union[str, bool]] = {}
        self._debug = False

        self.app_data_dir = typing.cast(
            str, self.platform_settings.get("app_data_directory")
        )
        self.app = app or QtWidgets.QApplication(sys.argv)

    def initialize(self) -> None:
        self.ensure_settings_files()
        self.resolve_settings()

    def run(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        # Display a splash screen until the app is loaded
        splash = qtwidgets.splashscreen.create_splash()
        splash_message_handler = \
            qtwidgets.logging_helpers.SplashScreenLogHandler(splash)

        # If debug mode, print the log messages directly on the splash screen
        if self._debug:
            splash_message_handler.setLevel(logging.DEBUG)
        else:
            splash_message_handler.setLevel(logging.INFO)

        splash.show()
        QtWidgets.QApplication.processEvents()

        qtwidgets.gui.set_app_display_metadata(self.app)

        with worker.ToolJobManager() as work_manager:

            work_manager.settings_path = \
                self.platform_settings.get_app_data_directory()

            windows = qtwidgets.gui.MainWindow1(
                work_manager=work_manager,
                debug=cast(bool, self.startup_settings['debug'])
            )

            windows.setWindowTitle("")
            self._logger.addHandler(splash_message_handler)

            self._logger.addHandler(windows.log_data_handler)
            self._logger.addHandler(windows.console_log_handler)

            app_title = speedwagon.__name__.title()
            try:
                app_version = metadata.version(__package__)
            except metadata.PackageNotFoundError:
                app_version = ""

            self._logger.info("%s %s", app_title, app_version)

            QtWidgets.QApplication.processEvents()

            self.load_configurations(work_manager)
            self._load_workflows(windows)

            self._logger.debug("Loading User Interface")

            windows.show()

            if "starting-tab" in self.startup_settings:
                windows.set_current_tab(
                    tab_name=cast(str, self.startup_settings['starting-tab']))

            splash.finish(windows)

            self._logger.info("Ready")
            self._logger.removeHandler(windows.log_data_handler)
            self._logger.removeHandler(windows.console_log_handler)
            self._logger.removeHandler(splash_message_handler)
            return self.app.exec_()

    def load_configurations(self,
                            work_manager: "worker.ToolJobManager") -> None:

        self._logger.debug("Applying settings to Speedwagon")
        work_manager.user_settings = self.platform_settings
        work_manager.configuration_file = self.config_file

    def _load_workflows(
            self,
            application: qtwidgets.gui.MainWindow1
    ) -> None:
        self._logger.debug("Loading Workflows")
        loading_workflows_stream = io.StringIO()
        with contextlib.redirect_stderr(loading_workflows_stream):
            all_workflows = job.available_workflows()
        # Load every user configured tab
        tabs_file_size = os.path.getsize(self.tabs_file)
        if tabs_file_size > 0:
            try:
                for tab_name, extra_tab in \
                        get_custom_tabs(all_workflows, self.tabs_file):
                    application.add_tab(tab_name, collections.OrderedDict(
                        sorted(extra_tab.items())))
            except FileFormatError as error:
                self._logger.warning(
                    "Unable to load custom tabs from %s. Reason: %s",
                    self.tabs_file,
                    error
                )
        # All Workflows tab
        self._logger.debug("Loading Tab All")
        application.add_tab("All", collections.OrderedDict(
            sorted(all_workflows.items())))
        workflow_errors_msg = loading_workflows_stream.getvalue().strip()
        if workflow_errors_msg:
            for line in workflow_errors_msg.split("\n"):
                self._logger.warning(line)

    def resolve_settings(
            self,
            resolution_strategy_order: Optional[List[
                speedwagon.config.AbsSetting]
            ] = None,
            loader: typing.Optional[speedwagon.config.ConfigLoader] = None
    ) -> None:
        loader = loader or speedwagon.config.ConfigLoader(self.config_file)

        self.platform_settings._data.update(
            loader.read_settings_file(self.config_file)
        )
        loader.logger = self._logger
        if resolution_strategy_order:
            loader.resolution_strategy_order = resolution_strategy_order
        results = loader.get_settings()

        self.startup_settings = results
        self._debug = self._get_debug(results)

    def _get_debug(self, settings) -> bool:
        try:
            debug = cast(bool, settings['debug'])
        except KeyError:
            self._logger.warning(
                "Unable to find a key for debug mode. Setting false")

            debug = False
        return bool(debug)

    def ensure_settings_files(self) -> None:
        speedwagon.config.ensure_settings_files(self, self._logger)


class StartQtThreaded(AbsStarter):

    def __init__(self, app: QtWidgets.QApplication = None) -> None:
        self.startup_settings: Dict[str, Union[str, bool]] = {
            'debug': False
        }

        self.windows: Optional[
            qtwidgets.gui.MainWindow2
        ] = None
        self.logger = logging.getLogger()

        formatter = logging.Formatter(
            '%(asctime)-15s %(threadName)s %(message)s'
        )

        self.platform_settings = speedwagon.config.get_platform_settings()
        self.app = app or QtWidgets.QApplication(sys.argv)
        self._log_data = io.StringIO()

        log_data_handler = logging.StreamHandler(self._log_data)
        log_data_handler.setLevel(logging.DEBUG)
        log_data_handler.setFormatter(formatter)

        self.logger.addHandler(log_data_handler)
        self.logger.setLevel(logging.DEBUG)

        self.load_settings()
        qtwidgets.gui.set_app_display_metadata(self.app)
        self._request_window = \
            qtwidgets.user_interaction.QtRequestMoreInfo(self.windows)

    @staticmethod
    def import_workflow_config(
            parent: qtwidgets.gui.MainWindow2,
            dialog_box: typing.Optional[QtWidgets.QFileDialog] = None,
            serialization_strategy: typing.Optional[
                job.AbsJobConfigSerializationStrategy
            ] = None
    ) -> None:
        serialization_strategy = \
            serialization_strategy or job.ConfigJSONSerialize()

        dialog_box = dialog_box or QtWidgets.QFileDialog()
        load_file, _ = dialog_box.getOpenFileName(
            parent,
            "Import Job Configuration",
            "",
            "Job Configuration JSON (*.json);;All Files (*)"
        )

        if load_file == "":
            # Return if cancelled
            return

        serialization_strategy.file_name = load_file
        workflow_name, data = serialization_strategy.load()
        parent.logger.debug(f"Loading {workflow_name}")
        parent.set_current_tab("All")
        parent.set_active_workflow(workflow_name)
        parent.set_current_workflow_settings(data)

    @staticmethod
    def save_workflow_config(
            workflow_name,
            data,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            dialog_box: typing.Optional[QtWidgets.QFileDialog] = None,
            serialization_strategy: typing.Optional[
                job.AbsJobConfigSerializationStrategy
            ] = None
    ) -> None:
        serialization_strategy = \
            serialization_strategy or job.ConfigJSONSerialize()

        dialog_box = dialog_box or QtWidgets.QFileDialog()
        export_file_name, _ = dialog_box.getSaveFileName(
                parent,
                "Export Job Configuration",
                f"{workflow_name}.json",
                "Job Configuration JSON (*.json)"
        )

        if export_file_name:
            serialization_strategy.file_name = export_file_name
            serialization_strategy.save(workflow_name, data)

    def load_settings(self) -> None:
        self.user_data_dir = typing.cast(
            str, self.platform_settings.get("user_data_directory")
        )

        self.config_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            CONFIG_INI_FILE_NAME
        )

        self.app_data_dir = typing.cast(
            str, self.platform_settings["app_data_directory"]
        )

        self.tabs_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            TABS_YML_FILE_NAME
        )

    def _load_help(self) -> None:
        try:
            pkg_metadata = dict(metadata.metadata(speedwagon.__name__))
            webbrowser.open_new(pkg_metadata['Home-page'])
        except metadata.PackageNotFoundError as error:
            self.logger.warning(
                "No help link available. Reason: %s", error)

    def ensure_settings_files(self) -> None:
        speedwagon.config.ensure_settings_files(
            self,
            logger=self.logger
        )

    @staticmethod
    def read_settings_file(
            settings_file: str
    ) -> Dict[str, Union[str, bool]]:

        with speedwagon.config.ConfigManager(settings_file) as config:
            return config.global_settings

    def resolve_settings(
            self,
            resolution_strategy_order: Optional[
                List[speedwagon.config.AbsSetting]
            ] = None,
            loader: speedwagon.config.ConfigLoader = None
    ) -> Dict[str, Union[str, bool]]:

        loader = loader or speedwagon.config.ConfigLoader(self.config_file)

        self.platform_settings._data.update(
            loader.read_settings_file(self.config_file)
        )

        loader.logger = self.logger
        if resolution_strategy_order:
            loader.resolution_strategy_order = resolution_strategy_order

        results = loader.get_settings()

        self.startup_settings = results
        return self.startup_settings

    def initialize(self) -> None:
        self.ensure_settings_files()
        self.startup_settings = self.resolve_settings()

    def _load_workflows(
            self,
            application: qtwidgets.gui.MainWindow2
    ) -> None:
        tabs_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            TABS_YML_FILE_NAME
        )

        self.logger.debug("Loading Workflows")
        loading_workflows_stream = io.StringIO()
        with contextlib.redirect_stderr(loading_workflows_stream):
            all_workflows = job.available_workflows()

        for workflow_name, error in \
                self._find_invalid(all_workflows):
            error_message = \
                f"Unable to load workflow '{workflow_name}'. Reason: {error}"

            self.logger.error(error_message)
            application.console.add_message(error_message)
            del all_workflows[workflow_name]

        # Load every user configured tab
        self.load_custom_tabs(application, tabs_file, all_workflows)

        # All Workflows tab
        self.load_all_workflows_tab(application, all_workflows)

        workflow_errors_msg = loading_workflows_stream.getvalue().strip()
        if workflow_errors_msg:
            for line in workflow_errors_msg.split("\n"):
                self.logger.warning(line)

    def load_all_workflows_tab(
            self,
            application: qtwidgets.gui.MainWindow2,
            loaded_workflows: typing.Dict[str, Type[speedwagon.Workflow]]
    ) -> None:
        self.logger.debug("Loading Tab All")
        application.add_tab(
            "All",
            collections.OrderedDict(
                sorted(loaded_workflows.items())
            )
        )

    def load_custom_tabs(
            self,
            main_window: qtwidgets.gui.MainWindow2,
            tabs_file: str,
            loaded_workflows: typing.Dict[str, Type[speedwagon.Workflow]]
    ) -> None:
        tabs_file_size = os.path.getsize(tabs_file)
        if tabs_file_size > 0:
            try:
                for tab_name, extra_tab in \
                        get_custom_tabs(loaded_workflows, tabs_file):
                    main_window.add_tab(tab_name, collections.OrderedDict(
                        sorted(extra_tab.items())))
            except FileFormatError as error:
                self.logger.warning(
                    "Unable to load custom tabs from %s. Reason: %s",
                    tabs_file,
                    error
                )

    def save_log(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        data = self._log_data.getvalue()
        epoch_in_minutes = int(time.time() / 60)
        while True:
            log_file_name, _ = \
                QtWidgets.QFileDialog.getSaveFileName(
                    parent,
                    "Export Log",
                    f"speedwagon_log_{epoch_in_minutes}.txt",
                    "Text Files (*.txt)")

            if not log_file_name:
                return
            try:
                with open(log_file_name, "w", encoding="utf-8") as file_handle:
                    file_handle.write(data)
            except OSError as error:
                message_box = QtWidgets.QMessageBox(parent)
                message_box.setText("Saving Log Failed")
                message_box.setDetailedText(str(error))
                message_box.exec_()
                continue

            self.logger.info("Saved log to %s", log_file_name)
            break

    @staticmethod
    def request_system_info(
            parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        qtwidgets.dialog.dialogs.SystemInfoDialog(parent).exec()

    @staticmethod
    def request_settings(parent: QtWidgets.QWidget = None) -> None:
        platform_settings = speedwagon.config.get_platform_settings()
        settings_path = platform_settings.get_app_data_directory()

        dialog_builder = \
            qtwidgets.dialog.settings.SettingsBuilder(parent=parent)

        dialog_builder.add_open_settings(
            platform_settings.get_app_data_directory()
        )

        dialog_builder.add_global_settings(
            os.path.join(settings_path, CONFIG_INI_FILE_NAME)
        )

        dialog_builder.add_tabs_setting(
            os.path.join(settings_path, TABS_YML_FILE_NAME)
        )

        config_dialog = dialog_builder.build()
        config_dialog.exec_()

    def run(self, app: Optional[QtWidgets.QApplication] = None) -> int:

        with runner_strategies.BackgroundJobManager() as job_manager:
            job_manager.global_settings = self.startup_settings
            self.windows = qtwidgets.gui.MainWindow2(
                job_manager=job_manager,
                settings=self.startup_settings
            )

            if self.windows is None:
                return 1

            self.windows.console.attach_logger(self.logger)
            self.windows.configuration_requested.connect(
                self.request_settings
            )

            self.windows.save_logs_requested.connect(self.save_log)

            self.windows.export_job_config.connect(
                self.save_workflow_config
            )

            self.windows.import_job_config.connect(
                self.import_workflow_config
            )

            self.windows.system_info_requested.connect(
                self.request_system_info
            )
            self.windows.help_requested.connect(self._load_help)
            self.windows.submit_job.connect(
                lambda workflow_name, options:
                self.submit_job(
                    job_manager,
                    workflow_name,
                    options,
                    main_app=self.windows,
                )
            )

            self._load_workflows(self.windows)
            self.windows.show()
            return self.app.exec_()

    @staticmethod
    def abort_job(
            dialog: qtwidgets.dialog.dialogs.WorkflowProgress,
            events: runner_strategies.AbsEvents
    ) -> None:
        dialog.stop()
        events.stop()

    def request_more_info(
            self,
            workflow: speedwagon.Workflow,
            options: Dict[str, typing.Any],
            pre_results: List[typing.Any],
            wait_condition: Optional[threading.Condition] = None
    ) -> Optional[Dict[str, typing.Any]]:
        self._request_window.exc = None
        waiter = wait_condition or threading.Condition()
        with waiter:
            self._request_window.request.emit(
                waiter,
                workflow,
                options,
                pre_results
            )
            waiter.wait()
        if self._request_window.exc is not None:
            raise self._request_window.exc
        return self._request_window.results

    def submit_job(
            self,
            job_manager: runner_strategies.BackgroundJobManager,
            workflow_name: str,
            options: Dict[str, typing.Any],
            main_app: typing.Optional[
                qtwidgets.gui.MainWindow2] = None,
    ) -> None:

        workflow_class = \
            job.available_workflows().get(workflow_name)
        try:
            if workflow_class is None:
                raise ValueError(f"Unknown workflow: '{workflow_name}'")
            workflow_class.validate_user_options(**options)
        except ValueError as user_option_error:
            self.report_exception(
                parent=main_app,
                exc=user_option_error,
                dialog_box_title="Invalid User Options"
            )
            return

        dialog_box = \
            qtwidgets.dialog.dialogs.WorkflowProgress(parent=self.windows)

        if main_app is not None:
            # pylint: disable=no-member
            dialog_box.rejected.connect(main_app.close)

        dialog_box.setWindowTitle(workflow_name)
        dialog_box.show()
        threaded_events = runner_strategies.ThreadedEvents()

        dialog_box.aborted.connect(
            lambda: self.abort_job(dialog_box, threaded_events)
        )
        callbacks = qtwidgets.runners.WorkflowProgressCallbacks(dialog_box)
        if main_app is not None:
            callbacks.signals.finished.connect(
                main_app.console.log_handler.flush
            )

        dialog_box.attach_logger(self.logger)
        setattr(job_manager, "request_more_info", self.request_more_info)
        job_manager.submit_job(
            workflow_name=workflow_name,
            options=options,
            app=self,
            liaison=runner_strategies.JobManagerLiaison(
                callbacks=callbacks,
                events=threaded_events
            )
        )
        threaded_events.started.set()

    def report_exception(
            self,
            exc: BaseException,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            dialog_box_title: Optional[str] = None,
    ) -> None:
        self.logger.error(str(exc))
        report_exception_dialog(exc, dialog_box_title, parent)

    def _find_invalid(
            self,
            workflows: typing.Dict[str, typing.Type[speedwagon.Workflow]]
    ) -> typing.Iterable[
            typing.Tuple[str, str]
    ]:
        for title, workflow in workflows.copy().items():
            try:
                workflow(global_settings=self.startup_settings)
            except (
                    speedwagon.exceptions.SpeedwagonException,
                    AttributeError
            ) as error:
                yield title, str(error)


class SingleWorkflowLauncher(AbsStarter):
    """Single workflow launcher.

    .. versionadded:: 0.2.0
       Added SingleWorkflowLauncher class for running a single workflow \
            without user interaction. Useful for building new workflows.

    """

    def __init__(self, logger: typing.Optional[logging.Logger] = None) -> None:
        """Set up window for running a single workflow."""
        super().__init__()
        self.window: Optional[
            qtwidgets.gui.MainWindow1
        ] = None
        self._active_workflow: Optional[job.AbsWorkflow] = None
        self.options: Dict[str, Union[str, bool]] = {}
        self.logger = logger or logging.getLogger(__name__)

    def run(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        """Run the workflow configured with the options given."""
        if self._active_workflow is None:
            raise AttributeError("Workflow has not been set")

        with worker.ToolJobManager() as work_manager:
            work_manager.logger = self.logger
            self._run(work_manager)
        return 0

    def _run(self, work_manager: worker.ToolJobManager) -> None:
        if self._active_workflow is None:
            raise ValueError("No active workflow set")

        window = qtwidgets.gui.MainWindow1(
            work_manager=work_manager,
            debug=False)

        window.show()
        if self._active_workflow.name is not None:
            window.setWindowTitle(self._active_workflow.name)
        runner_strategy = qtwidgets.runners.QtRunner(window)

        self._active_workflow.validate_user_options(**self.options)
        # runner_strategy.additional_info_callback

        runner_strategy.run(self._active_workflow,
                            self.options,
                            window.log_manager)
        window.log_manager.handlers.clear()
        window.close()

    def set_workflow(self, workflow: job.AbsWorkflow) -> None:
        """Set the current workflow."""
        self._active_workflow = workflow


def report_exception_dialog(exc, dialog_box_title, parent):
    text = str(exc)
    dialog_box = QtWidgets.QMessageBox(parent)
    if dialog_box_title is not None:
        dialog_box.setWindowTitle(dialog_box_title)
    dialog_box.setText(text)
    dialog_box.exec_()


class SingleWorkflowJSON(AbsStarter):
    """Start up class for loading instructions from a JSON file.

    .. versionadded:: 0.2.0
        SingleWorkflowJSON class added

    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """Create a environment where the workflow is loaded from a json file.

        Args:
            logger: Optional Logger, defaults to default logger for __name__.
        """
        super().__init__()
        self.global_settings = None
        self.on_exit: typing.Optional[
            typing.Callable[
                [qtwidgets.gui.MainWindow2], None]
        ] = None
        self.options: typing.Optional[typing.Dict[str, typing.Any]] = None
        self.workflow: typing.Optional[job.AbsWorkflow] = None
        self.logger = logger or logging.getLogger(__name__)

    def load_json_string(self, data: str) -> None:
        """Load json data containing options and workflow info.

        Args:
            data: JSON data as a string.

        """
        loaded_data = json.loads(data)
        self.options = loaded_data['Configuration']
        self._set_workflow(loaded_data['Workflow'])

    def load(self, file_pointer: io.TextIOBase) -> None:
        """Load the information from the json.

        Args:
            file_pointer: File pointer to json file

        """
        loaded_data = json.load(file_pointer)
        self.options = loaded_data['Configuration']
        self._set_workflow(loaded_data['Workflow'])

    def _set_workflow(self, workflow_name: str) -> None:
        available_workflows = job.available_workflows()
        self.workflow = available_workflows[workflow_name](
            global_settings=self.global_settings or {}
        )

    def run(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        """Launch Speedwagon."""
        if self.options is None:
            raise ValueError("no data loaded")
        if self.workflow is None:
            raise ValueError("no workflow loaded")
        with runner_strategies.BackgroundJobManager() as job_manager:
            self._run_workflow(job_manager, self.workflow, self.options)
            if app is not None:
                app.quit()
        return 0

    def report_exception(
            self,
            exc: BaseException,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            dialog_box_title: Optional[str] = None,
    ) -> None:
        self.logger.error(str(exc))
        report_exception_dialog(
            exc=exc,
            dialog_box_title=dialog_box_title,
            parent=parent
        )

    def _run_workflow(
            self,
            job_manager: runner_strategies.BackgroundJobManager,
            workflow: speedwagon.job.AbsWorkflow,
            options,
    ):

        try:
            if workflow.name is None:
                raise ValueError(f"Unknown workflow: '{workflow}'")
            workflow.validate_user_options(**options)
        except ValueError as user_option_error:
            self.report_exception(
                parent=None,
                exc=user_option_error,
                dialog_box_title="Invalid User Options"
            )
            return

        dialog_box = qtwidgets.dialog.dialogs.WorkflowProgress()

        dialog_box.setWindowTitle(workflow.name or "Workflow")
        dialog_box.show()

        callbacks = qtwidgets.runners.WorkflowProgressCallbacks(dialog_box)
        dialog_box.attach_logger(job_manager.logger)
        threaded_events = runner_strategies.ThreadedEvents()
        job_manager.submit_job(
            workflow_name=workflow.name,
            options=options,
            app=self,
            liaison=runner_strategies.JobManagerLiaison(
                callbacks=callbacks,
                events=threaded_events
            )
        )
        threaded_events.started.set()
        dialog_box.exec()
        if callable(self.on_exit):
            self.on_exit()

    @staticmethod
    def _load_main_window(
            job_manager: "runner_strategies.BackgroundJobManager",
            title: Optional[str]
    ) -> speedwagon.frontend.qtwidgets.gui.MainWindow2:
        window = speedwagon.frontend.qtwidgets.gui.MainWindow2(job_manager)
        if title is not None:
            window.setWindowTitle(title)

        return window


class MultiWorkflowLauncher(AbsStarter):

    def __init__(self, logger:  Optional[logging.Logger] = None) -> None:
        super().__init__()
        self.logger = logger or logging.getLogger(__name__)
        self._pending_tasks: \
            "queue.Queue[Tuple[job.AbsWorkflow, Dict[str, typing.Any]]]" \
            = queue.Queue()

    def run(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        with worker.ToolJobManager() as work_manager:
            work_manager.logger = self.logger
            self._run(work_manager)
        return 0

    def _run(self, work_manager: worker.ToolJobManager) -> None:
        window = speedwagon.frontend.qtwidgets.gui.MainWindow1(
            work_manager=work_manager,
            debug=False)

        window.show()
        try:
            while not self._pending_tasks.empty():
                active_workflow, options = self._pending_tasks.get()
                if active_workflow.name is not None:
                    window.setWindowTitle(active_workflow.name)
                runner_strategy = \
                    qtwidgets.runners.QtRunner(window)

                active_workflow.validate_user_options(**options)

                runner_strategy.run(
                    active_workflow,
                    options,
                    window.log_manager
                )

                self._pending_tasks.task_done()
        except qtwidgets.runners.TaskFailed as task_error:
            raise \
                speedwagon.exceptions.JobCancelled(task_error) from task_error

        finally:
            window.log_manager.handlers.clear()
            window.close()

    def add_job(self, workflow, args):
        self._pending_tasks.put((workflow, args))


class TabsEditorApp(QtWidgets.QDialog):
    """Dialog box for editing tabs.yml file."""

    def __init__(self, *args, **kwargs) -> None:
        """Create a tabs editor dialog window."""
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Speedwagon Tabs Editor")
        layout = QtWidgets.QVBoxLayout()
        self.editor = speedwagon.frontend.qtwidgets.dialog.settings.TabEditor()
        layout.addWidget(self.editor)
        self.dialog_button_box = QtWidgets.QDialogButtonBox(self)
        layout.addWidget(self.dialog_button_box)

        self.dialog_button_box.setStandardButtons(
            cast(
                QtWidgets.QDialogButtonBox.StandardButtons,
                QtWidgets.QDialogButtonBox.Cancel |
                QtWidgets.QDialogButtonBox.Ok
            )
        )

        self.setLayout(layout)

        # pylint: disable=no-member
        self.dialog_button_box.accepted.connect(self.on_okay)
        self.dialog_button_box.rejected.connect(self.on_cancel)
        self.rejected.connect(self.on_cancel)

    def load_all_workflows(self) -> None:
        workflows = job.available_workflows()
        self.editor.set_all_workflows(workflows)

    def on_okay(self) -> None:
        if self.editor.modified is True:
            if self.tabs_file is None:
                return
            qtwidgets.tabs.write_tabs_yaml(
                self.tabs_file,
                qtwidgets.tabs.extract_tab_information(
                    cast(
                        qtwidgets.models.TabsModel,
                        self.editor.selectedTabComboBox.model()
                    )
                )
            )

        self.close()

    def on_cancel(self) -> None:
        self.close()

    def load_tab_file(self, filename: str) -> None:
        """Load tab file."""
        self.editor.tabs_file = filename

    @property
    def tabs_file(self) -> Optional[str]:
        return self.editor.tabs_file

    @tabs_file.setter
    def tabs_file(self, value: str) -> None:
        self.editor.tabs_file = value


def standalone_tab_editor(app: QtWidgets.QApplication = None) -> None:
    """Launch standalone tab editor app."""
    print("Loading settings")
    settings = speedwagon.config.get_platform_settings()

    app = app or QtWidgets.QApplication(sys.argv)
    print("Loading tab editor")
    editor = TabsEditorApp()
    editor.load_all_workflows()

    tabs_file = \
        os.path.join(settings.get_app_data_directory(), TABS_YML_FILE_NAME)

    editor.load_tab_file(tabs_file)

    print("displaying tab editor")
    editor.show()
    app.exec()


class ApplicationLauncher:
    """Application launcher.

    .. versionadded:: 0.2.0
       Added ApplicationLauncher for launching speedwagon in different ways.

    Examples:
       The easy way

        .. testsetup::

            from speedwagon.startup import ApplicationLauncher, StartupDefault
            from unittest.mock import Mock

        .. doctest::
           :skipif: True

           >>> app = ApplicationLauncher()
           >>> app.run()

       or

        .. testsetup::

            from speedwagon.workflows.workflow_capture_one_to_dl_compound_and_dl import CaptureOneToDlCompoundAndDLWorkflow  # noqa: E501 pylint: disable=line-too-long


        .. testcode::
           :skipif: True

           >>> startup_strategy = SingleWorkflowLauncher()
           >>> startup_strategy.set_workflow(
           ...      CaptureOneToDlCompoundAndDLWorkflow()
           ... )
           >>> startup_strategy.options = {
           ...      "Input": "source/images/",
           ...      "Package Type": "Capture One",
           ...      "Output Digital Library": "output/dl",
           ...      "Output HathiTrust": "output/ht"
           ... }
           >>> app = ApplicationLauncher(strategy=startup_strategy)
           >>> app.run()
    """

    def __init__(self, strategy: AbsStarter = None) -> None:
        """Strategy pattern for loading speedwagon in different ways.

        Args:
            strategy: Starter strategy class.
        """
        super().__init__()
        self.strategy = strategy or StartQtThreaded()

    def initialize(self) -> None:
        """Initialize anything that needs to done prior to running."""
        self.strategy.initialize()

    def run(self, app=None) -> int:
        """Run Speedwagon."""
        return self.strategy.run(app)


class SubCommand(abc.ABC):
    def __init__(self, args) -> None:
        super().__init__()
        self.args = args
        self.global_settings = None

    @abc.abstractmethod
    def run(self):
        """Run the command."""


class RunCommand(SubCommand):
    def json_startup(self) -> None:
        startup_strategy = SingleWorkflowJSON()
        startup_strategy.global_settings = self.global_settings
        startup_strategy.load(self.args.json)
        self._run_strategy(startup_strategy)

    @staticmethod
    def _run_strategy(startup_strategy):
        app_launcher = \
            speedwagon.startup.ApplicationLauncher(strategy=startup_strategy)

        app = ApplicationLauncher()
        app.initialize()
        sys.exit(app_launcher.run())

    def run(self):
        if "json" in self.args:
            self.json_startup()
        else:
            print(f"Invalid {self.args}")


def get_global_options():
    platform_settings = speedwagon.config.get_platform_settings()

    config_file = os.path.join(
        platform_settings.get_app_data_directory(),
        CONFIG_INI_FILE_NAME
    )
    return speedwagon.config.ConfigLoader(config_file).get_settings()


def run_command(
        command_name: str,
        args: argparse.Namespace,
        command=None
) -> None:
    commands = {
        "run": RunCommand
    }
    command = command or commands.get(command_name)

    if command is None:
        raise ValueError(f"Unknown command {command_name}")

    new_command = command(args)
    new_command.global_settings = get_global_options()
    new_command.run()


def main(argv: List[str] = None) -> None:
    """Launch main entry point."""
    argv = argv or sys.argv
    if "tab-editor" in argv:
        standalone_tab_editor()
        return
    parser = speedwagon.config.CliArgsSetter.get_arg_parser()
    args = parser.parse_args(argv[1:])

    if args.command is not None:
        run_command(command_name=args.command, args=args)
        return

    app = ApplicationLauncher()
    app.initialize()
    sys.exit(app.run())


if __name__ == '__main__':
    main()
