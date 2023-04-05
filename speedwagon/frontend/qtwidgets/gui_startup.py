from __future__ import annotations
import abc
import collections
import contextlib
import io
import json
import logging
import os
import sys
import threading
import time
import types
import typing
from typing import Dict, Optional, cast, List, Type
import traceback as tb
import webbrowser
try:  # pragma: no cover
    from importlib import metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore
from PySide6 import QtWidgets

import speedwagon
from speedwagon import config
from . import user_interaction
from . import dialog
from . import runners

if typing.TYPE_CHECKING:
    from speedwagon import runner_strategies
    from speedwagon.frontend.qtwidgets import gui
    from speedwagon.frontend.qtwidgets.dialog import dialogs
    from speedwagon.job import AbsWorkflow, AbsJobConfigSerializationStrategy
    from speedwagon.config import SettingsData


class AbsGuiStarter(speedwagon.startup.AbsStarter, abc.ABC):

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app

    def run(self) -> int:
        return self.start_gui(self.app)

    @abc.abstractmethod
    def start_gui(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        """Run the gui application."""


def save_workflow_config(
        workflow_name,
        data,
        parent: QtWidgets.QWidget,
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


class StartQtThreaded(AbsGuiStarter):

    def __init__(self, app: Optional[QtWidgets.QApplication] = None) -> None:
        super().__init__(app)

        self.startup_settings: SettingsData = {'debug': False}

        self.windows: Optional[gui.MainWindow3] = None
        self.logger = logging.getLogger()

        formatter = \
            logging.Formatter('%(asctime)-15s %(threadName)s %(message)s')

        self.platform_settings = config.get_platform_settings()
        self.app: QtWidgets.QApplication = (
            app
            or QtWidgets.QApplication(sys.argv)
        )
        self._log_data = io.StringIO()
        self.config_loader_strategy = config.StandardConfigFileLocator()

        log_data_handler = logging.StreamHandler(self._log_data)
        log_data_handler.setLevel(logging.DEBUG)
        log_data_handler.setFormatter(formatter)

        self.logger.addHandler(log_data_handler)
        self.logger.setLevel(logging.DEBUG)

        speedwagon.frontend.qtwidgets.gui.set_app_display_metadata(self.app)
        self._request_window = user_interaction.QtRequestMoreInfo(self.windows)

    @staticmethod
    def import_workflow_config(
            parent: gui.MainWindow3,
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
        parent.set_active_workflow(workflow_name)
        parent.set_current_workflow_settings(data)

    def _load_help(self) -> None:
        try:
            pkg_metadata: metadata.PackageMetadata = \
                metadata.metadata(speedwagon.__name__)
            webbrowser.open_new(pkg_metadata['Home-page'])
        except metadata.PackageNotFoundError as error:
            self.logger.warning(
                "No help link available. Reason: %s", error)

    def ensure_settings_files(self) -> None:
        config.ensure_settings_files(logger=self.logger)

    @staticmethod
    def read_settings_file(settings_file: str) -> SettingsData:

        with config.ConfigManager(settings_file) as current_config:
            return current_config.global_settings

    def resolve_settings(
            self,
            resolution_order: Optional[
                List[config.AbsSetting]
            ] = None,
            loader: Optional[config.ConfigLoader] = None
    ) -> SettingsData:
        config_strategy = config.StandardConfigFileLocator()
        loader = \
            loader or config.ConfigLoader(config_strategy.get_config_file())

        self.platform_settings._data.update(
            loader.read_settings_file_globals(
                config_strategy.get_config_file()
            )
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

    def load_workflows(self) -> None:
        if self.windows is None:
            return
        print("load_workflows")
        config_strategy = config.StandardConfigFileLocator()

        self.logger.debug("Loading Workflows")
        loading_workflows_stream = io.StringIO()
        self.windows.clear_tabs()
        with contextlib.redirect_stderr(loading_workflows_stream):
            all_workflows = speedwagon.job.available_workflows()

        for workflow_name, error in \
                self._find_invalid(all_workflows):
            error_message = \
                f"Unable to load workflow '{workflow_name}'. Reason: {error}"

            self.logger.error(error_message)
            self.windows.console.add_message(error_message)
            del all_workflows[workflow_name]
        # self.windows.tab_widget.clear_tabs()
        # Load every user configured tab
        self.load_custom_tabs(
            self.windows,
            config_strategy.get_tabs_file(),
            all_workflows
        )

        # All Workflows tab
        self.load_all_workflows_tab(self.windows, all_workflows)

        workflow_errors_msg = loading_workflows_stream.getvalue().strip()
        if workflow_errors_msg:
            for line in workflow_errors_msg.split("\n"):
                self.logger.warning(line)

    def load_all_workflows_tab(
            self,
            application: gui.MainWindow3,
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
            main_window: gui.MainWindow3,
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

    def save_log(self, parent: QtWidgets.QWidget) -> None:
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

    def request_settings(
            self,
            parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        config_strategy = config.StandardConfigFileLocator()

        dialog_builder = dialog.settings.SettingsBuilder2(parent=parent)
        dialog_builder.app_data_dir = config_strategy.get_app_data_dir()

        global_settings_tab = dialog.settings.GlobalSettingsTab()
        global_settings_tab.load_ini_file(config_strategy.get_config_file())
        dialog_builder.add_tab("Global Settings", global_settings_tab)

        tabs_config = dialog.settings.TabsConfigurationTab()
        tabs_config.load(config_strategy.get_tabs_file())
        dialog_builder.add_tab("Tabs", tabs_config)

        plugins_tab = dialog.settings.PluginsTab()
        plugins_tab.load(config_strategy.get_config_file())
        dialog_builder.add_tab("Plugins", plugins_tab)

        saver = dialog.settings.ConfigSaver(parent)

        def success(_) -> None:
            if self.windows:
                self.windows.clear_tabs()
                self.windows.update_settings()
            self.load_workflows()

        saver.add_success_call_back(success)
        saver.tabs_yaml_path = config_strategy.get_tabs_file()
        saver.config_file_path = config_strategy.get_config_file()
        dialog_builder.set_saver_strategy(saver)
        config_dialog: dialog.settings.SettingsDialog = dialog_builder.build()
        config_dialog.exec_()

    def exceptions_hook(
            self,
            cls: Type[BaseException],
            exception: BaseException,
            traceback: Optional[types.TracebackType]
    ) -> None:
        if self.windows:
            self.windows.hide()
        tb.print_tb(traceback)
        self.report_exception(exception, self.windows)
        if self.windows:
            self.windows.close()
        print(f"Unhandled exception: {cls.__name__}")
        print("Speedwagon exited prematurely")
        self.app.exit(1)

    def start_gui(self, app: Optional[QtWidgets.QApplication] = None) -> int:

        original_hook = sys.excepthook

        def excepthook(
            cls: Type[BaseException],
            exception: BaseException,
            traceback: Optional[types.TracebackType]
        ):
            self.exceptions_hook(cls, exception, traceback)

        # without this, unhandled exceptions won't close the application
        # because QT/PySide keeps the GUI open.
        try:
            sys.excepthook = excepthook
            with speedwagon.runner_strategies.BackgroundJobManager() \
                    as job_manager:
                job_manager.global_settings = self.startup_settings
                self.windows = self.build_main_window(job_manager)
                self._request_window = \
                    user_interaction.QtRequestMoreInfo(self.windows)
                self.load_workflows()
                self.windows.update_settings()
                self.windows.show()
                return self.app.exec()
        finally:
            sys.excepthook = original_hook

    def build_main_window(
            self,
            job_manager
    ) -> speedwagon.frontend.qtwidgets.gui.MainWindow3:
        window = speedwagon.frontend.qtwidgets.gui.MainWindow3()
        window.console.attach_logger(self.logger)

        window.action_export_logs.triggered.connect(
            lambda: self.save_log(window)
        )

        window.export_job_config.connect(save_workflow_config)

        window.action_import_job.triggered.connect(
            lambda: self.import_workflow_config(window)
        )

        window.action_system_info_requested.triggered.connect(
            lambda: self.request_system_info(window)
        )

        window.action_open_application_preferences.triggered.connect(
            lambda: self.request_settings(window)
        )

        window.action_help_requested.triggered.connect(self._load_help)

        window.action_about.triggered.connect(
            lambda: dialog.about_dialog_box(window)
        )

        window.submit_job.connect(
            lambda workflow_name, options:
            self.submit_job(
                job_manager,
                workflow_name,
                options,
                main_app=self.windows,
            )
        )
        return window

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
                gui.MainWindow3
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
            dialog_box.rejected.connect(main_app.close)  # type: ignore

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

        error_dialog = \
            dialog.dialogs.SpeedwagonUnhandledExceptionDialog(parent)
        if dialog_box_title:
            error_dialog.setWindowTitle(dialog_box_title)
        error_dialog.exception = exc
        error_dialog.exec()

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
                QtWidgets.QDialogButtonBox.StandardButton,
                QtWidgets.QDialogButtonBox.StandardButton.Cancel |
                QtWidgets.QDialogButtonBox.StandardButton.Ok
            )
        )

        self.setLayout(layout)

        # pylint: disable=no-member
        self.dialog_button_box.accepted.connect(self.on_okay)  # type: ignore
        self.dialog_button_box.rejected.connect(self.on_cancel)  # type: ignore
        self.rejected.connect(self.on_cancel)  # type: ignore

    def load_all_workflows(self) -> None:
        self.editor.set_all_workflows(speedwagon.job.available_workflows())

    def on_okay(self) -> None:
        if self.editor.modified is True:
            if self.tabs_file is None:
                return
            speedwagon.frontend.qtwidgets.tabs.write_tabs_yaml(
                self.tabs_file,
                speedwagon.frontend.qtwidgets.tabs.extract_tab_information(
                    cast(
                        speedwagon.frontend.qtwidgets.models.TabsModel,
                        self.editor.selected_tab_combo_box.model()
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


def standalone_tab_editor(
        app: Optional[QtWidgets.QApplication] = None
) -> None:
    """Launch standalone tab editor app."""
    print("Loading settings")

    app = app or QtWidgets.QApplication(sys.argv)
    print("Loading tab editor")
    editor = TabsEditorApp()
    editor.load_all_workflows()

    file_locator = config.StandardConfigFileLocator()
    editor.load_tab_file(file_locator.get_tabs_file())

    print("displaying tab editor")
    editor.show()
    app.exec()


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
                [speedwagon.frontend.qtwidgets.gui.MainWindow3], None]
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
        error_dialog = \
            dialog.dialogs.SpeedwagonUnhandledExceptionDialog(parent)
        if dialog_box_title:
            error_dialog.setWindowTitle(dialog_box_title)
        error_dialog.exception = exc
        error_dialog.exec()

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
    ) -> gui.MainWindow3:
        window = speedwagon.frontend.qtwidgets.gui.MainWindow3()
        window.job_manager = job_manager
        if title is not None:
            window.setWindowTitle(title)

        return window
