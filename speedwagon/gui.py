"""Main UI code.

Mainly for connecting GUI elements, such as buttons, to functions and methods
that do the work
"""
import io
import logging
import os
import sys
import time
import traceback
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
import speedwagon.config

__all__ = [
    "MainWindow",
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
    add_log_message = QtCore.pyqtSignal(str)

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        with resources.path("speedwagon.ui",
                            "console.ui") as ui_file:
            uic.loadUi(ui_file, self)

        #  Use a monospaced font based on what's on system running
        monospaced_font = \
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)

        self._log = QtGui.QTextDocument()
        self._log.setDefaultFont(monospaced_font)

        self._console.setDocument(self._log)
        self._console.setFont(monospaced_font)
        self.add_log_message.connect(self.add_message)

    def add_message(self, message: str) -> None:
        cursor = QtGui.QTextCursor(self._log)
        cursor.movePosition(cursor.End)
        cursor.beginEditBlock()
        self._console.setTextCursor(cursor)
        cursor.insertText(message)

        # To get the new line character
        self._console.append(None)
        cursor.endEditBlock()

    @property
    def text(self) -> str:
        return self._log.toPlainText()


class ConsoleLogger(logging.Handler):
    def __init__(self, console: ToolConsole, level=logging.NOTSET) -> None:
        super().__init__(level)
        self.console = console

    def emit(self, record) -> None:

        try:
            self.console.add_log_message.emit(
                self.format(record)
            )
            QtWidgets.QApplication.processEvents()
        except RuntimeError as error:
            print("Error: {}".format(error), file=sys.stderr)
            traceback.print_tb(error.__traceback__)


class ItemTabsWidget(QtWidgets.QWidget):

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        with resources.path("speedwagon.ui",
                            "setup_job.ui") as ui_file:
            uic.loadUi(ui_file, self)

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


class MainWindow(MainProgram):
    def __init__(
            self,
            work_manager: "worker.ToolJobManager",
            debug: bool = False
    ) -> None:

        super().__init__(work_manager, debug)

        with resources.path("speedwagon.ui",
                            "main_window2.ui") as ui_file:
            uic.loadUi(ui_file, self)

        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.addWidget(self.main_splitter)

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

        # ##################

        self.statusBar()

        # ##################
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    def _create_console(self):

        self.console = ToolConsole(self.main_splitter)
        self.console.setMinimumHeight(75)
        self.console.setSizePolicy(CONSOLE_SIZE_POLICY)
        self.main_splitter.addWidget(self.console)
        self.console_log_handler = ConsoleLogger(self.console)
        self._log_data = io.StringIO()
        self.log_data_handler = logging.StreamHandler(self._log_data)
        self.log_data_handler.setFormatter(DEBUG_LOGGING_FORMAT)
        self.log_manager.addHandler(self.console_log_handler)
        self.log_manager.addHandler(self.log_data_handler)

    def _create_tabs_widget(self):
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
            self.console_log_handler.setFormatter(DEBUG_LOGGING_FORMAT)

        else:
            self._set_logging_level(logging.INFO)

    def _set_logging_level(self, level: int) -> None:
        self.console_log_handler.setLevel(level)
        self.log_data_handler.setLevel(level)

    def set_current_tab(self, tab_name: str) -> None:

        size = self.tab_widget.tabs.count()
        for tab in range(size):
            tab_title = self.tab_widget.tabs.tabText(tab)
            if tab_name == tab_title:
                self.tab_widget.tabs.setCurrentIndex(tab)
                return
        self.log_manager.warning("Unable to set tab to {}.".format(tab_name))

    def add_tab(self, workflow_name, workflows):

        workflows_tab = tabs.WorkflowsTab(
            parent=self,
            workflows=workflows,
            work_manager=self.work_manager,
            log_manager=self.log_manager
        )
        workflows_tab.parent = self
        workflows_tab.workflows = workflows
        self._tabs.append(workflows_tab)
        self.tab_widget.add_tab(workflows_tab.tab, workflow_name)
        self.tab_widget.setVisible(True)

    def closeEvent(self, *args, **kwargs) -> None:

        self.log_manager.removeHandler(self.console_log_handler)
        super().closeEvent(*args, **kwargs)

    def show_help(self):
        try:
            pkg_metadata = dict(metadata.metadata(speedwagon.__name__))
            webbrowser.open_new(pkg_metadata['Home-page'])

        except metadata.PackageNotFoundError as error:

            self.log_manager.warning(
                "No help link available. Reason: {}".format(error))

    def show_about_window(self) -> None:
        speedwagon.dialog.dialogs.about_dialog_box(parent=self)

    def show_system_info(self) -> None:
        system_info_dialog = speedwagon.dialog.dialogs.SystemInfoDialog(self)
        system_info_dialog.exec()

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
        with open(log_file_name, "w") as file_handle:
            file_handle.write(data)

        self.log_manager.info("Saved log to {}".format(log_file_name))


class SplashScreenLogHandler(logging.Handler):
    def __init__(self,
                 widget: QtWidgets.QWidget,
                 level: int = logging.NOTSET) -> None:

        super().__init__(level)
        self.widget = widget

    def emit(self, record) -> None:
        self.widget.showMessage(
            self.format(record),
            QtCore.Qt.AlignCenter,
        )
