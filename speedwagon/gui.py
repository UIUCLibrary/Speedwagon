import email
import logging
import os
import sys
import time
import traceback
import webbrowser
from typing import List
import io
import pkg_resources
from PyQt5 import QtWidgets, QtCore, QtGui  # type: ignore
import speedwagon.dialog
import speedwagon.dialog.dialogs
import speedwagon.dialog.settings
from . import tabs, worker
import speedwagon
import speedwagon.startup
import speedwagon.config
from .ui import main_window_shell_ui  # type: ignore
from collections import namedtuple

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

    def __init__(self, parent):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)

        # set only the top margin to 0
        default_style = self.style()

        left_margin = default_style.pixelMetric(
            QtWidgets.QStyle.PM_LayoutLeftMargin)

        right_margin = default_style.pixelMetric(
            QtWidgets.QStyle.PM_LayoutRightMargin)

        bottom_margin = default_style.pixelMetric(
            QtWidgets.QStyle.PM_LayoutBottomMargin)

        layout.setContentsMargins(left_margin, 0, right_margin, bottom_margin)

        self.setLayout(layout)

        self._console = QtWidgets.QTextBrowser(self)
        # self._console.setContentsMargins(0,0,0,0)

        self.layout().addWidget(self._console)

        #  Use a monospaced font based on what's on system running
        monospaced_font = \
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)

        self._log = QtGui.QTextDocument()
        self._log.setDefaultFont(monospaced_font)

        self._console.setSource(self._log.baseUrl())
        self._console.setUpdatesEnabled(True)
        self._console.setFont(monospaced_font)

    def add_message(self, message):
        self._console.append(message)


class ConsoleLogger(logging.Handler):
    def __init__(self, console: ToolConsole, level=logging.NOTSET) -> None:
        super().__init__(level)
        self.console = console
        # self.callback = callback

    def emit(self, record):
        try:
            msg = self.format(record)
            self.console.add_message(msg)
        except RuntimeError as e:
            print("Error: {}".format(e), file=sys.stderr)
            traceback.print_tb(e.__traceback__)


class ItemTabsWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        # QtWidgets.QTabWidget
        layout = QtWidgets.QVBoxLayout(self)

        default_style = self.style()

        left_margin = default_style.pixelMetric(
            QtWidgets.QStyle.PM_LayoutLeftMargin)

        right_margin = default_style.pixelMetric(
            QtWidgets.QStyle.PM_LayoutRightMargin)

        top_margin = default_style.pixelMetric(
            QtWidgets.QStyle.PM_LayoutTopMargin)

        layout.setContentsMargins(left_margin, top_margin, right_margin, 0)

        self.tabs = QtWidgets.QTabWidget()
        self.setLayout(layout)
        self.layout().addWidget(self.tabs)

    def add_tab(self, tab, name):
        self.tabs.addTab(tab, name)


class MainWindow(QtWidgets.QMainWindow, main_window_shell_ui.Ui_MainWindow):
    # noinspection PyUnresolvedReferences
    def __init__(self, work_manager: worker.ToolJobManager, debug=False) -> \
            None:

        super().__init__()
        self._debug = debug
        self.user_settings = None

        self._work_manager = work_manager

        self.log_manager = self._work_manager.logger
        self.log_manager.setLevel(logging.DEBUG)

        # self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.setupUi(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        self.main_splitter = QtWidgets.QSplitter(self.centralwidget)
        self.main_splitter.setOrientation(QtCore.Qt.Vertical)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setSizePolicy(CONSOLE_SIZE_POLICY)

        self.mainLayout.addWidget(self.main_splitter)

        ###########################################################
        # Tabs
        ###########################################################
        # self.tabWidget
        self.tabWidget = ItemTabsWidget(self.main_splitter)
        self.tabWidget.setVisible(False)

        self._tabs: List[speedwagon.tabs.ItemSelectionTab] = []

        # Add the tabs widget as the first widget
        self.tabWidget.setSizePolicy(TAB_WIDGET_SIZE_POLICY)
        self.main_splitter.addWidget(self.tabWidget)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 2)

        ###########################################################
        #  Console
        ###########################################################
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

        self.debug_mode(debug)

        ###########################################################

        # self.main_splitter.set
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

        file_menu.addSeparator()
        # File --> Exit
        # Create Exit button
        exit_button = QtWidgets.QAction(" &Exit", self)
        exit_button.triggered.connect(self.close)

        file_menu.addAction(exit_button)

        system_menu = menu_bar.addMenu("System")

        # System --> Configuration
        # Create a system info menu item

        system_settings_menu_item = \
            QtWidgets.QAction("Settings", self)

        system_settings_menu_item.triggered.connect(
            self.show_configuration)
        system_settings_menu_item.setShortcut("Ctrl+Shift+S")

        system_menu.addAction(system_settings_menu_item)

        # System --> System Info
        # Create a system info menu item
        system_info_menu_item = QtWidgets.QAction("System Info", self)
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

    def debug_mode(self, debug: bool):
        self._debug = debug
        if debug:
            self._set_logging_level(logging.DEBUG)
            self.console_log_handler.setFormatter(DEBUG_LOGGING_FORMAT)

        else:
            self._set_logging_level(logging.INFO)

    def _set_logging_level(self, level):
        self.console_log_handler.setLevel(level)
        self.log_data_handler.setLevel(level)

    def set_current_tab(self, tab_name: str):

        size = self.tabWidget.tabs.count()
        for t in range(size):
            tab_title = self.tabWidget.tabs.tabText(t)
            if tab_name == tab_title:
                self.tabWidget.tabs.setCurrentIndex(t)
                return
        self.log_manager.warning("Unable to set tab to {}.".format(tab_name))

    def add_tools(self, tools):
        tools_tab = tabs.ToolTab(
            parent=self.tabWidget,
            tools=tools,
            work_manager=self._work_manager,
            log_manager=self.log_manager
        )

        self.tabWidget.add_tab(tools_tab.tab, "Tools")
        self._tabs.append(tools_tab)
        self.tabWidget.setVisible(True)

    def add_tab(self, workflow_name, workflows):

        workflows_tab = tabs.WorkflowsTab(
            parent=None,
            workflows=workflows,
            work_manager=self._work_manager,
            log_manager=self.log_manager
        )
        workflows_tab.parent = self
        workflows_tab.workflows = workflows
        self._tabs.append(workflows_tab)
        self.tabWidget.add_tab(workflows_tab.tab, workflow_name)
        self.tabWidget.setVisible(True)

    def closeEvent(self, *args, **kwargs):
        self.log_manager.removeHandler(self.console_log_handler)
        super().closeEvent(*args, **kwargs)

    def show_help(self):
        try:
            distribution = speedwagon.get_project_distribution()

            metadata = dict(email.message_from_string(
                distribution.get_metadata(distribution.PKG_INFO)))

            webbrowser.open_new(metadata['Home-page'])

        except pkg_resources.DistributionNotFound as e:

            self.log_manager.warning(
                "No help link available. Reason: {}".format(e))

    def show_about_window(self):
        speedwagon.dialog.dialogs.about_dialog_box(parent=self)

    def show_system_info(self) -> None:
        system_info_dialog = speedwagon.dialog.dialogs.SystemInfoDialog(self)
        system_info_dialog.exec()

    def show_configuration(self) -> None:

        config_dialog = speedwagon.dialog.settings.SettingsDialog(self)

        if self._work_manager.settings_path is not None:
            config_dialog.settings_location = self._work_manager.settings_path

        global_settings_tab = speedwagon.dialog.settings.GlobalSettingsTab()

        # info_tab = speedwagon.dialog.SettingsPlaceholderInformationTab()
        if self._work_manager.settings_path is not None:
            global_settings_tab.config_file = \
                os.path.join(
                    self._work_manager.settings_path, "config.ini")

            global_settings_tab.read_config_data()

        config_dialog.add_tab(global_settings_tab, "Global Settings")
        config_dialog.accepted.connect(global_settings_tab.on_okay)

        tabs_tab = speedwagon.dialog.settings.SettingsPlaceholderTabsTab()

        if self._work_manager.settings_path is not None:
            tabs_tab.settings_location = \
                os.path.join(self._work_manager.settings_path, "tabs.yaml")

        config_dialog.add_tab(tabs_tab, "Tabs")

        config_dialog.exec()

    def start_workflow(self):
        num_selected = self._workflow_selector_view.selectedIndexes()
        if len(num_selected) != 1:
            print(
                "Invalid number of selected Indexes. "
                "Expected 1. Found {}".format(num_selected)
            )
            return

    def save_log(self):
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
        with open(log_file_name, "w") as f:
            f.write(data)

        self.log_manager.info("Saved log to {}".format(log_file_name))


class SplashScreenLogHandler(logging.Handler):
    def __init__(self, widget, level=logging.NOTSET):
        super().__init__(level)
        self.widget = widget

    def emit(self, record):
        self.widget.showMessage(
            f"{record.msg}",
            QtCore.Qt.AlignCenter,
        )


