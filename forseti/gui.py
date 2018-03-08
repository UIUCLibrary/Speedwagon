import logging
import sys
import typing

import abc

from PyQt5 import QtWidgets, QtCore, QtGui
import forseti.tool
import forseti.tools.abstool
import forseti.workflow
from forseti.tools import options
from forseti.ui import main_window_shell_ui
from forseti import tool as tool_, worker, runner_strategies
from collections import namedtuple
import traceback

PROJECT_NAME = "Forseti"

Setting = namedtuple("Setting", ("label", "widget"))


class ToolConsole(QtWidgets.QGroupBox):

    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle("Console")
        layout = QtWidgets.QVBoxLayout()
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
        self.console.add_message(record.msg)


class AbsTab(metaclass=abc.ABCMeta):
    def __init__(self, parent, work_manager, log_manager):
        self.log_manager = log_manager
        self.parent = parent
        self.work_manager = work_manager

        self.tab, self.tab_tools_layout = self.create_tab()

    @abc.abstractmethod
    def compose_tab_layout(self):
        pass

    @abc.abstractmethod
    def create_actions(self):
        pass

    @staticmethod
    def create_tools_settings_view(parent):
        tool_settings = QtWidgets.QTableView(parent=parent)
        tool_settings.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        tool_settings.setItemDelegate(MyDelegate(parent))
        tool_settings.horizontalHeader().setVisible(False)
        tool_settings.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        tool_settings.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        tool_settings.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        tool_settings.verticalHeader().setSectionsClickable(False)
        return tool_settings

    @classmethod
    def create_config_layout(cls, parent):

        tool_config_layout = QtWidgets.QFormLayout()

        tool_name_line = QtWidgets.QLineEdit()
        tool_name_line.setReadOnly(True)

        tool_description_information = QtWidgets.QTextBrowser()

        tool_settings = cls.create_tools_settings_view(parent)

        tool_config_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)
        tool_config_layout.addRow(QtWidgets.QLabel("Selected"), tool_name_line)
        tool_config_layout.addRow(QtWidgets.QLabel("Description"), tool_description_information)
        tool_config_layout.addRow(QtWidgets.QLabel("Settings"), tool_settings)

        widgets = {
            "name": tool_name_line,
            "description": tool_description_information,
            "settings": tool_settings,
        }
        return widgets, tool_config_layout

    @staticmethod
    def create_workspace(title):
        tool_workspace = QtWidgets.QGroupBox()
        workspace2_layout = QtWidgets.QVBoxLayout()

        tool_workspace.setTitle(title)
        tool_workspace.setLayout(workspace2_layout)
        return tool_workspace, workspace2_layout

    @staticmethod
    def create_tab() -> typing.Tuple[QtWidgets.QWidget, QtWidgets.QLayout]:
        tab_tools = QtWidgets.QWidget()
        tab_tools.setObjectName("tab")
        tab_tools_layout = QtWidgets.QVBoxLayout(tab_tools)
        tab_tools_layout.setObjectName("tab_tools_layout")
        return tab_tools, tab_tools_layout



class ToolTab(AbsTab):
    def __init__(self, parent, tools, work_manager, log_manager):
        super().__init__(parent, work_manager, log_manager)
        self._tool_options_model = None

        # Create model for tool options
        self._tools_model = tool_.ToolsListModel(tools)

        # =============================

        self.tool_workspace, self.workspace_layout = self.create_workspace("Tool")
        self.config_widgets, self.tool_config_layout = self.create_config_layout(parent)
        self.workspace_layout.addLayout(self.tool_config_layout)
        self.actions, self._tool_actions_layout = self.create_actions()
        # =============================

        self._tool_selector_view = self.create_selector_view(parent, model=self._tools_model)
        self._tool_mapper = self.create_tool_mapper(self.parent, self.config_widgets, model=self._tools_model)

        self.compose_tab_layout()

    def compose_tab_layout(self):
        self.tab_tools_layout.addWidget(self._tool_selector_view)
        self.tab_tools_layout.addWidget(self.tool_workspace)
        self.tab_tools_layout.addLayout(self._tool_actions_layout)

    @staticmethod
    def create_tool_mapper(parent, config_widgets, model):
        tool_mapper = QtWidgets.QDataWidgetMapper(parent)
        tool_mapper.setModel(model)
        tool_mapper.addMapping(config_widgets['name'], 0)
        # This needs custom mapping because without it, new line characters are removed
        tool_mapper.addMapping(config_widgets['description'], 1, b"plainText")
        return tool_mapper



    def create_selector_view(self, parent, model):
        selector_view = QtWidgets.QListView(parent)
        selector_view.setMinimumHeight(100)
        selector_view.setModel(model)
        selector_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        selector_view.selectionModel().currentChanged.connect(self._update_tool_selected)
        return selector_view



    def create_actions(self) -> typing.Tuple[typing.Dict[str, QtWidgets.QWidget], QtWidgets.QLayout]:
        tool_actions_layout = QtWidgets.QHBoxLayout()

        start_button = QtWidgets.QPushButton()
        start_button.setText("Start")
        start_button.clicked.connect(self._start_tool)

        tool_actions_layout.addSpacerItem(QtWidgets.QSpacerItem(0, 40, QtWidgets.QSizePolicy.Expanding))
        tool_actions_layout.addWidget(start_button)
        actions = {
            "start_button": start_button
        }
        return actions, tool_actions_layout


    def on_failed(self, exc):
        self.log_manager.error("Process failed. Reason: {}".format(exc))
        print("************** {}".format(exc))
        if exc:
            # self.log_manager.notify(str(exc))
            self.log_manager.warning(str(exc))
            exception_message = traceback.format_exception(type(exc), exc, tb=exc.__traceback__)
            msg = QtWidgets.QMessageBox(self.parent)
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle(str(type(exc).__name__))
            msg.setText(str(exc))
            msg.setDetailedText("".join(exception_message))
            msg.exec_()

    def on_success(self, results, callback):
        self.log_manager.info("Done!")
        user_args = self._tool_options_model.get()
        callback(results=results, user_args=user_args)
        report = self._tool.generate_report(results=results, user_args=user_args)
        if report:
            line_sep = "\n" + "*" * 60

            fancy_report = f"{line_sep}" \
                           f"\n   Report" \
                           f"{line_sep}" \
                           f"\n" \
                           f"\n{report}" \
                           f"\n" \
                           f"{line_sep}"

            # self.log_manager.notify(fancy_report)
            self.log_manager.info(fancy_report)

        # self._tool.on_completion(results=results,user_args=user_args)

        # QtWidgets.QMessageBox.about(self, "Finished", "Finished")

    def _update_tool_selected(self, current, previous):
        tool_settings = self.config_widgets['settings']
        try:
            self._tool_selected(current)
            tool_settings.resizeRowsToContents()
            self._tool_mapper.setCurrentModelIndex(current)
        except Exception as e:
            self._tool_selected(previous)
            tool_settings.resizeRowsToContents()
            self._tool_mapper.setCurrentModelIndex(previous)
            self._tool_selector_view.setCurrentIndex(previous)

    def _tool_selected(self, index: QtCore.QModelIndex):
        tool = self._tools_model.data(index, QtCore.Qt.UserRole)
        tool_settings = self.config_widgets['settings']
        # model.
        # self.tool_workspace.set_tool(tool)
        #################
        try:
            self._tool_options_model = tool_.ToolOptionsModel3(tool.get_user_options())

            tool_settings.setModel(self._tool_options_model)
        except Exception as e:
            message = "Unable to use {} as it's not fully implemented".format(tool.name)
            QtWidgets.QMessageBox.warning(self, "Tool settings error", message)
            self.log_manager.warning(message)
            raise

    def _start_tool(self):
        # logger = logging.getLogger(__name__)
        # logger.debug("Start button pressed")
        if len(self._tool_selector_view.selectedIndexes()) != 1:
            print("Invalid number of selected Indexes. Expected 1. Found {}".format(
                len(self._tool_selector_view.selectedIndexes())))
            return

        tool = self._tools_model.data(self._tool_selector_view.selectedIndexes()[0], QtCore.Qt.UserRole)
        if issubclass(tool, forseti.tools.abstool.AbsTool):
            options = self._tool_options_model.get()
            self._tool = tool

            # wrapped_strat = runner_strategies.UsingWorkWrapper()
            # runner = runner_strategies.RunRunner(wrapped_strat)
            manager_strat = runner_strategies.UsingExternalManager(manager=self.work_manager)
            # manager_strat = runner_strategies.UsingWorkManager()
            runner = runner_strategies.RunRunner(manager_strat)

            runner.run(self.parent, tool, options, self.on_success, self.on_failed, self.work_manager.logger)

        else:
            QtWidgets.QMessageBox.warning(self.parent, "No op", "No tool selected.")


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

        self.tools_tab = ToolTab(self, tools, self._work_manager, self.log_manager)
        self.tabWidget.addTab(self.tools_tab.tab, "Tools")

        # WORKFLOW tab
        self.tab_workflow = QtWidgets.QWidget()
        self.tab_workflow.setObjectName("tab_workflow")
        self.tab_workflow_layout = QtWidgets.QVBoxLayout(self.tab_workflow)
        self.tab_workflow_layout.setObjectName("tab_workflow_layout")

        # self._tool_selector_view.setFixedHeight(100)

        ###########################################################
        #

        ######################
        self._workflow_model = tool_.ToolsListModel(workflows)
        self._workflow_selector_view = QtWidgets.QListView(self)
        self._workflow_selector_view.setMinimumHeight(100)

        # TODO: Change the model to show workflows only
        self._workflow_selector_view.setModel(self._workflow_model)
        self.tab_workflow_layout.addWidget(self._workflow_selector_view)

        self._workflow_workspace = QtWidgets.QGroupBox()
        self._workflow_workspace.setTitle("Workflow")

        self._selected_workflow_name_line = QtWidgets.QLineEdit()
        self._selected_workflow_description_information = QtWidgets.QTextBrowser()

        self._workflow_workspace_layout = QtWidgets.QVBoxLayout()

        self._workflow_settings = QtWidgets.QTableView(parent=self)

        self._workflow_config_layout = QtWidgets.QFormLayout()
        self._workflow_config_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)

        self._workflow_config_layout.addRow(QtWidgets.QLabel("Selected"), self._selected_workflow_name_line)
        self._workflow_config_layout.addRow(QtWidgets.QLabel("Description"),
                                            self._selected_workflow_description_information)
        self._workflow_config_layout.addRow(QtWidgets.QLabel("Settings"), self._workflow_settings)

        self._workflow_actions_layout = QtWidgets.QHBoxLayout()
        self._workflow_start_button = QtWidgets.QPushButton()
        self._workflow_start_button.setText("Start")
        self._workflow_start_button.clicked.connect(self.start_workflow)

        self._workflow_actions_layout.addSpacerItem(QtWidgets.QSpacerItem(0, 40, QtWidgets.QSizePolicy.Expanding))
        self._workflow_actions_layout.addWidget(self._workflow_start_button)

        self._workflow_workspace.setLayout(self._workflow_workspace_layout)
        self._workflow_workspace_layout.addLayout(self._workflow_config_layout)
        # self._workflow_workspace_layout.addLayout(self._workflow_actions_layout)
        self.tab_workflow_layout.addWidget(self._workflow_workspace)
        self.tab_workflow_layout.addLayout(self._workflow_actions_layout)
        self.tabWidget.addTab(self.tab_workflow, "Workflows")

        ###########################################################
        self.main_splitter.addWidget(self.tabWidget)
        ###########################################################
        self.console = self.create_console()
        self._handler = ConsoleLogger(self.console)
        self._handler.setLevel(logging.INFO)
        self.log_manager.addHandler(self._handler)
        self.log_manager.info("READY!")
        ###########################################################

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
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Show Window
        self.show()

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
    # def on_success(self, results, callback):
    #     self.tools_tab.tab.on_success(results, callback)
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
    #     # # self._tool.on_completion(results=results,user_args=user_args)
    #     #
    #     # # QtWidgets.QMessageBox.about(self, "Finished", "Finished")
    #
    # def on_failed(self, exc):
    #     self.tools_tab.tab.on_failed(exc)
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
    # #     #     runner.run(self, tool, options, self.on_success, self.on_failed, self.work_manager.logger)
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


class MyDelegate(QtWidgets.QStyledItemDelegate):

    def createEditor(self, parent, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
        if index.isValid():
            tool_settings = index.data(QtCore.Qt.UserRole)
            browser_widget = tool_settings.edit_widget()
            if browser_widget:
                assert isinstance(browser_widget, options.CustomItemWidget)
                browser_widget.editingFinished.connect(self.update_custom_item)

                # browser_widget.editingFinished.connect(lambda : self.commitData(browser_widget))
                browser_widget.setParent(parent)

                return browser_widget
        return super().createEditor(parent, option, index)

    # noinspection PyUnresolvedReferences
    def update_custom_item(self):
        self.commitData.emit(self.sender())

    def setEditorData(self, editor: QtWidgets.QPushButton, index: QtCore.QModelIndex):

        if index.isValid():
            i = index.data(QtCore.Qt.UserRole)
            if isinstance(editor, options.CustomItemWidget):
                editor.data = i.data
            # i.browse()
        super().setEditorData(editor, index)

    def setModelData(self, widget: QtWidgets.QWidget, model: QtCore.QAbstractItemModel, index):
        if isinstance(widget, options.CustomItemWidget):
            model.setData(index, widget.data)
            return
        super().setModelData(widget, model, index)

    def destroyEditor(self, QWidget, QModelIndex):
        super().destroyEditor(QWidget, QModelIndex)


def main():
    app = QtWidgets.QApplication(sys.argv)
    tools = tool_.available_tools()
    workflows = forseti.workflow.available_workflows()
    with worker.ToolJobManager() as work_manager:
        windows = MainWindow(work_manager=work_manager, tools=tools, workflows=workflows)
        windows.setWindowTitle(f"{PROJECT_NAME}: Version {forseti.__version__}")
        rc = app.exec_()
    sys.exit(rc)


if __name__ == '__main__':
    main()
