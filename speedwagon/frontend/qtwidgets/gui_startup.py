"""Start up gui windows."""

from __future__ import annotations
import abc
import collections
import contextlib
import functools
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
    Dict,
    Optional,
    cast,
    List,
    Type,
    Callable,
    DefaultDict,
    Mapping,
)
import traceback as tb
import webbrowser

# pylint: disable=wrong-import-position
if sys.version_info >= (3, 10):
    from importlib import metadata
else:
    import importlib_metadata as metadata

from PySide6 import QtWidgets, QtCore

import speedwagon.job
from speedwagon.frontend.qtwidgets.models.tabs import TabDataModelConfigLoader
from speedwagon.workflow import initialize_workflows

from speedwagon.config.tabs import CustomTabsYamlConfig, TabsYamlWriter
from speedwagon.config.config import (
    StandardConfigFileLocator,
    get_platform_settings,
    IniConfigManager,
    StandardConfig,
)
from speedwagon.config.common import DEFAULT_CONFIG_DIRECTORY_NAME
from speedwagon.config import plugins as plugin_config
from speedwagon.config.workflow import locate_workflow_settings_yaml
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
    from speedwagon.frontend.qtwidgets.dialog.settings import (
        AbsConfigSaverCallbacks
    )

    from speedwagon.job import (
        AbsWorkflow,
        AbsWorkflowFinder,
        AbsJobConfigSerializationStrategy,
        Workflow,
    )
    from speedwagon.config.common import SettingsDataType
    from speedwagon.config.config import AbsSettingLocator
    from speedwagon.config import FullSettingsData
    from speedwagon.config.workflow import AbsWorkflowBackend
    from speedwagon.config.tabs import AbsTabsConfigDataManagement
    from speedwagon.workflow import AbsOutputOptionDataType
    import pluggy

__all__ = ["AbsGuiStarter", "StartQtThreaded", "SingleWorkflowJSON"]

system_info_report_formatters: DefaultDict[
    str, Callable[[info.SystemInfo], str]
] = collections.defaultdict(
    lambda: info.system_info_to_text_formatter,
    {"Text (*.txt)": info.system_info_to_text_formatter},
)


class AbsGuiStarter(speedwagon.startup.AbsStarter, abc.ABC):
    """Abstract base class to starting a gui application."""

    @staticmethod
    def get_default_settings_strategy() -> AbsResolveSettingsStrategy:
        """Get default settings strategy."""
        settings_resolver = ResolveSettings()
        settings_resolver.config_file_locator_strategy = (
            lambda: StandardConfigFileLocator(
                DEFAULT_CONFIG_DIRECTORY_NAME
            ).get_config_file()
        )
        return settings_resolver

    def __init__(
        self,
        app: Optional[QtWidgets.QApplication],
        config: speedwagon.config.AbsConfigSettings,
    ) -> None:
        """Create a new gui starter object."""
        super().__init__()
        self.app = app
        self.config = config

    @property
    def settings(self) -> FullSettingsData:
        """Complete settings for session."""
        return self.config.application_settings()

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
    return str(home) if os.path.exists(home) else "."


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
                get_default_workflow_config_path(), default_file_name
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
                    {k: v.value for k, v in data.items()},
                ),
                error_dialog_title="Export Job Configuration Failed",
            )
            is True
        ):
            confirm_dialog = QtWidgets.QMessageBox(parent)
            confirm_dialog.setText("Exported Job")
            confirm_dialog.exec()
            return


def locate_config_file(config_directory_prefix: str) -> str:
    return StandardConfigFileLocator(
        config_directory_prefix
    ).get_config_file()


class AbsResolveSettingsStrategy(abc.ABC):  # pylint: disable=R0903
    def __init__(self) -> None:
        self.config_file_locator_strategy: Callable[[], str] = (
            lambda: locate_config_file(DEFAULT_CONFIG_DIRECTORY_NAME)
        )

    @abc.abstractmethod
    def get_settings(self) -> FullSettingsData:
        """Get full settings."""


class ResolveSettings(AbsResolveSettingsStrategy):  # pylint: disable=R0903
    def get_settings(self) -> FullSettingsData:
        manager = IniConfigManager(self.config_file_locator_strategy())
        return manager.data()


def get_active_workflows(
    config_file: str,
    workflow_finder: Optional[AbsWorkflowFinder] = None
) -> Dict[str, Type[Workflow]]:
    workflow_finder = (
        workflow_finder or
        speedwagon.job.OnlyActivatedPluginsWorkflows(
            plugin_settings=plugin_config.read_settings_file_plugins(
                config_file
            )
        )
    )
    return speedwagon.job.available_workflows(workflow_finder)


def _setup_config_tab(
    saver: dialog.settings.MultiSaver,
    locate_tabs_file_strategy: Callable[[], str] = lambda: _get_tabs_file(
        DEFAULT_CONFIG_DIRECTORY_NAME
    ),
    config_file_location_strategy: Callable[
        [], str
    ] = lambda: StandardConfigFileLocator(
        config_directory_prefix=DEFAULT_CONFIG_DIRECTORY_NAME
    ).get_config_file(),
) -> dialog.settings.TabsConfigurationTab:

    tabs_config = dialog.settings.TabsConfigurationTab()
    model_loader = TabDataModelConfigLoader(
        tabs_manager=CustomTabsYamlConfig(locate_tabs_file_strategy())
    )
    model_loader.get_all_active_workflows_strategy = functools.partial(
        get_active_workflows, config_file=config_file_location_strategy()
    )
    tabs_config.load_tab_data_model_strategy = model_loader
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
            locate_tabs_file_strategy(),
        )
    )
    return tabs_config


def _setup_workflow_settings_tab(
    saver: dialog.settings.MultiSaver,
    workflow_settings_location_strategy: Callable[
        [], str
    ] = lambda: locate_workflow_settings_yaml(DEFAULT_CONFIG_DIRECTORY_NAME),
) -> dialog.settings.ConfigWorkflowSettingsTab:
    workflow_settings_tab = dialog.settings.ConfigWorkflowSettingsTab()
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
                ),
            ),
            workflow_settings_location_strategy(),
        )
    )
    # Only add workflows to the configuration if it has something to
    # configure. Otherwise, this gets overly cluttered.
    workflow_settings_tab.set_workflows(
        filter(
            lambda workflow: len(workflow.workflow_options()) != 0,
            initialize_workflows(
                workflow_settings_location_strategy
            ),
        )
    )
    return workflow_settings_tab


def save_global_tab_widget_settings(config_file, tab) -> None:
    ini_manager = IniConfigManager(config_file)
    ini_manager.save(
        {
            "GLOBAL": typing.cast(
                speedwagon.config.SettingsData,
                tab.get_data()
            )
        }
    )


def _setup_global_settings_tab(
    saver: dialog.settings.MultiSaver,
    config_file_location_strategy: Callable[
        [], str
    ] = lambda: locate_config_file(DEFAULT_CONFIG_DIRECTORY_NAME),
) -> dialog.settings.GlobalSettingsTab:
    global_settings_tab = dialog.settings.GlobalSettingsTab()
    config_file = config_file_location_strategy()

    saver.config_savers.append(
        dialog.settings.CallbackSaver(
            save_data_callback_func=functools.partial(
                save_global_tab_widget_settings,
                config_file=config_file,
                tab=global_settings_tab
            )
        )
    )
    global_settings_tab.load_ini_file(config_file)
    return global_settings_tab


def _setup_plugins_tab(
    saver: dialog.settings.MultiSaver,
    config_file_location_strategy: Callable[
        [], str
    ] = lambda: StandardConfigFileLocator(
        config_directory_prefix=DEFAULT_CONFIG_DIRECTORY_NAME
    ).get_config_file(),
) -> dialog.settings.PluginsTab:
    config_file = config_file_location_strategy()
    plugins_tab = dialog.settings.PluginsTab()
    plugins_tab.load(config_file)

    def serializer(widget) -> str:
        ini_serializer = plugin_config.IniSerializer()
        ini_serializer.parser.read(config_file)
        return ini_serializer.serialize(widget.get_data())

    saver.config_savers.append(
        dialog.settings.ConfigFileSaver(
            dialog.settings.SettingsTabSaveStrategy(plugins_tab, serializer),
            config_file,
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
                url_type, url_value = value.split(", ")
            except ValueError as error:
                raise ValueError("malformed entry for Project-URL") from error
            if url_type == "project":
                return url_value.strip()
    return None


def _get_tabs_file(config_directory_prefix: str) -> str:
    config_strategy = StandardConfigFileLocator(
        config_directory_prefix=config_directory_prefix
    )
    return config_strategy.get_tabs_file()


class StartQtThreaded(AbsGuiStarter):
    """Start a Qt Widgets base app using threads for job workers."""

    def __init__(
        self,
        config: Optional[speedwagon.config.AbsConfigSettings] = None,
        app: Optional[QtWidgets.QApplication] = None,
    ) -> None:
        """Create a new starter object."""
        super().__init__(app, config or StandardConfig())
        self._application_name: Optional[str] = None
        self.config_files_locator: AbsSettingLocator =\
            StandardConfigFileLocator(
                config_directory_prefix=DEFAULT_CONFIG_DIRECTORY_NAME
            )

        self.startup_settings: FullSettingsData = {"GLOBAL": {"debug": False}}

        self.windows: Optional[gui.MainWindow3] = None
        self.logger = logging.getLogger()
        self._settings_builder = LocalSettingsBuilder(
            app_data_dir=self.config_locations.get_app_data_dir(),
        )
        formatter = logging.Formatter(
            "%(asctime)-15s %(threadName)s %(message)s"
        )

        self.platform_settings = get_platform_settings()
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

    @property
    def config_locations(self) -> AbsSettingLocator:
        """Get config."""
        return self.config_files_locator

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

    def set_application_name(self, name: str) -> None:
        """Set the Qt application name and the window matching."""
        self._application_name = name

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

    def resolve_settings(self) -> FullSettingsData:
        """Resolve settings."""
        self.platform_settings._data.update(self.settings.get("GLOBAL", {}))
        self.startup_settings = self.settings
        return self.startup_settings

    def initialize(self) -> None:
        """Initialize the application before opening the main window."""
        startup_tasks: List[system_tasks.AbsSystemTask] = [
            system_tasks.EnsureGlobalConfigFiles(
                self.logger,
                directory_prefix=self.config_locations.get_app_data_dir(),
            ),
        ]

        plugin_manager = plugins.get_plugin_manager(
            plugins.register_whitelisted_plugins
        )

        for (
            plugin_tasks
        ) in plugin_manager.hook.registered_initialization_tasks():
            startup_tasks += plugin_tasks

        for task in startup_tasks:
            task.set_config_backend(self.config)
            task.run()

        self.startup_settings = self.resolve_settings()

    def load_workflows(self) -> None:
        """Load workflows."""
        if self.windows is None:
            return

        self.logger.debug("Loading Workflows")
        loading_workflows_stream = io.StringIO()
        self.windows.clear_tabs()

        with contextlib.redirect_stderr(loading_workflows_stream):
            all_workflows = speedwagon.job.available_workflows(
                strategy=speedwagon.job.OnlyActivatedPluginsWorkflows(
                    plugin_settings=plugin_config.read_settings_file_plugins(
                        self.config_locations.get_config_file()
                    )
                )
            )

        for workflow_name, error in self._find_invalid(all_workflows):
            error_message = (
                f"Unable to load workflow '{workflow_name}'. Reason: {error}"
            )

            self.logger.error(error_message)
            self.windows.console.add_message(error_message)
            del all_workflows[workflow_name]

        # Load every user configured tab
        self.load_custom_tabs(
            self.windows, self.config_locations.get_tabs_file(), all_workflows
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

        def success(_) -> None:
            if self.windows:
                self.windows.clear_tabs()
                self.windows.update_settings()
            self.load_workflows()
        self._settings_builder.reset()
        self._settings_builder.on_success_save_updated_settings = success
        get_config_file = self.config_locations.get_config_file
        get_tabs_file = self.config_locations.get_tabs_file

        self._settings_builder.add_tab(
            "Workflow Settings",
            functools.partial(
                _setup_workflow_settings_tab,
                workflow_settings_location_strategy=lambda:
                locate_workflow_settings_yaml(
                    self.config_locations.get_app_data_dir()
                ),
            ),
        )
        self._settings_builder.add_tab(
            "Global Settings",
            functools.partial(
                _setup_global_settings_tab,
                config_file_location_strategy=get_config_file,
            ),
        )
        self._settings_builder.add_tab(
            "Tabs",
            functools.partial(
                _setup_config_tab,
                locate_tabs_file_strategy=get_tabs_file,
                config_file_location_strategy=get_config_file,
            ),
        )

        def are_there_any_plugins() -> bool:
            def no_builtins(manager: pluggy.PluginManager) -> None:
                manager.load_setuptools_entrypoints("speedwagon.plugins")

            plugin_manager = speedwagon.plugins.get_plugin_manager(no_builtins)
            return len(plugin_manager.get_plugins()) > 0

        self._settings_builder.add_tab(
            "Plugins",
            functools.partial(
                _setup_plugins_tab,
                config_file_location_strategy=get_config_file,
            ),
            active=are_there_any_plugins(),
        )
        settings_dialog = self._settings_builder.build(parent=parent)
        settings_dialog()

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

            with (
                speedwagon.runner_strategies.BackgroundJobManager() as
                job_manager
            ):
                job_manager.global_settings = self.startup_settings.get(
                    "GLOBAL", {}
                )

                self.windows = self.build_main_window(job_manager)

                self._request_window = user_interaction.QtRequestMoreInfo(
                    self.windows
                )
                self.load_workflows()
                self.windows.update_settings()
                self.windows.show()
                if self._application_name is not None:
                    QtCore.QCoreApplication.setApplicationName(
                        self._application_name
                    )
                    self.windows.setWindowTitle(
                        QtCore.QCoreApplication.applicationName()
                    )
                return self.app.exec()
        finally:
            sys.excepthook = original_hook

    def build_main_window(
        self, job_manager
    ) -> speedwagon.frontend.qtwidgets.gui.MainWindow3:
        """Build main window widget."""
        window = speedwagon.frontend.qtwidgets.gui.MainWindow3()
        window.session_config = self.config

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
                option.setting_name
                if option.setting_name
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
        self.tabs_file_locator_strategy = lambda: _get_tabs_file(
            DEFAULT_CONFIG_DIRECTORY_NAME
        )
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
        return CustomTabsYamlConfig(self.tabs_file_locator_strategy())

    def on_okay(self) -> None:
        if self.editor.modified is True:
            if self.tabs_file_locator_strategy() is None:
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

    def __init__(
        self,
        app,
        config: Optional[speedwagon.config.AbsConfigSettings] = None,
        logger: Optional[logging.Logger] = None
    ) -> None:
        """Create an environment where the workflow is loaded from a json file.

        Args:
            app: Qt application
            config: Speedwagon config
            logger: Optional Logger, defaults to default logger for __name__.
        """
        super().__init__(app, config or StandardConfig())
        self.global_settings = None
        self.on_exit: typing.Optional[
            Callable[
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
        with (
            speedwagon.runner_strategies.BackgroundJobManager() as job_manager
        ):
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
    file: str, file_type: str, writer=info.write_system_info_to_file
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


class ResolveSettingsStrategyConfigAdapter(
    speedwagon.config.AbsConfigSettings
):
    def __init__(
        self,
        source_application_settings: AbsResolveSettingsStrategy,
        workflow_backend: Callable[[Workflow], AbsWorkflowBackend]
    ):
        self.application_source = source_application_settings
        self.workflow_backend = workflow_backend

    def application_settings(self) -> FullSettingsData:
        return self.application_source.get_settings()

    def workflow_settings(
        self,
        workflow: speedwagon.job.Workflow
    ) -> Mapping[str, SettingsDataType]:
        return self.workflow_backend(workflow)


class LocalSettingsBuilder:
    class TabData(typing.NamedTuple):
        name: str
        setup_function: Callable[
            [dialog.settings.AbsConfigSaverCallbacks],
            dialog.settings.SettingsTab
        ]
        active: bool

    def __init__(self, app_data_dir: str) -> None:
        self.app_data_dir = app_data_dir
        self.tabs: List[LocalSettingsBuilder.TabData] = []
        self.on_success_save_updated_settings: Callable[
            [typing.Any],
            None
        ] = lambda *_: None

    def reset(self) -> None:
        self.tabs.clear()
        self.on_success_save_updated_settings = lambda *_: None

    def add_tab(
        self,
        name: str,
        setup_function: Callable[
            [dialog.settings.AbsConfigSaverCallbacks],
            dialog.settings.SettingsTab
        ],
        active: bool = True
    ) -> None:
        self.tabs.append(
            LocalSettingsBuilder.TabData(name, setup_function, active)
        )

    def _build_tabs(
        self,
        dialog_builder: dialog.settings.SettingsBuilder2,
        saver: AbsConfigSaverCallbacks
    ) -> None:
        for tab in self.tabs:
            if tab.active is True:
                dialog_builder.add_tab(tab.name, tab.setup_function(saver))

    def build(self, parent: Optional[QtWidgets.QWidget]) -> Callable[[], None]:
        dialog_builder = dialog.settings.SettingsBuilder2(parent=parent)
        dialog_builder.app_data_dir = self.app_data_dir

        saver = dialog.settings.MultiSaver(parent=parent)
        self._build_tabs(dialog_builder, saver)
        saver.add_success_call_back(self.on_success_save_updated_settings)
        dialog_builder.set_saver_strategy(saver)
        config_dialog: dialog.settings.SettingsDialog = dialog_builder.build()

        def run() -> None:
            config_dialog.exec()
        return run
