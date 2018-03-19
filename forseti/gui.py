import logging
import sys
import traceback

import pkg_resources
from PyQt5 import QtWidgets, QtCore, QtGui
import forseti.tool
import forseti.job
import forseti.workflow
from forseti.tabs import ToolTab, WorkflowsTab
from forseti.ui import main_window_shell_ui
from forseti import tool as tool_, worker
from collections import namedtuple

TAB_WIDGET_SIZE_POLICY = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Maximum)

CONSOLE_SIZE_POLICY = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum)

PROJECT_NAME = "Forseti"

Setting = namedtuple("Setting", ("label", "widget"))


class ToolConsole(QtWidgets.QWidget):

    def __init__(self, parent):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)
        self._console = QtWidgets.QTextBrowser(self)
        self._console.setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._console)

        #  Use a monospaced font based on what's on system running
        monospaced_font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
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


class MainWindow(QtWidgets.QMainWindow, main_window_shell_ui.Ui_MainWindow):
    # noinspection PyUnresolvedReferences
    def __init__(self, work_manager: worker.ToolJobManager, tools, workflows) -> None:
        super().__init__()
        self._work_manager = work_manager

        self.log_manager = self._work_manager.logger
        self.log_manager.setLevel(logging.DEBUG)

        self.setupUi(self)

        self.main_splitter = QtWidgets.QSplitter(self.tabWidget)
        self.main_splitter.setOrientation(QtCore.Qt.Vertical)
        self.main_splitter.setChildrenCollapsible(False)

        self.mainLayout.addWidget(self.main_splitter)



        ###########################################################
        # Tabs
        ###########################################################

        self.tools_tab = ToolTab(parent=self,
                                 tools=tools,
                                 work_manager=self._work_manager,
                                 log_manager=self.log_manager)
        self.tabWidget.addTab(self.tools_tab.tab, "Tools")


        self.workflows_tab = WorkflowsTab(parent=self,
                                          workflows=workflows,
                                          work_manager=self._work_manager,
                                          log_manager=self.log_manager)
        self.tabWidget.addTab(self.workflows_tab.tab, "Workflows")
        # self.tabWidget.setMinimumHeight(100)

        # Add the tabs widget as the first widget
        self.tabWidget.setSizePolicy(TAB_WIDGET_SIZE_POLICY)
        # self.main_splitter.setHandleWidth(10)
        self.main_splitter.addWidget(self.tabWidget)


        ###########################################################
        #  Console
        ###########################################################
        self.console = self.create_console()
        self.console.setMinimumHeight(50)
        self.console.setSizePolicy(CONSOLE_SIZE_POLICY)
        # self.tabWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Maximum))
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
        message = f"Forseti" \
                  f"\n" \
                  f"\n" \
                  f"Collection of tools and workflows for DS" \
                  f"\n" \
                  f"\n" \
                  f"Version {forseti.__version__}"

        QtWidgets.QMessageBox.about(self, "About", message)

    # def _update_tool_selected(self, current, previous):
    #     self.tools_tab._update_tool_selected(current, previous)
    #     # try:
    #     #     self._tool_selected(current)
    #     #     self.tool_settings.resizeRowsToContents()
    #     #     self._tool_mapper.setCurrentModelIndex(current)
    #     # except Exception as e:
    #     #     self._tool_selected(previous)
    #     #     self.tool_settings.resizeRowsToContents()
    #     #     self._tool_mapper.setCurrentModelIndex(previous)
    #     #     self._tool_selector_view.setCurrentIndex(previous)
    #
    # def _update_workflow_selected(self, current, previous):
    #
    #     try:
    #         self._tool_selected(current)
    #         self.tool_settings.resizeRowsToContents()
    #         self._tool_mapper.setCurrentModelIndex(current)
    #     except Exception as e:
    #         self._tool_selected(previous)
    #         self.tool_settings.resizeRowsToContents()
    #         self._tool_mapper.setCurrentModelIndex(previous)
    #         self._tool_selector_view.setCurrentIndex(previous)
    #
    # def _on_success(self, results, callback):
    #     self.tools_tab.tab._on_success(results, callback)
    #     # self.log_manager.info("Done!")
    #     # user_args = self._tool_options_model.get()
    #     # callback(results=results, user_args=user_args)
    #     # report = self._tool.generate_report(results=results, user_args=user_args)
    #     # if report:
    #     #     line_sep = "\n" + "*" * 60
    #     #
    #     #     fancy_report = f"{line_sep}" \
    #     #                    f"\n   Report" \
    #     #                    f"{line_sep}" \
    #     #                    f"\n" \
    #     #                    f"\n{report}" \
    #     #                    f"\n" \
    #     #                    f"{line_sep}"
    #     #
    #     #     # self.log_manager.notify(fancy_report)
    #     #     self.log_manager.info(fancy_report)
    #     #
    #     # # self._tool.setup_task(results=results,user_args=user_args)
    #     #
    #     # # QtWidgets.QMessageBox.about(self, "Finished", "Finished")
    #
    # def _on_failed(self, exc):
    #     self.tools_tab.tab._on_failed(exc)
    #     # self.log_manager.error("Process failed. Reason: {}".format(exc))
    #     # print("************** {}".format(exc))
    #     # if exc:
    #     #     # self.log_manager.notify(str(exc))
    #     #     self.log_manager.warning(str(exc))
    #     #     exception_message = traceback.format_exception(type(exc), exc, tb=exc.__traceback__)
    #     #     msg = QtWidgets.QMessageBox(self)
    #     #     msg.setIcon(QtWidgets.QMessageBox.Warning)
    #     #     msg.setWindowTitle(str(type(exc).__name__))
    #     #     msg.setText(str(exc))
    #     #     msg.setDetailedText("".join(exception_message))
    #     #     msg.exec_()
    #     # # raise exc
    #     # sys.exit(1)
    #
    # def _start_tool(self):
    #     self.tools_tab._start_tool()
    #
    # #     # # logger = logging.getLogger(__name__)
    # #     # # logger.debug("Start button pressed")
    # #     # if len(self._tool_selector_view.selectedIndexes()) != 1:
    # #     #     print("Invalid number of selected Indexes. Expected 1. Found {}".format(
    # #     #         len(self._tool_selector_view.selectedIndexes())))
    # #     #     return
    # #     #
    # #     # tool = self._tools_model.data(self._tool_selector_view.selectedIndexes()[0], QtCore.Qt.UserRole)
    # #     # if issubclass(tool, forseti.tools.abstool.AbsTool):
    # #     #     options = self._tool_options_model.get()
    # #     #     self._tool = tool
    # #     #
    # #     #     # wrapped_strat = runner_strategies.UsingWorkWrapper()
    # #     #     # runner = runner_strategies.RunRunner(wrapped_strat)
    # #     #     manager_strat = runner_strategies.UsingExternalManager(manager=self.work_manager)
    # #     #     # manager_strat = runner_strategies.UsingWorkManager()
    # #     #     runner = runner_strategies.RunRunner(manager_strat)
    # #     #
    # #     #     runner.run(self, tool, options, self._on_success, self._on_failed, self.work_manager.logger)
    # #     #
    # #     # else:
    # #     #     QtWidgets.QMessageBox.warning(self, "No op", "No tool selected.")

    def start_workflow(self):
        if len(self._workflow_selector_view.selectedIndexes()) != 1:
            print("Invalid number of selected Indexes. Expected 1. Found {}".format(
                len(self._workflow_selector_view.selectedIndexes())))
            return

    # def _tool_selected(self, index: QtCore.QModelIndex):
    #     self.tools_tab._tool_selected(index)
    #     # tool = self._tools_model.data(index, QtCore.Qt.UserRole)
    #     # # model.
    #     # # self.tool_workspace.set_tool(tool)
    #     # #################
    #     # try:
    #     #     self._tool_options_model = tool_.ToolOptionsModel3(tool.get_user_options())
    #     #
    #     #     self.tool_settings.setModel(self._tool_options_model)
    #     # except Exception as e:
    #     #     message = "Unable to use {} as it's not fully implemented".format(tool.name)
    #     #     QtWidgets.QMessageBox.warning(self, "Tool settings error", message)
    #     #     self.log_manager.warning(message)
    #     #     raise

    def create_console(self):
        console = ToolConsole(self.main_splitter)

        return console


def main():
    app = QtWidgets.QApplication(sys.argv)
    icon = pkg_resources.resource_stream(__name__, "favicon.ico")
    app.setWindowIcon(QtGui.QIcon(icon.name))
    app.setApplicationVersion(f"{forseti.__version__}")
    app.setApplicationDisplayName(f"{PROJECT_NAME}")
    tools = tool_.available_tools()
    workflows = forseti.workflow.available_workflows()
    with worker.ToolJobManager() as work_manager:

        windows = MainWindow(work_manager=work_manager, tools=tools, workflows=workflows)
        windows.setWindowTitle("")
        # windows.setWindowTitle(f"Version {forseti.__version__}")
        rc = app.exec_()
    sys.exit(rc)


if __name__ == '__main__':
    main()
