import abc
import traceback
import typing
from abc import ABCMeta, abstractmethod

from PyQt5 import QtWidgets, QtCore

import forseti.tools
from forseti import tool as tool_, runner_strategies
from forseti.tools import options


class AbsTab(metaclass=abc.ABCMeta):
    def __init__(self, parent, work_manager, log_manager):
        self.log_manager = log_manager
        self.parent = parent
        self.work_manager = work_manager

        self.tab, self.tab_layout = self.create_tab()

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
        tab_tools_layout.setObjectName("tab_layout")
        return tab_tools, tab_tools_layout


class ItemSelectionTab(AbsTab, metaclass=ABCMeta):
    @abstractmethod
    def _update_tool_selected(self, current, previous):
        pass

    def _create_selector_view(self, parent, model):
        selector_view = QtWidgets.QListView(parent)
        selector_view.setMinimumHeight(100)
        selector_view.setModel(model)
        selector_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        selector_view.selectionModel().currentChanged.connect(self._update_tool_selected)
        return selector_view

    @staticmethod
    def _create_tool_mapper(parent, config_widgets, model):
        tool_mapper = QtWidgets.QDataWidgetMapper(parent)
        tool_mapper.setModel(model)
        tool_mapper.addMapping(config_widgets['name'], 0)
        # This needs custom mapping because without it, new line characters are removed
        tool_mapper.addMapping(config_widgets['description'], 1, b"plainText")
        return tool_mapper

    @abstractmethod
    def start(self):
        pass

    def create_actions(self):
        tool_actions_layout = QtWidgets.QHBoxLayout()

        start_button = QtWidgets.QPushButton()
        start_button.setText("Start")
        start_button.clicked.connect(self._start)

        tool_actions_layout.addSpacerItem(QtWidgets.QSpacerItem(0, 40, QtWidgets.QSizePolicy.Expanding))
        tool_actions_layout.addWidget(start_button)
        actions = {
            "start_button": start_button
        }
        return actions, tool_actions_layout

    def _start(self):
        if self.is_ready_to_start():
            self.start()

    @abstractmethod
    def is_ready_to_start(self) -> bool:
        pass


class ToolTab(ItemSelectionTab):
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

        self._tool_selector_view = self._create_selector_view(parent, model=self._tools_model)
        self._tool_mapper = self._create_tool_mapper(self.parent, self.config_widgets, model=self._tools_model)

        self.compose_tab_layout()

    def compose_tab_layout(self):
        self.tab_layout.addWidget(self._tool_selector_view)
        self.tab_layout.addWidget(self.tool_workspace)
        self.tab_layout.addLayout(self._tool_actions_layout)

    def is_ready_to_start(self) -> bool:
        if len(self._tool_selector_view.selectedIndexes()) != 1:
            print("Invalid number of selected Indexes. Expected 1. Found {}".format(
                len(self._tool_selector_view.selectedIndexes())))
            return False
        return True

    def start(self):
        # logger = logging.getLogger(__name__)
        # logger.debug("Start button pressed")

        tool = self._tools_model.data(self._tool_selector_view.selectedIndexes()[0], QtCore.Qt.UserRole)
        if issubclass(tool, forseti.tools.abstool.AbsTool):
            options = self._tool_options_model.get()
            self._tool = tool

            # wrapped_strat = runner_strategies.UsingWorkWrapper()
            # runner = runner_strategies.RunRunner(wrapped_strat)
            manager_strat = runner_strategies.UsingExternalManager(manager=self.work_manager)
            # manager_strat = runner_strategies.UsingWorkManager()
            runner = runner_strategies.RunRunner(manager_strat)

            runner.run(self.parent, tool, options, self._on_success, self._on_failed, self.work_manager.logger)

        else:
            QtWidgets.QMessageBox.warning(self.parent, "No op", "No tool selected.")

    def _on_failed(self, exc):
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

    def _on_success(self, results, callback):
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


class WorkflowsTab(ItemSelectionTab):

    def __init__(self, parent, workflows, work_manager, log_manager):
        super().__init__(parent, work_manager, log_manager)
        self._workflow_model = tool_.ToolsListModel(workflows)
        self.config_widgets, self.workflow_config_layout = self.create_config_layout(parent)
        self.workflow_workspace, self.workspace_layout = self.create_workspace("Workflow")
        self.workspace_layout.addLayout(self.workflow_config_layout)
        self._workflow_selector_view = self._create_selector_view(parent, model=self._workflow_model)
        self._workflow_actions, self._workflow_actions_layout = self.create_actions()
        self.compose_tab_layout()

    def is_ready_to_start(self):
        return False

    def start(self):
        print("starting")

        # if len(self._tool_selector_view.selectedIndexes()) != 1:
        #     print("Invalid number of selected Indexes. Expected 1. Found {}".format(
        #         len(self._tool_selector_view.selectedIndexes())))
        #     return
        #
        # tool = self._tools_model.data(self._tool_selector_view.selectedIndexes()[0], QtCore.Qt.UserRole)
        # if issubclass(tool, forseti.tools.abstool.AbsTool):
        #     options = self._tool_options_model.get()
        #     self._tool = tool
        #
        #     # wrapped_strat = runner_strategies.UsingWorkWrapper()
        #     # runner = runner_strategies.RunRunner(wrapped_strat)
        #     manager_strat = runner_strategies.UsingExternalManager(manager=self.work_manager)
        #     # manager_strat = runner_strategies.UsingWorkManager()
        #     runner = runner_strategies.RunRunner(manager_strat)
        #
        #     runner.run(self.parent, tool, options, self._on_success, self._on_failed, self.work_manager.logger)
        #
        # else:
        #     QtWidgets.QMessageBox.warning(self.parent, "No op", "No tool selected.")

    def compose_tab_layout(self):
        self.tab_layout.addWidget(self._workflow_selector_view)
        self.tab_layout.addWidget(self.workflow_workspace)
        self.tab_layout.addLayout(self._workflow_actions_layout)

    # TODO: _update_tool_selected
    def _update_tool_selected(self, current, previous):
        pass
        # tool_settings = self.config_widgets['settings']
        # try:
        #     self._tool_selected(current)
        #     tool_settings.resizeRowsToContents()
        #     self._tool_mapper.setCurrentModelIndex(current)
        # except Exception as e:
        #     self._tool_selected(previous)
        #     tool_settings.resizeRowsToContents()
        #     self._tool_mapper.setCurrentModelIndex(previous)
        #     self._tool_selector_view.setCurrentIndex(previous)


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