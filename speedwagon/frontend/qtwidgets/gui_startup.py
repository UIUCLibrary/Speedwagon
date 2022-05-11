from __future__ import annotations
import abc
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
from typing import Dict, Union, Optional, cast, List, Type
import webbrowser
try:  # pragma: no cover
    from importlib import metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore
from PySide6 import QtWidgets

import speedwagon
from speedwagon import config
from . import logging_helpers
from . import user_interaction
from . import splashscreen
from . import dialog
from . import runners

if typing.TYPE_CHECKING:
    from typing import Tuple
    from speedwagon import runner_strategies
    from speedwagon.frontend.qtwidgets import gui, worker
    from speedwagon.frontend.qtwidgets.dialog import dialogs
    from speedwagon.job import AbsWorkflow, AbsJobConfigSerializationStrategy


class AbsGuiStarter(speedwagon.startup.AbsStarter):

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app

    def run(self) -> int:
        return self.start_gui(self.app)

    @abc.abstractmethod
    def start_gui(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        """Run the gui application."""


class StartupGuiDefault(AbsGuiStarter):
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
        self.platform_settings = config.get_platform_settings()

        self.config_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            speedwagon.startup.CONFIG_INI_FILE_NAME
        )

        self.tabs_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            speedwagon.startup.TABS_YML_FILE_NAME
        )

        # Make sure required directories exists
        self.user_data_dir = \
            typing.cast(str, self.platform_settings.get("user_data_directory"))

        self.startup_settings: Dict[str, Union[str, bool]] = {}
        self._debug = False

        self.app_data_dir = typing.cast(
            str, self.platform_settings.get("app_data_directory")
        )
        self.app = app or QtWidgets.QApplication(sys.argv)

    def initialize(self) -> None:
        self.ensure_settings_files()
        self.resolve_settings()

    def start_gui(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        splash = splashscreen.create_splash()
        splash_message_handler = logging_helpers.SplashScreenLogHandler(splash)

        # If debug mode, print the log messages directly on the splash screen
        if self._debug:
            splash_message_handler.setLevel(logging.DEBUG)
        else:
            splash_message_handler.setLevel(logging.INFO)

        splash.show()
        QtWidgets.QApplication.processEvents()

        speedwagon.frontend.qtwidgets.gui.set_app_display_metadata(self.app)

        with speedwagon.frontend.qtwidgets.worker.ToolJobManager() \
                as work_manager:

            work_manager.settings_path = \
                self.platform_settings.get_app_data_directory()

            windows = speedwagon.frontend.qtwidgets.gui.MainWindow1(
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

    def load_configurations(self, work_manager: worker.ToolJobManager) -> None:
        self._logger.debug("Applying settings to Speedwagon")
        work_manager.user_settings = self.platform_settings
        work_manager.configuration_file = self.config_file

    def _load_workflows(self, application: gui.MainWindow1) -> None:
        self._logger.debug("Loading Workflows")
        loading_workflows_stream = io.StringIO()
        with contextlib.redirect_stderr(loading_workflows_stream):
            all_workflows = speedwagon.job.available_workflows()
        # Load every user configured tab
        tabs_file_size = os.path.getsize(self.tabs_file)
        if tabs_file_size > 0:
            try:
                for tab_name, extra_tab in \
                        speedwagon.startup.get_custom_tabs(
                            all_workflows,
                            self.tabs_file
                        ):
                    application.add_tab(tab_name, collections.OrderedDict(
                        sorted(extra_tab.items())))
            except speedwagon.startup.FileFormatError as error:
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
            resolution_order: Optional[List[config.AbsSetting]] = None,
            loader: typing.Optional[config.ConfigLoader] = None
    ) -> None:
        loader = loader or config.ConfigLoader(self.config_file)

        self.platform_settings._data.update(
            loader.read_settings_file(self.config_file)
        )
        loader.logger = self._logger
        if resolution_order:
            loader.resolution_strategy_order = resolution_order
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
        config.ensure_settings_files(self, self._logger)


class StartQtThreaded(AbsGuiStarter):

    def __init__(self, app: QtWidgets.QApplication = None) -> None:
        self.startup_settings: Dict[str, Union[str, bool]] = {'debug': False}

        self.windows: Optional[gui.MainWindow2] = None
        self.logger = logging.getLogger()

        formatter = \
            logging.Formatter('%(asctime)-15s %(threadName)s %(message)s')

        self.platform_settings = config.get_platform_settings()
        self.app = app or QtWidgets.QApplication(sys.argv)
        self._log_data = io.StringIO()

        log_data_handler = logging.StreamHandler(self._log_data)
        log_data_handler.setLevel(logging.DEBUG)
        log_data_handler.setFormatter(formatter)

        self.logger.addHandler(log_data_handler)
        self.logger.setLevel(logging.DEBUG)

        self.load_settings()
        speedwagon.frontend.qtwidgets.gui.set_app_display_metadata(self.app)
        self._request_window = user_interaction.QtRequestMoreInfo(self.windows)

    @staticmethod
    def import_workflow_config(
            parent: gui.MainWindow2,
            dialog_box: typing.Optional[QtWidgets.QFileDialog] = None,
            serialization_strategy: typing.Optional[
                AbsJobConfigSerializationStrategy] = None
    ) -> None:
        serialization_strategy = \
            serialization_strategy or speedwagon.job.ConfigJSONSerialize()

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
                speedwagon.job.AbsJobConfigSerializationStrategy
            ] = None
    ) -> None:
        serialization_strategy = \
            serialization_strategy or speedwagon.job.ConfigJSONSerialize()

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
            speedwagon.startup.CONFIG_INI_FILE_NAME
        )

        self.app_data_dir = typing.cast(
            str, self.platform_settings["app_data_directory"]
        )

        self.tabs_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            speedwagon.startup.TABS_YML_FILE_NAME
        )

    def _load_help(self) -> None:
        try:
            pkg_metadata = dict(metadata.metadata(speedwagon.__name__))
            webbrowser.open_new(pkg_metadata['Home-page'])
        except metadata.PackageNotFoundError as error:
            self.logger.warning(
                "No help link available. Reason: %s", error)

    def ensure_settings_files(self) -> None:
        config.ensure_settings_files(self, logger=self.logger)

    @staticmethod
    def read_settings_file(settings_file: str) -> Dict[str, Union[str, bool]]:

        with config.ConfigManager(settings_file) as current_config:
            return current_config.global_settings

    def resolve_settings(
            self,
            resolution_order: Optional[
                List[config.AbsSetting]
            ] = None,
            loader: config.ConfigLoader = None
    ) -> Dict[str, Union[str, bool]]:

        loader = loader or config.ConfigLoader(self.config_file)

        self.platform_settings._data.update(
            loader.read_settings_file(self.config_file)
        )

        loader.logger = self.logger
        if resolution_order:
            loader.resolution_strategy_order = resolution_order

        results = loader.get_settings()

        self.startup_settings = results
        return self.startup_settings

    def initialize(self) -> None:
        self.ensure_settings_files()
        self.startup_settings = self.resolve_settings()

    def _load_workflows(
            self,
            application: gui.MainWindow2
    ) -> None:
        tabs_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            speedwagon.startup.TABS_YML_FILE_NAME
        )

        self.logger.debug("Loading Workflows")
        loading_workflows_stream = io.StringIO()
        with contextlib.redirect_stderr(loading_workflows_stream):
            all_workflows = speedwagon.job.available_workflows()

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
            application: gui.MainWindow2,
            loaded_workflows: typing.Dict[str, Type[speedwagon.job.Workflow]]
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
            main_window: gui.MainWindow2,
            tabs_file: str,
            loaded_workflows: typing.Dict[str, Type[speedwagon.job.Workflow]]
    ) -> None:
        tabs_file_size = os.path.getsize(tabs_file)
        if tabs_file_size > 0:
            try:
                for tab_name, extra_tab in \
                        speedwagon.startup.get_custom_tabs(
                            loaded_workflows,
                            tabs_file
                        ):
                    main_window.add_tab(tab_name, collections.OrderedDict(
                        sorted(extra_tab.items())))
            except speedwagon.startup.FileFormatError as error:
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
        dialog.dialogs.SystemInfoDialog(parent).exec()

    @staticmethod
    def request_settings(parent: QtWidgets.QWidget = None) -> None:
        platform_settings = config.get_platform_settings()
        settings_path = platform_settings.get_app_data_directory()

        dialog_builder = dialog.settings.SettingsBuilder(parent=parent)

        dialog_builder.add_open_settings(
            platform_settings.get_app_data_directory()
        )

        dialog_builder.add_global_settings(
            os.path.join(
                settings_path,
                speedwagon.startup.CONFIG_INI_FILE_NAME
            )
        )

        dialog_builder.add_tabs_setting(
            os.path.join(settings_path, speedwagon.startup.TABS_YML_FILE_NAME)
        )

        config_dialog = dialog_builder.build()
        config_dialog.exec_()

    def start_gui(self, app: Optional[QtWidgets.QApplication] = None) -> int:

        with speedwagon.runner_strategies.BackgroundJobManager() \
                as job_manager:
            job_manager.global_settings = self.startup_settings
            self.windows = speedwagon.frontend.qtwidgets.gui.MainWindow2(
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
            dialog_box: dialogs.WorkflowProgress,
            events: runner_strategies.AbsEvents
    ) -> None:
        dialog_box.stop()
        events.stop()

    def request_more_info(
            self,
            workflow: speedwagon.job.Workflow,
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
                gui.MainWindow2
            ] = None,
    ) -> None:

        workflow_class = \
            speedwagon.job.available_workflows().get(workflow_name)
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

        dialog_box = dialog.dialogs.WorkflowProgress(parent=self.windows)

        if main_app is not None:
            # pylint: disable=no-member
            dialog_box.rejected.connect(main_app.close)

        dialog_box.setWindowTitle(workflow_name)
        dialog_box.show()
        threaded_events = speedwagon.runner_strategies.ThreadedEvents()

        dialog_box.aborted.connect(
            lambda: self.abort_job(dialog_box, threaded_events)
        )
        callbacks = runners.WorkflowProgressCallbacks(dialog_box)

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
            liaison=speedwagon.runner_strategies.JobManagerLiaison(
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
            workflows: typing.Dict[str, typing.Type[speedwagon.job.Workflow]]
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
        workflows = speedwagon.job.available_workflows()
        self.editor.set_all_workflows(workflows)

    def on_okay(self) -> None:
        if self.editor.modified is True:
            if self.tabs_file is None:
                return
            speedwagon.frontend.qtwidgets.tabs.write_tabs_yaml(
                self.tabs_file,
                speedwagon.frontend.qtwidgets.tabs.extract_tab_information(
                    cast(
                        speedwagon.frontend.qtwidgets.models.TabsModel,
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
    settings = config.get_platform_settings()

    app = app or QtWidgets.QApplication(sys.argv)
    print("Loading tab editor")
    editor = TabsEditorApp()
    editor.load_all_workflows()

    tabs_file = \
        os.path.join(
            settings.get_app_data_directory(),
            speedwagon.startup.TABS_YML_FILE_NAME
        )

    editor.load_tab_file(tabs_file)

    print("displaying tab editor")
    editor.show()
    app.exec()


class SingleWorkflowLauncher(AbsGuiStarter):
    """Single workflow launcher.

    .. versionadded:: 0.2.0
       Added SingleWorkflowLauncher class for running a single workflow \
            without user interaction. Useful for building new workflows.

    """

    def __init__(
            self,
            app,
            logger: typing.Optional[logging.Logger] = None
    ) -> None:
        """Set up window for running a single workflow."""
        super().__init__(app)
        self.window: Optional[
            speedwagon.frontend.qtwidgets.gui.MainWindow1
        ] = None
        self._active_workflow: Optional[AbsWorkflow] = None
        self.options: Dict[str, Union[str, bool]] = {}
        self.logger = logger or logging.getLogger(__name__)

    def start_gui(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        """Run the workflow configured with the options given."""
        if self._active_workflow is None:
            raise AttributeError("Workflow has not been set")

        with speedwagon.frontend.qtwidgets.worker.ToolJobManager() \
                as work_manager:
            work_manager.logger = self.logger
            self._run(work_manager)
        return 0

    def _run(
            self,
            work_manager: speedwagon.frontend.qtwidgets.worker.ToolJobManager
    ) -> None:
        if self._active_workflow is None:
            raise ValueError("No active workflow set")

        window = speedwagon.frontend.qtwidgets.gui.MainWindow1(
            work_manager=work_manager,
            debug=False)

        window.show()
        if self._active_workflow.name is not None:
            window.setWindowTitle(self._active_workflow.name)
        runner_strategy = \
            speedwagon.frontend.qtwidgets.runners.QtRunner(window)

        self._active_workflow.validate_user_options(**self.options)
        # runner_strategy.additional_info_callback

        runner_strategy.run(self._active_workflow,
                            self.options,
                            window.log_manager)
        window.log_manager.handlers.clear()
        window.close()

    def set_workflow(self, workflow: AbsWorkflow) -> None:
        """Set the current workflow."""
        self._active_workflow = workflow


def report_exception_dialog(exc, dialog_box_title, parent):
    text = str(exc)
    dialog_box = QtWidgets.QMessageBox(parent)
    if dialog_box_title is not None:
        dialog_box.setWindowTitle(dialog_box_title)
    dialog_box.setText(text)
    dialog_box.exec_()


class SingleWorkflowJSON(AbsGuiStarter):
    """Start up class for loading instructions from a JSON file.

    .. versionadded:: 0.2.0
        SingleWorkflowJSON class added

    """

    def __init__(self, app, logger: Optional[logging.Logger] = None) -> None:
        """Create a environment where the workflow is loaded from a json file.

        Args:
            logger: Optional Logger, defaults to default logger for __name__.
        """
        super().__init__(app)
        self.global_settings = None
        self.on_exit: typing.Optional[
            typing.Callable[
                [speedwagon.frontend.qtwidgets.gui.MainWindow2], None]
        ] = None
        self.options: typing.Optional[typing.Dict[str, typing.Any]] = None
        self.workflow: typing.Optional[AbsWorkflow] = None
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
        available_workflows = speedwagon.job.available_workflows()
        self.workflow = available_workflows[workflow_name](
            global_settings=self.global_settings or {}
        )

    def start_gui(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        """Launch Speedwagon."""
        if self.options is None:
            raise ValueError("no data loaded")
        if self.workflow is None:
            raise ValueError("no workflow loaded")
        with speedwagon.runner_strategies.BackgroundJobManager() \
                as job_manager:
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
            workflow: AbsWorkflow,
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

        dialog_box = dialog.dialogs.WorkflowProgress()

        dialog_box.setWindowTitle(workflow.name or "Workflow")
        dialog_box.show()

        callbacks = \
            speedwagon.frontend.qtwidgets.runners.WorkflowProgressCallbacks(
                dialog_box
            )

        dialog_box.attach_logger(job_manager.logger)
        threaded_events = speedwagon.runner_strategies.ThreadedEvents()
        job_manager.submit_job(
            workflow_name=workflow.name,
            options=options,
            app=self,
            liaison=speedwagon.runner_strategies.JobManagerLiaison(
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
            job_manager: runner_strategies.BackgroundJobManager,
            title: Optional[str]
    ) -> gui.MainWindow2:
        window = speedwagon.frontend.qtwidgets.gui.MainWindow2(job_manager)
        if title is not None:
            window.setWindowTitle(title)

        return window


class MultiWorkflowLauncher(AbsGuiStarter):

    def __init__(self, app, logger:  Optional[logging.Logger] = None) -> None:
        super().__init__(app)
        self.logger = logger or logging.getLogger(__name__)
        self._pending_tasks: \
            "queue.Queue[Tuple[AbsWorkflow, Dict[str, typing.Any]]]" \
            = queue.Queue()

    def start_gui(self, app: Optional[QtWidgets.QApplication] = None) -> int:

        with speedwagon.frontend.qtwidgets.worker.ToolJobManager() as \
                work_manager:
            work_manager.logger = self.logger
            self._run(work_manager)
        return 0

    def _run(
            self,
            work_manager: worker.ToolJobManager
    ) -> None:
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
                    speedwagon.frontend.qtwidgets.runners.QtRunner(window)

                active_workflow.validate_user_options(**options)

                runner_strategy.run(
                    active_workflow,
                    options,
                    window.log_manager
                )

                self._pending_tasks.task_done()
        except speedwagon.frontend.qtwidgets.runners.TaskFailed as task_error:
            raise \
                speedwagon.exceptions.JobCancelled(task_error) from task_error

        finally:
            window.log_manager.handlers.clear()
            window.close()

    def add_job(self, workflow, args):
        self._pending_tasks.put((workflow, args))
