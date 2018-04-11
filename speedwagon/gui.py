import logging
import sys
import traceback
from . import about
import pkg_resources
from PyQt5 import QtWidgets, QtCore, QtGui
from . import job, tabs
import speedwagon.tabs
from .ui import main_window_shell_ui  # type: ignore
from . import worker
from collections import namedtuple

TAB_WIDGET_SIZE_POLICY = QtWidgets.QSizePolicy(
    QtWidgets.QSizePolicy.MinimumExpanding,
    QtWidgets.QSizePolicy.Maximum
)

CONSOLE_SIZE_POLICY = QtWidgets.QSizePolicy(
    QtWidgets.QSizePolicy.MinimumExpanding,
    QtWidgets.QSizePolicy.Minimum
)

Setting = namedtuple("Setting", ("label", "widget"))


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

        layout.setContentsMargins(left_margin, 0, right_margin, 0)

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

    def addTab(self, w, name):
        self.tabs.addTab(w, name)

class MainWindow(QtWidgets.QMainWindow, main_window_shell_ui.Ui_MainWindow):
    # noinspection PyUnresolvedReferences
    def __init__(self, work_manager: worker.ToolJobManager, tools,
                 workflows) -> None:
        super().__init__()
        self._work_manager = work_manager

        self.log_manager = self._work_manager.logger
        self.log_manager.setLevel(logging.DEBUG)

        # self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.setupUi(self)

        self.main_splitter = QtWidgets.QSplitter()
        # self.mainLayout.setContentsMargins(10,10,10,10)
        # self.centralwidget.setContentsMargins(10,10,10,10,)
        self.main_splitter.setOrientation(QtCore.Qt.Vertical)
        self.main_splitter.setChildrenCollapsible(False)
        # self.main_splitter.setLayout(self.mainLayout)

        self.mainLayout.addWidget(self.main_splitter)

        ###########################################################
        # Tabs
        ###########################################################
        # self.tabWidget
        self.tabWidget = ItemTabsWidget(self.main_splitter)

        # self.tabWidget
        # self.tabWidget.setLayout(l)

        self.tools_tab = tabs.ToolTab(
            parent=self.tabWidget,
            tools=tools,
            work_manager=self._work_manager,
            log_manager=self.log_manager
        )

        self.tabWidget.addTab(self.tools_tab.tab, "Tools")

        self.workflows_tab = tabs.WorkflowsTab(
            parent=self,
            workflows=workflows,
            work_manager=self._work_manager,
            log_manager=self.log_manager
        )

        self.tabWidget.addTab(self.workflows_tab.tab, "Workflows")
        # self.tabWidget.setMinimumHeight(100)

        # Add the tabs widget as the first widget
        self.tabWidget.setSizePolicy(TAB_WIDGET_SIZE_POLICY)
        # self.main_splitter.setHandleWidth(10)
        # self.tabWidget.setContentsMargins(0,0,10,0)
        self.main_splitter.addWidget(self.tabWidget)

        ###########################################################
        #  Console
        ###########################################################
        self.console = ToolConsole(self.main_splitter)
        self.console.setMinimumHeight(50)
        self.console.setSizePolicy(CONSOLE_SIZE_POLICY)
        self.main_splitter.addWidget(self.console)
        self._handler = ConsoleLogger(self.console)
        self._handler.setLevel(logging.INFO)
        self.log_manager.addHandler(self._handler)
        self.log_manager.info("READY!")
        ###########################################################
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 2)
        # self.main_splitter.set
        # Add menu bar
        menu_bar = self.menuBar()

        # File Menu

        file_menu = menu_bar.addMenu("File")

        # Create Exit button
        exit_button = QtWidgets.QAction("Exit", self)
        exit_button.triggered.connect(self.close)

        file_menu.addAction(exit_button)

        # Help Menu
        help_menu = menu_bar.addMenu("Help")

        # Create an About button
        about_button = QtWidgets.QAction("About", self)
        about_button.triggered.connect(self.show_about_window)

        help_menu.addAction(about_button)

        # ##################

        self.statusBar()

        # ##################
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Show Window
        self.show()

    def closeEvent(self, *args, **kwargs):
        self.log_manager.removeHandler(self._handler)
        super().closeEvent(*args, **kwargs)

    def show_about_window(self):
        about.about_dialog_box(parent=self)

    def start_workflow(self):
        num_selected = self._workflow_selector_view.selectedIndexes()
        if len(num_selected) != 1:
            print(
                "Invalid number of selected Indexes. "
                "Expected 1. Found {}".format(num_selected)
            )
            return


def main():
    app = QtWidgets.QApplication(sys.argv)
    icon = pkg_resources.resource_stream(__name__, "favicon.ico")
    app.setWindowIcon(QtGui.QIcon(icon.name))
    app.setApplicationVersion(f"{speedwagon.__version__}")
    app.setApplicationDisplayName(f"{speedwagon.__name__.title()}")
    tools = job.available_tools()
    workflows = job.available_workflows()
    with worker.ToolJobManager() as work_manager:
        windows = MainWindow(work_manager=work_manager,
                             tools=tools,
                             workflows=workflows)

        windows.setWindowTitle("")
        # windows.setWindowTitle(f"Version {speedwagon.__version__}")
        rc = app.exec_()
    sys.exit(rc)


if __name__ == '__main__':
    main()
