"""Start up gui windows."""

from __future__ import annotations
import abc
import collections
import contextlib
import pathlib
from functools import partial
import io
import json
import logging
import os
import sys
import threading
import time
import types
import typing
from typing import (
    Dict, Optional, cast, List, Type, Callable, DefaultDict, Mapping
)
import traceback as tb
import webbrowser
# pylint: disable=wrong-import-position
if sys.version_info >= (3, 10):
    from importlib import metadata
else:
    import importlib_metadata as metadata

from PySide6 import QtWidgets

import speedwagon.job
from speedwagon.config.tabs import CustomTabsYamlConfig, TabsYamlWriter
from speedwagon.workflow import initialize_workflows
from speedwagon.config import config
from speedwagon.config import plugins as plugin_config
from speedwagon.config.workflow import WORKFLOWS_SETTINGS_YML_FILE_NAME
from speedwagon.utils import get_desktop_path, validate_user_input
from speedwagon.tasks import system as system_tasks
from speedwagon import plugins, info
from . import user_interaction
from . import dialog
from . import runners

if typing.TYPE_CHECKING:
    from speedwagon import runner_strategies
    from speedwagon.frontend.qtwidgets import gui
    from speedwagon.frontend.qtwidgets.dialog import dialogs
    from speedwagon.job import AbsWorkflow, AbsJobConfigSerializationStrategy
    from speedwagon.config import FullSettingsData
    from speedwagon.config.tabs import AbsTabsConfigDataManagement
    from speedwagon.workflow import AbsOutputOptionDataType
    import pluggy

__all__ = [
    'AbsGuiStarter',
    'StartQtThreaded',
    'SingleWorkflowJSON'
]

system_info_report_formatters: DefaultDict[
    str,
    Callable[[info.SystemInfo], str]
] = collections.defaultdict(
        lambda: info.system_info_to_text_formatter,
        {
            "Text (*.txt)": info.system_info_to_text_formatter
        }
    )


class AbsGuiStarter(speedwagon.startup.AbsStarter, abc.ABC):
    """Abstract base class to starting a gui application."""

    def __init__(self, app) -> None:
        """Create a new gui starter object."""
        super().__init__()
        self.app = app

    def run(self) -> int:
        """Start gui application."""
        return self.start_gui(self.app)

    @abc.abstractmethod
    def start_gui(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        """Run the gui application."""


def qt_process_file(
    parent: QtWidgets.QWidget,
    process_callback: Callable[[], None],
    error_dialog_title: str,
) -> bool:
    try:
        process_callback()
        return True
    except OSError as error:
        message_box = QtWidgets.QMessageBox(parent)
        message_box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        message_box.setText(error_dialog_title)
        message_box.setDetailedText(str(error))
        message_box.exec()
        return False


def get_default_workflow_config_path() -> str:
    home = pathlib.Path.home()
    return str(home) if os.path.exists(home) else '.'


def save_workflow_config(
    workflow_name: str,
    data: Dict[str, AbsOutputOptionDataType],
    parent: QtWidgets.QWidget,
    dialog_box: typing.Optional[QtWidgets.QFileDialog] = None,
    serialization_strategy: typing.Optional[
        speedwagon.job.AbsJobConfigSerializationStrategy
    ] = None,
) -> None:
    serialization_strategy = (
        serialization_strategy or speedwagon.job.ConfigJSONSerialize()
    )
    default_file_name = f"{workflow_name}.json"
    while True:
        dialog_box = dialog_box or QtWidgets.QFileDialog()
        export_file_name, _ = dialog_box.getSaveFileName(
            parent,
            "Export Job Configuration",
            os.path.join(
                get_default_workflow_config_path(),
                default_file_name
            ),
            "Job Configuration JSON (*.json)",
        )

        if not export_file_name:
            return

        serialization_strategy.file_name = export_file_name
        if (
            qt_process_file(
                parent=parent,
                process_callback=partial(
                    serialization_strategy.save,
                    workflow_name,
                    {k: v.value for k, v in data.items()}
                ),
                error_dialog_title="Export Job Configuration Failed",
            )
            is True
        ):
            confirm_dialog = QtWidgets.QMessageBox(parent)
            confirm_dialog.setText("Exported Job")
            confirm_dialog.exec()
            return


class AbsResolveSettingsStrategy(abc.ABC):  # pylint: disable=R0903
    @abc.abstractmethod
    def get_settings(self) -> FullSettingsData:
        """Get full settings."""


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
                lambda widget: TabsYamlWriter().serialize(
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
                WORKFLOWS_SETTINGS_YML_FILE_NAME,
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
        ini_serializer = config.IniConfigSaver()
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
        ini_serializer = plugin_config.IniSerializer()
        ini_serializer.parser.read(config_file)
        return ini_serializer.serialize(widget.get_data())

    saver.config_savers.append(
        dialog.settings.ConfigFileSaver(
            dialog.settings.SettingsTabSaveStrategy(plugins_tab, serializer),
            config_file
        )
    )
    return plugins_tab


def get_help_url() -> Optional[str]:
    pkg_metadata: metadata.PackageMetadata = metadata.metadata(
        speedwagon.__name__
    )
    urls = pkg_metadata.get_all("Project-URL")
    if urls:
        for value in urls:
            try:
                url_type, url_value = value.split(', ')
            except ValueError as error:
                raise ValueError("malformed entry for Project-URL") from error
            if url_type == "project":
                return url_value.strip()
    return None


class StartQtThreaded(AbsGuiStarter):
    """Start a Qt Widgets base app using threads for job workers."""

    def __init__(self, app: Optional[QtWidgets.QApplication] = None) -> None:
        """Create a new starter object."""
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
        """Import workflow configuration to parent."""
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
            home_page = get_help_url()
            if home_page:
                webbrowser.open_new(home_page)
            else:
                self.logger.warning(
                    "No help link available. "
                    "Reason: no project url located in Project-URL package "
                    "metadata"
                )
        except metadata.PackageNotFoundError as error:
            self.logger.warning("No help link available. Reason: %s", error)

    def ensure_settings_files(self) -> None:
        """Ensure settings files exists."""
        config.ensure_settings_files(logger=self.logger)

    def resolve_settings(self) -> FullSettingsData:
        """Resolve settings."""
        settings = self.settings_resolver.get_settings()
        self.platform_settings._data.update(settings.get("GLOBAL", {}))
        self.startup_settings = settings
        return self.startup_settings

    def initialize(self) -> None:
        """Initialize the application before opening the main window."""
        startup_tasks: List[system_tasks.AbsSystemTask] = [
            system_tasks.EnsureGlobalConfigFiles(self.logger),
        ]

        plugin_manager = plugins.get_plugin_manager(
            plugins.register_whitelisted_plugins
        )

        for plugin_tasks in \
                plugin_manager.hook.registered_initialization_tasks():
            startup_tasks += plugin_tasks

        for task in startup_tasks:
            task.run()

        self.startup_settings = self.resolve_settings()

    def load_workflows(self) -> None:
        """Load workflows."""
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
        """Load tab that contains all workflows."""
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
        """Load custom tabs."""
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
        """Action for user to save logs as a file."""
        data = self._log_data.getvalue()
        epoch_in_minutes = int(time.time() / 60)

        log_saved = export_logs_action(
            parent,
            default_file_name=f"speedwagon_log_{epoch_in_minutes}.txt",
            data=data,
        )
        if log_saved:
            self.logger.info("Saved log to %s", log_saved)

    @staticmethod
    def request_system_info(
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        """Action to open up system info dialog box."""
        system_info_dialog = dialog.dialogs.SystemInfoDialog(
            system_info=info.SystemInfo(), parent=parent
        )
        system_info_dialog.export_to_file.connect(export_system_info_to_file)
        system_info_dialog.exec()

    def request_settings(
        self, parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        """Open dialog box for settings."""

        class TabData(typing.NamedTuple):
            name: str
            setup_function: Callable[
                [dialog.settings.MultiSaver], dialog.settings.SettingsTab
            ]
            active: bool

        def are_there_any_plugins() -> bool:
            def no_builtins(manager: pluggy.PluginManager) -> None:
                manager.load_setuptools_entrypoints('speedwagon.plugins')

            plugin_manager = \
                speedwagon.plugins.get_plugin_manager(no_builtins)
            return len(plugin_manager.get_plugins()) > 0

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
        """Start gui application."""
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
        """Build main window widget."""
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
        """Abort job."""
        dialog_box.stop()
        events.stop()

    def request_more_info(
        self,
        workflow: speedwagon.job.Workflow,
        options: Mapping[str, object],
        pre_results: List[speedwagon.tasks.Result[typing.Any]],
        wait_condition: Optional[threading.Condition] = None,
    ) -> Optional[Mapping[str, typing.Any]]:
        """Request more information from the user."""
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
        options: Dict[str, AbsOutputOptionDataType],
        main_app: typing.Optional[gui.MainWindow3] = None,
    ) -> None:
        """Submit job."""
        workflow_class = speedwagon.job.available_workflows().get(
            workflow_name
        )

        def serialize_options(options):
            return {
                option.setting_name if option.setting_name
                else option.label: option.value
                for option in options.values()
            }

        try:
            if workflow_class is None:
                raise ValueError(f"Unknown workflow: '{workflow_name}'")

            if findings := validate_user_input(options):
                raise ValueError(generate_findings_report(findings))

            workflow_class.validate_user_options(**serialize_options(options))
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
            def _rejected():
                QtWidgets.QApplication.processEvents()
                main_app.close()
            dialog_box.rejected.connect(_rejected)  # type: ignore

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
        job_manager.request_more_info = self.request_more_info
        job_manager.submit_job(
            workflow_name=workflow_name,
            options=serialize_options(options),
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
        return CustomTabsYamlConfig(
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
        """Create an environment where the workflow is loaded from a json file.

        Args:
            app: Qt application
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


def export_system_info_to_file(
        file: str,
        file_type: str,
        writer=info.write_system_info_to_file
) -> None:
    writer(info.SystemInfo(), file, system_info_report_formatters[file_type])


def get_default_log_path() -> str:
    try:
        return get_desktop_path()
    except FileNotFoundError:
        return str(pathlib.Path.home())


def export_logs_action(
    parent: QtWidgets.QWidget, default_file_name: str, data: str
) -> Optional[str]:
    def save_file(file_name: str) -> None:
        with open(file_name, "w", encoding="utf-8") as file_handle:
            file_handle.write(data)

    while True:
        log_file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent,
            "Export Log",
            os.path.join(get_default_log_path(), default_file_name),
            "Text Files (*.txt)",
        )

        if not log_file_name:
            return None

        if (
            qt_process_file(
                parent=parent,
                process_callback=partial(save_file, log_file_name),
                error_dialog_title="Saving Log Failed",
            )
            is True
        ):
            return log_file_name


def generate_findings_report(findings: Dict[str, List[str]]) -> str:
    error_lines = ["errors with the following options"]
    error_lines += [
        f"{key}: {', '.join(value)}" for key, value in findings.items()
    ]
    return "\n".join(error_lines)
