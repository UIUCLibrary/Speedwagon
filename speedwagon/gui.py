"""Main UI code.

Mainly for connecting GUI elements, such as buttons, to functions and methods
that do the work
"""
import io
import logging
import logging.handlers
import os
import time
import typing
import webbrowser
from typing import List

try:  # pragma: no cover
    from importlib import metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore

try:  # pragma: no cover
    from importlib import resources
except ImportError:  # pragma: no cover
    import importlib_resources as resources  # type: ignore

from collections import namedtuple

from PyQt5 import QtWidgets, QtCore, QtGui  # type: ignore
from PyQt5 import uic
import speedwagon.dialog
import speedwagon.dialog.dialogs
import speedwagon.dialog.settings
from speedwagon import tabs, worker
import speedwagon
import speedwagon.ui
import speedwagon.config
import speedwagon.runner_strategies
from speedwagon.logging_helpers import ConsoleFormatter

__all__ = [
    "MainWindow1",
    "SplashScreenLogHandler"
]

DEBUG_LOGGING_FORMAT = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

TAB_WIDGET_SIZE_POLICY = QtWidgets.QSizePolicy(
    QtWidgets.QSizePolicy.MinimumExpanding,
    QtWidgets.QSizePolicy.Maximum
)

CONSOLE_SIZE_POLICY = QtWidgets.QSizePolicy(
    QtWidgets.QSizePolicy.MinimumExpanding,
    QtWidgets.QSizePolicy.Minimum
)

Setting = namedtuple("Setting", ("installed_packages_title", "widget"))


class ToolConsole(QtWidgets.QWidget):
    """Logging console."""

    class ConsoleLogHandler(logging.handlers.BufferingHandler):
        class Signals(QtCore.QObject):
            message = QtCore.pyqtSignal(str)

        def __init__(self, console_widget: "ToolConsole"):
            super().__init__(capacity=100)
            self.signals = ToolConsole.ConsoleLogHandler.Signals()
            self.console_widget = console_widget
            self.signals.message.connect(self.console_widget.add_message)

        def flush(self) -> None:
            if len(self.buffer) > 0:
                message_buffer = [
                    self.format(record) for record in self.buffer
                ]
                self.signals.message.emit(" ".join(message_buffer))
            super().flush()

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.log_handler = ToolConsole.ConsoleLogHandler(self)

        self.log_formatter = ConsoleFormatter()
        self.log_handler.setFormatter(self.log_formatter)

        with resources.path(speedwagon.ui, "console.ui") as ui_file:
            uic.loadUi(ui_file, self)

        # ======================================================================
        # Type hints:
        self._console: QtWidgets.QTextBrowser
        # ======================================================================

        #  Use a monospaced font based on what's on system running
        monospaced_font = \
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)

        self._log = QtGui.QTextDocument()
        self._log.setDefaultFont(monospaced_font)
        self._log.contentsChanged.connect(self._follow_text)
        self._console.setDocument(self._log)
        self._console.setFont(monospaced_font)

        self._attached_logger: typing.Optional[logging.Logger] = None

    def close(self) -> bool:
        self.detach_logger()
        return super().close()

    def _follow_text(self) -> None:
        cursor = QtGui.QTextCursor(self._log)
        cursor.movePosition(cursor.End)
        self._console.setTextCursor(cursor)

    @QtCore.pyqtSlot(str)
    def add_message(
            self,
            message: str,
    ) -> None:

        cursor = QtGui.QTextCursor(self._log)
        cursor.movePosition(cursor.End)
        cursor.beginEditBlock()
        self._console.setTextCursor(cursor)
        cursor.insertHtml(message)
        cursor.endEditBlock()

    @property
    def text(self) -> str:
        return self._log.toPlainText()

    def attach_logger(self, logger: logging.Logger) -> None:
        logger.addHandler(self.log_handler)
        self._attached_logger = logger

    def detach_logger(self) -> None:
        if self._attached_logger is not None:
            self.log_handler.flush()
            self._attached_logger.removeHandler(self.log_handler)
            self._attached_logger = None


class ItemTabsWidget(QtWidgets.QWidget):

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        with resources.path(speedwagon.ui, "setup_job.ui") as ui_file:
            uic.loadUi(ui_file, self)
        # ======================================================================
        # Type Hints
        self.tabs: QtWidgets.QTabWidget
        # ======================================================================
        self.layout().addWidget(self.tabs)

    def add_tab(self, tab: QtWidgets.QWidget, name: str) -> None:
        self.tabs.addTab(tab, name)


class MainProgram(QtWidgets.QMainWindow):
    def __init__(
            self,
            work_manager: "worker.ToolJobManager",
            debug: bool = False
    ) -> None:
        super().__init__()

        self._debug = debug
        self.user_settings = None

        self.work_manager = work_manager

        self.log_manager = self.work_manager.logger
        self.log_manager.setLevel(logging.DEBUG)

    def debug_mode(self, debug: bool) -> None:
        self._debug = debug


class MainWindowMenuBuilder:
    def __init__(self, parent: QtWidgets.QMainWindow) -> None:
        self._parent = parent
        self._menu_bar: QtWidgets.QMenuBar = self._parent.menuBar()

        self.add_help: bool = True
        self.add_about: bool = True

        self.show_configuration_signal: \
            typing.Optional[typing.Callable[[], None]] = None

        self.show_system_info_signal: \
            typing.Optional[typing.Callable[[], None]] = None

        self.exit_function: typing.Optional[typing.Callable[[], bool]] = None

        self.save_log_function: \
            typing.Optional[typing.Callable[[], None]] = None

        self.export_signal: typing.Optional[typing.Callable[[], None]] = None
        self.import_signal: typing.Optional[typing.Callable[[], None]] = None

    def build(self) -> None:
        self._build_file_menu(self._menu_bar)

        self._build_job_menu(self._menu_bar)
        self._build_system_menu(self._menu_bar)

        self._build_help(self._menu_bar)

    def _build_system_menu(self, menu_bar: QtWidgets.QMenuBar) -> None:
        system_menu = menu_bar.addMenu("System")
        system_menu.setObjectName("systemMenu")

        self._build_config_action(system_menu)
        self._build_system_info_action(system_menu)

    def _build_system_info_action(self, system_menu: QtWidgets.QMenu) -> None:
        # System --> System Info
        # Create a system info menu item
        if self.show_system_info_signal is not None:

            system_info_menu_item = QtWidgets.QAction(
                "System Info",
                self._parent
            )

            system_info_menu_item.setObjectName("systemInfoAction")

            system_info_menu_item.triggered.connect(
                self.show_system_info_signal
            )
            system_menu.addAction(system_info_menu_item)

    def _build_config_action(self, system_menu: QtWidgets.QMenu) -> None:
        # System --> Configuration
        # Create a system info menu item
        if self.show_configuration_signal is not None:
            system_settings_menu_item = \
                QtWidgets.QAction("Settings", self._parent)

            system_settings_menu_item.setObjectName('settingsAction')

            system_settings_menu_item.triggered.connect(
                self.show_configuration_signal)

            system_settings_menu_item.setShortcut("Ctrl+Shift+S")
            system_menu.addAction(system_settings_menu_item)

    def _build_file_menu(self, menu_bar: QtWidgets.QMenuBar) -> None:

        # File Menu
        file_menu = menu_bar.addMenu("File")
        self._build_export_log_action(file_menu)
        self._build_exit_action(file_menu)

    def _build_exit_action(self, file_menu: QtWidgets.QMenu) -> None:
        # File --> Exit
        # Create Exit button
        if self.exit_function is not None:
            exit_button = QtWidgets.QAction(" &Exit", self._parent)
            exit_button.setObjectName("exitAction")

            exit_button.triggered.connect(self.exit_function)
            file_menu.addAction(exit_button)

    def _build_export_log_action(self, file_menu: QtWidgets.QMenu) -> None:
        # File --> Export Log
        if self.save_log_function is not None:

            export_logs_button = QtWidgets.QAction(
                " &Export Log",
                self._parent
            )

            export_logs_button.setIcon(
                self._parent.style().standardIcon(
                    QtWidgets.QStyle.SP_DialogSaveButton)
            )
            export_logs_button.triggered.connect(self.save_log_function)
            # export_logs_button.triggered.connect(self._parent.save_log)
            file_menu.addAction(export_logs_button)
            file_menu.setObjectName("fileMenu")
            file_menu.addAction(export_logs_button)
            file_menu.setObjectName("fileMenu")
            file_menu.addSeparator()

    def _build_help(self, menu_bar: QtWidgets.QMenuBar) -> None:
        # Help Menu
        help_menu = menu_bar.addMenu("Help")

        if self.add_help is True:
            # Help --> Help
            # Create a Help menu item
            help_button = QtWidgets.QAction(" &Help ", self._parent)
            help_button.triggered.connect(self._parent.help_requested)
            help_menu.addAction(help_button)

        if self.add_about is True:
            # Help --> About
            # Create an About button
            about_button = QtWidgets.QAction(" &About ", self._parent)
            about_button.triggered.connect(self._parent.show_about_window)
            help_menu.addAction(about_button)

    def _build_job_menu(self, menu_bar: QtWidgets.QMenuBar) -> None:
        job_menu = menu_bar.addMenu("Job")
        job_menu.setObjectName("jobMenu")

        if self.export_signal is not None:
            export_button = QtWidgets.QAction(
                "Export",
                self._parent
            )

            export_button.triggered.connect(self.export_signal)
            job_menu.addAction(export_button)

        if self.import_signal is not None:
            import_button = QtWidgets.QAction(
                "Import",
                self._parent
            )

            import_button.triggered.connect(self.import_signal)
            job_menu.addAction(import_button)


class MainWindow1(MainProgram):
    def __init__(
            self,
            work_manager: "worker.ToolJobManager",
            debug: bool = False
    ) -> None:

        super().__init__(work_manager, debug)
        with resources.path(speedwagon.ui, "main_window2.ui") as ui_file:
            self.load_ui_file(str(ui_file))

        # ======================================================================
        # Type hints
        # ======================================================================
        self.main_layout: QtWidgets.QVBoxLayout
        self.main_splitter: QtWidgets.QSplitter
        # ======================================================================

        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.main_splitter)

        ###########################################################
        # Tabs
        ###########################################################
        self._create_tabs_widget()

        ###########################################################
        #  Console
        ###########################################################
        self._create_console()

        ###########################################################
        self.debug_mode(debug)
        self.setup_menu()

        # ##################

        self.statusBar()

        # ##################
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    def load_ui_file(self, ui_file: str) -> None:
        uic.loadUi(ui_file, self)

    def show_about_window(self) -> None:
        speedwagon.dialog.dialogs.about_dialog_box(parent=self)

    def show_system_info(self) -> None:
        system_info_dialog = speedwagon.dialog.dialogs.SystemInfoDialog(self)
        system_info_dialog.exec()

    def show_help(self) -> None:
        try:
            pkg_metadata = dict(metadata.metadata(speedwagon.__name__))
            webbrowser.open_new(pkg_metadata['Home-page'])
        except metadata.PackageNotFoundError as error:
            self.log_manager.warning(
                "No help link available. Reason: {}".format(error))

    def setup_menu(self) -> None:
        # Add menu bar
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("File")

        # File --> Export Log
        export_logs_button = QtWidgets.QAction(" &Export Log", self)
        export_logs_button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton)
        )
        export_logs_button.triggered.connect(self.save_log)

        file_menu.addAction(export_logs_button)
        file_menu.setObjectName("fileMenu")
        file_menu.addAction(export_logs_button)
        file_menu.setObjectName("fileMenu")
        file_menu.addSeparator()

        # File --> Exit
        # Create Exit button
        exit_button = QtWidgets.QAction(" &Exit", self)
        exit_button.setObjectName("exitAction")
        exit_button.triggered.connect(QtWidgets.QApplication.exit)
        file_menu.addAction(exit_button)
        system_menu = menu_bar.addMenu("System")
        system_menu.setObjectName("systemMenu")

        # System --> Configuration
        # Create a system info menu item
        system_settings_menu_item = \
            QtWidgets.QAction("Settings", self)
        system_settings_menu_item.setObjectName('settingsAction')

        system_settings_menu_item.triggered.connect(
            self.show_configuration)

        system_settings_menu_item.setShortcut("Ctrl+Shift+S")
        system_menu.addAction(system_settings_menu_item)

        # System --> System Info
        # Create a system info menu item
        system_info_menu_item = QtWidgets.QAction("System Info", self)
        system_info_menu_item.setObjectName("systemInfoAction")
        system_info_menu_item.triggered.connect(self.show_system_info)
        system_menu.addAction(system_info_menu_item)

        # Help Menu
        help_menu = menu_bar.addMenu("Help")

        # Help --> Help
        # Create a Help menu item
        help_button = QtWidgets.QAction(" &Help ", self)
        help_button.triggered.connect(self.show_help)
        help_menu.addAction(help_button)

        # Help --> About
        # Create an About button
        about_button = QtWidgets.QAction(" &About ", self)
        about_button.triggered.connect(self.show_about_window)
        help_menu.addAction(about_button)

    def _create_console(self) -> None:

        self.console = ToolConsole(self.main_splitter)
        self.console.setMinimumHeight(75)
        self.console.setSizePolicy(CONSOLE_SIZE_POLICY)
        self.main_splitter.addWidget(self.console)
        self._log_data = io.StringIO()
        self.log_data_handler = logging.StreamHandler(self._log_data)
        self.log_data_handler.setFormatter(DEBUG_LOGGING_FORMAT)
        self.log_manager.addHandler(self.log_data_handler)

    def _create_tabs_widget(self) -> None:
        self.tab_widget = ItemTabsWidget(self.main_splitter)
        self.tab_widget.setVisible(False)
        self._tabs: List[speedwagon.tabs.ItemSelectionTab] = []
        # Add the tabs widget as the first widget
        self.tab_widget.setSizePolicy(TAB_WIDGET_SIZE_POLICY)
        self.main_splitter.addWidget(self.tab_widget)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 2)

    def debug_mode(self, debug: bool) -> None:
        """Set debug mode on or off."""
        super().debug_mode(debug)
        if debug:
            self._set_logging_level(logging.DEBUG)
            self.console.log_handler.setFormatter(DEBUG_LOGGING_FORMAT)

        else:
            self._set_logging_level(logging.INFO)

    def _set_logging_level(self, level: int) -> None:
        self.console.log_handler.setLevel(level)
        self.log_data_handler.setLevel(level)

    def set_current_tab(self, tab_name: str) -> None:

        size = self.tab_widget.tabs.count()
        for tab in range(size):
            tab_title = self.tab_widget.tabs.tabText(tab)
            if tab_name == tab_title:
                self.tab_widget.tabs.setCurrentIndex(tab)
                return
        self.log_manager.warning("Unable to set tab to {}.".format(tab_name))

    def add_tab(
            self,
            workflow_name: str,
            workflows: typing.Dict[str, typing.Type[speedwagon.Workflow]]
    ) -> None:

        workflows_tab = tabs.WorkflowsTab(
            parent=self,
            workflows=workflows,
            work_manager=self.work_manager,
            log_manager=self.log_manager
        )
        workflows_tab.parent = self
        workflows_tab.workflows = workflows
        self._tabs.append(workflows_tab)
        self.tab_widget.add_tab(workflows_tab.tab_widget, workflow_name)
        self.tab_widget.setVisible(True)

    def closeEvent(self, *args, **kwargs) -> None:  # pylint: disable=C0103
        super().closeEvent(*args, **kwargs)

    def show_configuration(self) -> None:

        config_dialog = speedwagon.dialog.settings.SettingsDialog(parent=self)

        if self.work_manager.settings_path is not None:
            config_dialog.settings_location = self.work_manager.settings_path

        global_settings_tab = speedwagon.dialog.settings.GlobalSettingsTab()

        if self.work_manager.settings_path is not None:
            global_settings_tab.config_file = \
                os.path.join(
                    self.work_manager.settings_path, "config.ini")

            global_settings_tab.read_config_data()

        config_dialog.add_tab(global_settings_tab, "Global Settings")
        config_dialog.accepted.connect(global_settings_tab.on_okay)

        tabs_tab = speedwagon.dialog.settings.TabsConfigurationTab()

        if self.work_manager.settings_path is not None:
            tabs_tab.settings_location = \
                os.path.join(self.work_manager.settings_path, "tabs.yml")
            tabs_tab.load()

        config_dialog.add_tab(tabs_tab, "Tabs")
        config_dialog.accepted.connect(tabs_tab.on_okay)

        config_dialog.exec()

    def start_workflow(self) -> None:
        num_selected = self._workflow_selector_view.selectedIndexes()
        if len(num_selected) != 1:
            print(
                "Invalid number of selected Indexes. "
                "Expected 1. Found {}".format(num_selected)
            )

    def save_log(self) -> None:
        data = self._log_data.getvalue()

        epoch_in_minutes = int(time.time() / 60)
        log_file_name, _ = \
            QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Export Log",
                "speedwagon_log_{}.txt".format(epoch_in_minutes),
                "Text Files (*.txt)")

        if not log_file_name:
            return
        with open(log_file_name, "w", encoding="utf-8") as file_handle:
            file_handle.write(data)

        self.log_manager.info("Saved log to {}".format(log_file_name))


MainWindow = MainWindow1


class MainWindow2UI(QtWidgets.QMainWindow):

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)
        with resources.path(speedwagon.ui, "main_window2.ui") as ui_file:
            uic.loadUi(ui_file, self)

        # ======================================================================
        # Type hints
        # ======================================================================
        self.main_layout: QtWidgets.QVBoxLayout
        self.main_splitter: QtWidgets.QSplitter
        # ======================================================================


class MainWindow2(MainWindow2UI):
    submit_job = QtCore.pyqtSignal(str, dict)
    configuration_requested = QtCore.pyqtSignal(QtWidgets.QWidget)
    system_info_requested = QtCore.pyqtSignal(QtWidgets.QWidget)
    help_requested = QtCore.pyqtSignal()
    save_logs_requested = QtCore.pyqtSignal(QtWidgets.QWidget)
    export_job_config = QtCore.pyqtSignal(str, dict, QtWidgets.QWidget)
    import_job_config = QtCore.pyqtSignal(QtWidgets.QWidget)

    def __init__(
            self,
            job_manager: "speedwagon.runner_strategies.BackgroundJobManager",
            settings: typing.Optional[
                typing.Dict[str, typing.Union[str, bool]]
            ] = None
            ) -> None:
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.job_manager = job_manager
        self.user_settings = settings or {}

        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.main_splitter)

        ###########################################################
        # Tabs
        ###########################################################
        self._create_tabs_widget()

        ###########################################################
        #  Console
        ###########################################################
        self._create_console()
        self.setup_menu()
        ###########################################################

    def set_current_tab(self, tab_name: str) -> None:
        tab_index = self.locate_tab_index_by_name(tab_name)
        if tab_index is None:
            raise IndexError(f"No tab named {tab_name}")
        self.tab_widget.tabs.setCurrentIndex(tab_index)

    def locate_tab_index_by_name(self, name) -> typing.Optional[int]:
        for index in range(self.tab_widget.tabs.count()):
            if self.tab_widget.tabs.tabText(index) == name:
                return index
        return None

    def set_active_workflow(self, workflow_name: str) -> None:
        tab_index = self.locate_tab_index_by_name("All")
        if tab_index is None:
            raise AssertionError("Missing All tab")
        all_tab = self._tabs[tab_index]
        for i in range(all_tab.item_selector_view.model().rowCount()):
            workflow_index = all_tab.item_selector_view.model().index(i, 0)
            name = workflow_index.data()
            if name == workflow_name:
                all_tab.item_selector_view.setCurrentIndex(workflow_index)

    def set_current_workflow_settings(
            self,
            data: typing.Dict[str, typing.Any]
    ):
        tab_index = self.locate_tab_index_by_name("All")
        if tab_index is None:
            raise AssertionError("Missing All tab")
        all_tab = self._tabs[tab_index]
        model = all_tab.workspace_widgets[tabs.TabWidgets.SETTINGS].model()
        for key, value in data.items():
            model[key] = value

    def close(self) -> bool:
        self.console.close()
        return super().close()

    def closeEvent(  # pylint: disable=C0103
            self,
            event: QtGui.QCloseEvent
    ) -> None:
        self.console.close()
        super().closeEvent(event)

    def setup_menu(self) -> None:
        builder = MainWindowMenuBuilder(parent=self)
        builder.exit_function = lambda: self.close()

        builder.show_system_info_signal = \
            lambda: self.system_info_requested.emit(self)

        builder.show_configuration_signal = \
            lambda: self.configuration_requested.emit(self)

        builder.save_log_function = self.save_log

        builder.export_signal = lambda: self.export_job_config.emit(
            self.get_current_workflow_name(),
            self.get_current_job_settings(),
            self
        )

        builder.import_signal = lambda: self.import_job_config.emit(self)

        builder.add_help = True
        builder.build()

    def get_current_workflow_name(self) -> str:
        current_tab_index = self.tab_widget.tabs.currentIndex()

        item_selected_index = \
            self._tabs[
                current_tab_index
            ].item_selector_view.selectedIndexes()[0]

        return \
            self._tabs[
                current_tab_index
            ].item_selection_model.data(item_selected_index,
                                        QtCore.Qt.UserRole).name

    def get_current_job_settings(self) -> typing.Dict[str, typing.Any]:
        return \
            self._tabs[self.tab_widget.tabs.currentIndex()].options_model.get()

    def add_tab(
            self,
            tab_name: str,
            workflows: typing.Mapping[
                str,
                typing.Type[speedwagon.job.Workflow]
            ]
    ) -> None:

        workflows_tab = tabs.WorkflowsTab2(
            parent=self,
            workflows=workflows,
        )
        workflows_tab.tab_name = tab_name
        workflows_tab.signals.start_workflow.connect(self._start_workflow)

        workflows_tab.parent = self
        self._tabs.append(workflows_tab)
        self.tab_widget.add_tab(workflows_tab.tab_widget, tab_name)
        self.tab_widget.setVisible(True)

    def _start_workflow(self,
                        workflow: str,
                        options: typing.Dict[str, typing.Any]) -> None:
        self.submit_job.emit(workflow, options)

    def show_about_window(self) -> None:
        speedwagon.dialog.dialogs.about_dialog_box(parent=self)

    def save_log(self) -> None:
        self.save_logs_requested.emit(self)

    def _create_tabs_widget(self) -> None:
        self.tab_widget = ItemTabsWidget(self.main_splitter)
        self.tab_widget.setVisible(False)
        self._tabs: List[speedwagon.tabs.ItemSelectionTab] = []

        # Add the tabs widget as the first widget
        self.tab_widget.setSizePolicy(TAB_WIDGET_SIZE_POLICY)
        self.main_splitter.addWidget(self.tab_widget)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 2)

    def _create_console(self) -> None:

        self.console = ToolConsole(self.main_splitter)
        self.console.log_formatter.verbose = \
            typing.cast(
                bool,
                self.user_settings.get('debug', False)
            )

        self.console.setMinimumHeight(75)
        self.console.setSizePolicy(CONSOLE_SIZE_POLICY)
        self.main_splitter.addWidget(self.console)


class SplashScreenLogHandler(logging.Handler):
    def __init__(self,
                 widget: QtWidgets.QWidget,
                 level: int = logging.NOTSET) -> None:

        super().__init__(level)
        self.widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        self.widget.showMessage(
            self.format(record),
            QtCore.Qt.AlignCenter,
        )
