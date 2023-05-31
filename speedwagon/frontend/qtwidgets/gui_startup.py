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
from typing import Dict, Optional, cast, List, Type, Callable
import traceback as tb
import webbrowser

try:  # pragma: no cover
    from importlib import metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore
from PySide6 import QtWidgets

import speedwagon
from speedwagon.workflow import initialize_workflows
from speedwagon import config
from speedwagon.tasks import system as system_tasks
from . import user_interaction
from . import dialog
from .dialog.settings import EntrypointsPluginModelLoader
from . import runners

if typing.TYPE_CHECKING:
    from speedwagon import runner_strategies
    from speedwagon.frontend.qtwidgets import gui
    from speedwagon.frontend.qtwidgets.dialog import dialogs
    from speedwagon.job import AbsWorkflow, AbsJobConfigSerializationStrategy
    from speedwagon.config import FullSettingsData
    from speedwagon.config.tabs import AbsTabsConfigDataManagement


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
    ] = None,
) -> None:
    serialization_strategy = (
        serialization_strategy or speedwagon.job.ConfigJSONSerialize()
    )

    dialog_box = dialog_box or QtWidgets.QFileDialog()
    export_file_name, _ = dialog_box.getSaveFileName(
        parent,
        "Export Job Configuration",
        f"{workflow_name}.json",
        "Job Configuration JSON (*.json)",
    )

    if export_file_name:
        serialization_strategy.file_name = export_file_name
        serialization_strategy.save(workflow_name, data)


class AbsResolveSettingsStrategy(abc.ABC):  # pylint: disable=R0903
    @abc.abstractmethod
    def get_settings(self) -> FullSettingsData:
        """Get full settings"""


class ResolveSettings(AbsResolveSettingsStrategy):  # pylint: disable=R0903
    def get_settings(self) -> FullSettingsData:
        config_strategy = config.StandardConfigFileLocator()
        manager = config.IniConfigManager(config_strategy.get_config_file())
        return manager.data()


def _setup_config_tab(
    saver: dialog.settings.MultiSaver,
) -> dialog.settings.TabsConfigurationTab:
    config_strategy = config.StandardConfigFileLocator()
    tabs_config = dialog.settings.TabsConfigurationTab()
    tabs_config.editor.load_data()
    saver.config_savers.append(
        dialog.settings.ConfigFileSaver(
            dialog.settings.SettingsTabSaveStrategy(
                tabs_config,
                lambda widget: config.tabs.TabsYamlWriter().serialize(
                    filter(
                        lambda tab: tab.tab_name != "All",
                        widget.get_data().get("tab_information", []),
                    )
                ),
            ),
            config_strategy.get_tabs_file(),
        )
    )
    return tabs_config


def _setup_workflow_settings_tab(
    saver: dialog.settings.MultiSaver,
) -> dialog.settings.ConfigWorkflowSettingsTab:
    workflow_settings_tab = dialog.settings.ConfigWorkflowSettingsTab()
    config_strategy = config.StandardConfigFileLocator()
    saver.config_savers.append(
        dialog.settings.ConfigFileSaver(
            dialog.settings.SettingsTabSaveStrategy(
                workflow_settings_tab,
                lambda widget: speedwagon.config.workflow
                .SettingsYamlSerializer
                .serialize_structure_to_yaml(
                    {
                        workflow_name:
                            speedwagon.config.workflow.SettingsYamlSerializer
                            .structure_workflow_data(value)
                        for (workflow_name, value) in
                        widget.get_data()['workflow settings'].items()
                    }
                )
            ),
            os.path.join(
                config_strategy.get_app_data_dir(),
                config.WORKFLOWS_SETTINGS_YML_FILE_NAME,
            ),
        )
    )
    # Only add workflows to the configuration if it has something to
    # configure. Otherwise, this gets overly cluttered.
    workflow_settings_tab.set_workflows(
        filter(
            lambda workflow: len(workflow.workflow_options()) != 0,
            initialize_workflows(),
        )
    )
    return workflow_settings_tab


def _setup_global_settings_tab(
    saver: dialog.settings.MultiSaver,
) -> dialog.settings.GlobalSettingsTab:
    config_strategy = config.StandardConfigFileLocator()
    global_settings_tab = dialog.settings.GlobalSettingsTab()

    def serialize(widget):
        ini_serializer = config.config.IniConfigSaver()
        ini_serializer.parser.read(config_strategy.get_config_file())
        return ini_serializer.serialize(
            {
                "GLOBAL": typing.cast(
                    speedwagon.config.SettingsData, widget.get_data()
                )
            }
        )

    saver.config_savers.append(
        dialog.settings.ConfigFileSaver(
            dialog.settings.SettingsTabSaveStrategy(
                global_settings_tab,
                serialize
            ),
            config_strategy.get_config_file(),
        )
    )
    global_settings_tab.load_ini_file(config_strategy.get_config_file())
    return global_settings_tab


def _setup_plugins_tab(
        saver: dialog.settings.MultiSaver,
) -> dialog.settings.PluginsTab:
    config_strategy = config.StandardConfigFileLocator()
    plugins_tab = dialog.settings.PluginsTab()
    plugins_tab.load(config_strategy.get_config_file())

    config_file = config_strategy.get_config_file()

    def serializer(widget) -> str:
        ini_serializer = config.plugins.IniSerializer()
        ini_serializer.parser.read(config_file)
        return ini_serializer.serialize(widget.get_data())

    saver.config_savers.append(
        dialog.settings.ConfigFileSaver(
            dialog.settings.SettingsTabSaveStrategy(plugins_tab, serializer),
            config_file
        )
    )
    return plugins_tab


class StartQtThreaded(AbsGuiStarter):
    def __init__(self, app: Optional[QtWidgets.QApplication] = None) -> None:
        super().__init__(app)
        self.settings_resolver: AbsResolveSettingsStrategy = ResolveSettings()
        self.startup_settings: FullSettingsData = {"GLOBAL": {"debug": False}}

        self.windows: Optional[gui.MainWindow3] = None
        self.logger = logging.getLogger()

        formatter = logging.Formatter(
            "%(asctime)-15s %(threadName)s %(message)s"
        )

        self.platform_settings = config.get_platform_settings()
        self.app: QtWidgets.QApplication = app or QtWidgets.QApplication(
            sys.argv
        )
        self._log_data = io.StringIO()

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
            AbsJobConfigSerializationStrategy
        ] = None,
    ) -> None:
        serialization_strategy = (
            serialization_strategy or speedwagon.job.ConfigJSONSerialize()
        )

        dialog_box = dialog_box or QtWidgets.QFileDialog()
        load_file, _ = dialog_box.getOpenFileName(
            parent,
            "Import Job Configuration",
            "",
            "Job Configuration JSON (*.json);;All Files (*)",
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
            pkg_metadata: metadata.PackageMetadata = metadata.metadata(
                speedwagon.__name__
            )
            webbrowser.open_new(pkg_metadata["Home-page"])
        except metadata.PackageNotFoundError as error:
            self.logger.warning("No help link available. Reason: %s", error)

    def ensure_settings_files(self) -> None:
        config.config.ensure_settings_files(logger=self.logger)

    def resolve_settings(self) -> FullSettingsData:
        settings = self.settings_resolver.get_settings()
        self.platform_settings._data.update(settings.get("GLOBAL", {}))
        self.startup_settings = settings
        return self.startup_settings

    def initialize(self) -> None:
        startup_tasks: List[system_tasks.AbsSystemTask] = [
            system_tasks.EnsureGlobalConfigFiles(self.logger),
            system_tasks.EnsureBuiltinWorkflowConfigFiles()
        ]
        plugin_strategy = speedwagon.plugins.LoadWhiteListedPluginsOnly()
        plugin_strategy.whitelisted_entry_points = (
            speedwagon.config.get_whitelisted_plugins()
        )
        for plugin in plugin_strategy.locate():
            startup_tasks.extend(iter(plugin.plugin_init_tasks))
        for task in startup_tasks:
            task.run()

        self.startup_settings = self.resolve_settings()

    def load_workflows(self) -> None:
        if self.windows is None:
            return
        config_strategy = config.StandardConfigFileLocator()

        self.logger.debug("Loading Workflows")
        loading_workflows_stream = io.StringIO()
        self.windows.clear_tabs()
        with contextlib.redirect_stderr(loading_workflows_stream):
            all_workflows = speedwagon.job.available_workflows()

        for workflow_name, error in self._find_invalid(all_workflows):
            error_message = (
                f"Unable to load workflow '{workflow_name}'. Reason: {error}"
            )

            self.logger.error(error_message)
            self.windows.console.add_message(error_message)
            del all_workflows[workflow_name]

        # Load every user configured tab
        self.load_custom_tabs(
            self.windows, config_strategy.get_tabs_file(), all_workflows
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
        loaded_workflows: typing.Dict[str, Type[speedwagon.job.Workflow]],
    ) -> None:
        print("Loading Tab All")
        self.logger.debug("Loading Tab All")
        application.add_tab(
            "All", collections.OrderedDict(sorted(loaded_workflows.items()))
        )

    def load_custom_tabs(
        self,
        main_window: gui.MainWindow3,
        tabs_file: str,
        loaded_workflows: typing.Dict[str, Type[speedwagon.job.Workflow]],
    ) -> None:
        tabs_file_size = os.path.getsize(tabs_file)
        if tabs_file_size > 0:
            try:
                for tab_name, extra_tab in speedwagon.startup.get_custom_tabs(
                    loaded_workflows, tabs_file
                ):
                    main_window.add_tab(
                        tab_name,
                        collections.OrderedDict(sorted(extra_tab.items())),
                    )
            except speedwagon.exceptions.FileFormatError as error:
                self.logger.warning(
                    "Unable to load custom tabs from %s. Reason: %s",
                    tabs_file,
                    error,
                )

    def save_log(self, parent: QtWidgets.QWidget) -> None:
        data = self._log_data.getvalue()
        epoch_in_minutes = int(time.time() / 60)
        while True:
            log_file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
                parent,
                "Export Log",
                f"speedwagon_log_{epoch_in_minutes}.txt",
                "Text Files (*.txt)",
            )

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
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        dialog.dialogs.SystemInfoDialog(parent).exec()

    def request_settings(
        self, parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        class TabData(typing.NamedTuple):
            name: str
            setup_function: Callable[
                [dialog.settings.MultiSaver], dialog.settings.SettingsTab
            ]
            active: bool

        def are_there_any_plugins() -> bool:
            return len(EntrypointsPluginModelLoader.plugin_entry_points()) > 0

        tabs: List[TabData] = [
            TabData("Workflow Settings", _setup_workflow_settings_tab, True),
            TabData("Global Settings", _setup_global_settings_tab, True),
            TabData("Tabs", _setup_config_tab, True),
            TabData("Plugins", _setup_plugins_tab, are_there_any_plugins()),
        ]
        config_strategy = config.StandardConfigFileLocator()

        dialog_builder = dialog.settings.SettingsBuilder2(parent=parent)
        dialog_builder.app_data_dir = config_strategy.get_app_data_dir()

        saver = dialog.settings.MultiSaver(parent=parent)

        for tab in tabs:
            if tab.active is True:
                dialog_builder.add_tab(tab.name, tab.setup_function(saver))

        def success(_) -> None:
            if self.windows:
                self.windows.clear_tabs()
                self.windows.update_settings()
            self.load_workflows()

        saver.add_success_call_back(success)
        dialog_builder.set_saver_strategy(saver)
        config_dialog: dialog.settings.SettingsDialog = dialog_builder.build()

        config_dialog.exec()

    def start_gui(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        original_hook = sys.excepthook

        # without this, unhandled exceptions won't close the application
        # because QT/PySide keeps the GUI open.
        try:
            sys.excepthook = (
                lambda cls, exception, traceback: gui_exceptions_hook(
                    cls, exception, traceback, self.app, self.windows
                )
            )
            with speedwagon.runner_strategies.BackgroundJobManager() as \
                    job_manager:
                job_manager.global_settings = \
                    self.startup_settings.get("GLOBAL", {})

                self.windows = self.build_main_window(job_manager)
                self._request_window = user_interaction.QtRequestMoreInfo(
                    self.windows
                )
                self.load_workflows()
                self.windows.update_settings()
                self.windows.show()
                return self.app.exec()
        finally:
            sys.excepthook = original_hook

    def build_main_window(
        self, job_manager
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
            lambda workflow_name, options: self.submit_job(
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
        events: runner_strategies.AbsEvents,
    ) -> None:
        dialog_box.stop()
        events.stop()

    def request_more_info(
        self,
        workflow: speedwagon.job.Workflow,
        options: Dict[str, typing.Any],
        pre_results: List[typing.Any],
        wait_condition: Optional[threading.Condition] = None,
    ) -> Optional[Dict[str, typing.Any]]:
        self._request_window.exc = None
        waiter = wait_condition or threading.Condition()
        with waiter:
            self._request_window.request.emit(
                waiter, workflow, options, pre_results
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
        main_app: typing.Optional[gui.MainWindow3] = None,
    ) -> None:
        workflow_class = speedwagon.job.available_workflows().get(
            workflow_name
        )
        try:
            if workflow_class is None:
                raise ValueError(f"Unknown workflow: '{workflow_name}'")
            workflow_class.validate_user_options(**options)
        except ValueError as user_option_error:
            report_exception_dialog(
                exc=user_option_error,
                parent=main_app,
                dialog_box_title="Invalid User Options",
                is_fatal=False,
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
                callbacks=callbacks, events=threaded_events
            ),
        )
        threaded_events.started.set()

    def _find_invalid(
        self, workflows: typing.Dict[str, typing.Type[speedwagon.job.Workflow]]
    ) -> typing.Iterable[typing.Tuple[str, str]]:
        for title, workflow in workflows.copy().items():
            try:
                workflow(
                    global_settings=self.startup_settings.get("GLOBAL", {})
                )
            except (
                speedwagon.exceptions.SpeedwagonException,
                AttributeError,
            ) as error:
                yield title, str(error)


def report_exception_dialog(
    exc: BaseException,
    parent: typing.Optional[QtWidgets.QWidget] = None,
    dialog_box_title: Optional[str] = None,
    is_fatal=True,
) -> None:
    error_dialog = dialog.dialogs.SpeedwagonExceptionDialog(parent)
    if dialog_box_title:
        error_dialog.setWindowTitle(dialog_box_title)
    if is_fatal is True:
        error_dialog.setText(
            "Speedwagon has exited due to an unhandled exception"
        )
    error_dialog.exception = exc
    error_dialog.exec()


def gui_exceptions_hook(
    cls: Type[BaseException],
    exception: BaseException,
    traceback: Optional[types.TracebackType],
    app: Optional[QtWidgets.QApplication] = None,
    window: Optional[QtWidgets.QMainWindow] = None,
) -> None:
    if window:
        window.hide()
    tb.print_tb(traceback)
    report_exception_dialog(exception, window)
    if window:
        window.close()
    print(f"Unhandled exception: {cls.__name__}")
    print("Speedwagon exited prematurely")
    if app is not None:
        app.exit(1)


class TabsEditorApp(QtWidgets.QDialog):
    """Dialog box for editing tabs.yml file."""

    def __init__(self, *args, **kwargs) -> None:
        """Create a tabs editor dialog window."""
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Speedwagon Tabs Editor")
        layout = QtWidgets.QVBoxLayout()
        self.editor = speedwagon.frontend.qtwidgets.dialog.settings.TabEditor()
        # self.editor.tabs_model.
        layout.addWidget(self.editor)
        layout.setContentsMargins(0, 0, 0, 0)
        self.dialog_button_box = QtWidgets.QDialogButtonBox(self)
        layout.addWidget(self.dialog_button_box)

        self.dialog_button_box.setStandardButtons(
            cast(
                QtWidgets.QDialogButtonBox.StandardButton,
                QtWidgets.QDialogButtonBox.StandardButton.Cancel
                | QtWidgets.QDialogButtonBox.StandardButton.Ok,
            )
        )

        self.setLayout(layout)

        # pylint: disable=no-member
        self.dialog_button_box.accepted.connect(self.on_okay)  # type: ignore
        self.dialog_button_box.rejected.connect(self.on_cancel)  # type: ignore
        self.rejected.connect(self.on_cancel)  # type: ignore

    def load_all_workflows(self) -> None:
        self.editor.set_all_workflows()

    def get_tab_config_strategy(self) -> AbsTabsConfigDataManagement:
        config_strategy = config.StandardConfigFileLocator()
        return config.tabs.CustomTabsYamlConfig(
            config_strategy.get_tabs_file()
        )

    def on_okay(self) -> None:
        config_strategy = config.StandardConfigFileLocator()
        tabs_file = config_strategy.get_tabs_file()
        if self.editor.modified is True:
            if tabs_file is None:
                return
            strategy = self.get_tab_config_strategy()
            strategy.save(
                list(
                    filter(
                        lambda tab: tab.tab_name != "All",
                        self.editor.model.tab_information(),
                    )
                )
            )
        self.close()

    def on_cancel(self) -> None:
        self.close()


def standalone_tab_editor(
    app: Optional[QtWidgets.QApplication] = None,
) -> None:
    """Launch standalone tab editor app."""

    print("Loading settings")
    app = app or QtWidgets.QApplication(sys.argv)

    def exception_hook(
        cls: Type[BaseException],
        exception: BaseException,
        traceback: Optional[types.TracebackType],
    ) -> None:
        gui_exceptions_hook(cls, exception, traceback, app=app)

    sys.excepthook = exception_hook

    print("Loading tab editor")
    dialog_box = TabsEditorApp()

    dialog_box.editor.load_data()

    print("displaying tab editor")
    dialog_box.show()
    sys.exit(app.exec())


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
                [speedwagon.frontend.qtwidgets.gui.MainWindow3], None
            ]
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
        self.options = loaded_data["Configuration"]
        self._set_workflow(loaded_data["Workflow"])

    def load(self, file_pointer: io.TextIOBase) -> None:
        """Load the information from the json.

        Args:
            file_pointer: File pointer to json file

        """
        loaded_data = json.load(file_pointer)
        self.options = loaded_data["Configuration"]
        self._set_workflow(loaded_data["Workflow"])

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
            report_exception_dialog(
                parent=None,
                exc=user_option_error,
                dialog_box_title="Invalid User Options",
            )
            return

        dialog_box = dialog.dialogs.WorkflowProgress()

        dialog_box.setWindowTitle(workflow.name or "Workflow")
        dialog_box.show()

        callbacks = (
            speedwagon.frontend.qtwidgets.runners.WorkflowProgressCallbacks(
                dialog_box
            )
        )

        dialog_box.attach_logger(job_manager.logger)
        threaded_events = speedwagon.runner_strategies.ThreadedEvents()
        job_manager.submit_job(
            workflow_name=workflow.name,
            options=options,
            app=self,
            liaison=speedwagon.runner_strategies.JobManagerLiaison(
                callbacks=callbacks, events=threaded_events
            ),
        )
        threaded_events.started.set()
        dialog_box.exec()
        if callable(self.on_exit):
            self.on_exit()

    @staticmethod
    def _load_main_window(
        job_manager: runner_strategies.BackgroundJobManager,
        title: Optional[str],
    ) -> gui.MainWindow3:
        window = speedwagon.frontend.qtwidgets.gui.MainWindow3()
        window.job_manager = job_manager
        if title is not None:
            window.setWindowTitle(title)

        return window
