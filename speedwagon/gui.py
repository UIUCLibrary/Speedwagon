import argparse
import contextlib
import email
import logging
import sys
import time
import traceback
import webbrowser
from typing import Optional, List
import io
import pkg_resources
from PyQt5 import QtWidgets, QtCore, QtGui
import speedwagon.dialog
from . import job, tabs, worker
import speedwagon
from .ui import main_window_shell_ui  # type: ignore
from collections import namedtuple

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
            self.console.add_message(record.msg)
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
    def __init__(self, work_manager: worker.ToolJobManager) -> None:
        super().__init__()

        self._work_manager = work_manager

        self.log_manager = self._work_manager.logger
        self.log_manager.setLevel(logging.DEBUG)

        # self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.setupUi(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        self.main_splitter = QtWidgets.QSplitter(self.centralwidget)
        self.main_splitter.setOrientation(QtCore.Qt.Vertical)
        self.main_splitter.setChildrenCollapsible(False)

        self.mainLayout.addWidget(self.main_splitter)

        ###########################################################
        # Tabs
        ###########################################################
        # self.tabWidget
        self.tabWidget = ItemTabsWidget(self.main_splitter)
        self.tabWidget.setMinimumHeight(400)

        self._tabs: List[speedwagon.tabs.ItemSelectionTab] = []

        # Add the tabs widget as the first widget
        self.tabWidget.setSizePolicy(TAB_WIDGET_SIZE_POLICY)
        self.main_splitter.addWidget(self.tabWidget)

        ###########################################################
        #  Console
        ###########################################################
        self.console = ToolConsole(self.main_splitter)
        self.console.setMinimumHeight(75)
        self.console.setSizePolicy(CONSOLE_SIZE_POLICY)
        self.main_splitter.addWidget(self.console)
        self._handler = ConsoleLogger(self.console)
        self._handler.setLevel(logging.INFO)
        self.log_manager.addHandler(self._handler)

        self._log_data = io.StringIO()
        self._log_data_handler = logging.StreamHandler(self._log_data)
        self._log_data_handler.setLevel(logging.INFO)
        self.log_manager.addHandler(self._log_data_handler)

        ###########################################################
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 2)
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

        # Help Menu
        help_menu = menu_bar.addMenu("Help")

        # Help --> Help
        # Create a Help menu item
        help_button = QtWidgets.QAction(" &Help ", self)

        help_button.triggered.connect(self.show_help)
        help_menu.addAction(help_button)

        # Help --> System Info
        # Create a system info menu item
        system_info_menu_item = QtWidgets.QAction("System Info", self)
        system_info_menu_item.triggered.connect(self.show_system_info)
        help_menu.addAction(system_info_menu_item)

        help_menu.addSeparator()

        # Help --> About
        # Create an About button
        about_button = QtWidgets.QAction(" &About ", self)
        about_button.triggered.connect(self.show_about_window)

        help_menu.addAction(about_button)

        # ##################

        self.statusBar()

        # ##################
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)


    def set_current_tab(self, tab_name: str):

        size = self.tabWidget.tabs.count()
        for t in range(size):
            tab_title = self.tabWidget.tabs.tabText(t)
            if tab_name == tab_title:
                self.tabWidget.tabs.setCurrentIndex(t)
                return
        self.log_manager.warning("{} not found".format(tab_name))

    def add_tools(self, tools):
        tools_tab = tabs.ToolTab(
            parent=self.tabWidget,
            tools=tools,
            work_manager=self._work_manager,
            log_manager=self.log_manager
        )

        self.tabWidget.add_tab(tools_tab.tab, "Tools")
        self._tabs.append(tools_tab)

    def add_tab(self, workflow_name, workflows):
        workflows_tab = tabs.WorkflowsTab(
            parent=self,
            workflows=workflows,
            work_manager=self._work_manager,
            log_manager=self.log_manager
        )
        self._tabs.append(workflows_tab)
        self.tabWidget.add_tab(workflows_tab.tab, workflow_name)

    def closeEvent(self, *args, **kwargs):
        self.log_manager.removeHandler(self._handler)
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
        speedwagon.dialog.about_dialog_box(parent=self)

    def show_system_info(self) -> None:
        system_info_dialog = speedwagon.dialog.SystemInfoDialog(self)
        system_info_dialog.exec()

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
        log_file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
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
        self.widget.showMessage(record.msg, QtCore.Qt.AlignCenter)


def main(args: Optional[argparse.Namespace] = None) -> None:
    app = QtWidgets.QApplication(sys.argv)

    icon = pkg_resources.resource_stream(__name__, "favicon.ico")
    splash = QtWidgets.QSplashScreen(QtGui.QPixmap(icon.name))

    splash.setEnabled(False)

    splash.setWindowFlags(
        QtCore.Qt.WindowStaysOnTopHint |
        QtCore.Qt.FramelessWindowHint
    )

    splash.show()

    app.setWindowIcon(QtGui.QIcon(icon.name))
    app.setApplicationVersion(f"{speedwagon.__version__}")
    app.setApplicationDisplayName(f"{speedwagon.__name__.title()}")

    with worker.ToolJobManager() as work_manager:
        splash_message_handler = SplashScreenLogHandler(splash)
        splash_message_handler.setLevel(logging.INFO)

        windows = MainWindow(work_manager=work_manager)

        windows.log_manager.addHandler(splash_message_handler)

        windows.log_manager.info(
            f"{speedwagon.__name__.title()} {speedwagon.__version__}"
        )

        windows.log_manager.debug("Loading Tools")

        loading_job_stream = io.StringIO()
        with contextlib.redirect_stderr(loading_job_stream):
            tools = job.available_tools()
            windows.add_tools(tools)

        tool_error_msgs = loading_job_stream.getvalue().strip()
        if tool_error_msgs:
            windows.log_manager.warn(tool_error_msgs)

        windows.log_manager.debug("Loading Workflows")

        loading_workflows_stream = io.StringIO()
        with contextlib.redirect_stderr(loading_workflows_stream):
            workflows = job.available_workflows()
            windows.add_tab("Workflows", workflows)
        workflow_errors_msg = loading_workflows_stream.getvalue().strip()

        if workflow_errors_msg:
            windows.log_manager.warn(workflow_errors_msg)

        windows.log_manager.debug("Loading User Interface ")

        windows.log_manager.removeHandler(splash_message_handler)

        windows.setWindowTitle("")
        if args:
            if args.start_tab:
                windows.set_current_tab(tab_name=args.start_tab)
        splash.finish(windows)
        windows.show()
        windows.log_manager.info("Ready")
        rc = app.exec_()
    sys.exit(rc)


if __name__ == '__main__':
    main()
