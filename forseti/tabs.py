import abc
import traceback
import typing
from abc import ABCMeta, abstractmethod

from PyQt5 import QtWidgets, QtCore

import forseti.models
import forseti.tools
from forseti import tool as tool_, runner_strategies
from forseti.tools import options
from forseti.workflow import AbsWorkflow


class AbsTab(metaclass=abc.ABCMeta):
    def __init__(self, parent, work_manager):
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
    def create_config_layout(cls, parent) -> typing.Tuple[typing.Dict[str, QtWidgets.QWidget], QtWidgets.QLayout]:
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
    def create_workspace(title) -> QtWidgets.QWidget:
        tool_workspace = QtWidgets.QGroupBox()
        workspace2_layout = QtWidgets.QVBoxLayout()

        tool_workspace.setTitle(title)
        tool_workspace.setLayout(workspace2_layout)
        return tool_workspace

    @staticmethod
    def create_tab() -> typing.Tuple[QtWidgets.QWidget, QtWidgets.QLayout]:
        tab_tools = QtWidgets.QWidget()
        tab_tools.setObjectName("tab")
        tab_tools_layout = QtWidgets.QVBoxLayout(tab_tools)
        tab_tools_layout.setObjectName("tab_layout")
        return tab_tools, tab_tools_layout


class ItemSelectionTab(AbsTab, metaclass=ABCMeta):
    def __init__(self, name, parent: QtWidgets.QWidget, item_model, work_manager, log_manager) -> None:
        super().__init__(parent, work_manager)
        self.log_manager = log_manager
        self.item_selection_model = item_model
        self.options_model = None
        self.tab_name = name
        self.item_selector_view = self._create_selector_view(parent, model=self.item_selection_model)
        self.workspace = self.create_workspace(self.tab_name)
        self.config_widgets, self.config_layout = self.create_config_layout(parent)
        self.workspace.layout().addLayout(self.config_layout)
        self.item_form = self.create_form(self.parent, self.config_widgets, model=self.item_selection_model)
        self.actions_widgets, self.actions_layout = self.create_actions()
        self.compose_tab_layout()

    def _create_selector_view(self, parent, model: QtCore.QAbstractTableModel):
        selector_view = QtWidgets.QListView(parent)
        selector_view.setMinimumHeight(100)
        selector_view.setModel(model)
        selector_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        selector_view.selectionModel().currentChanged.connect(self._update_tool_selected)

        return selector_view

    @staticmethod
    def create_form(parent, config_widgets, model):
        tool_mapper = QtWidgets.QDataWidgetMapper(parent)
        tool_mapper.setModel(model)
        tool_mapper.addMapping(config_widgets['name'], 0)
        # This needs custom mapping because without it, new line characters are removed
        tool_mapper.addMapping(config_widgets['description'], 1, b"plainText")
        return tool_mapper

    @abc.abstractmethod
    def start(self):
        pass

    @abc.abstractmethod
    def get_item_options_model(self, item):
        pass

    def create_actions(self) -> typing.Tuple[typing.Dict[str, QtWidgets.QWidget], QtWidgets.QLayout]:
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

    @abc.abstractmethod
    def is_ready_to_start(self) -> bool:
        pass

    def _update_tool_selected(self, current, previous):
        selection_settings_widget = self.config_widgets['settings']
        try:
            if current.isValid():
                self.item_selected(current)
                self.item_form.setCurrentModelIndex(current)
        except Exception as e:
            if previous.isValid():
                self.item_selected(previous)
                self.item_form.setCurrentModelIndex(previous)
                self.item_selector_view.setCurrentIndex(previous)
            else:
                traceback.print_tb(e.__traceback__)
                # traceback.print_exception(e)
                self.item_selector_view.setCurrentIndex(previous)

    def item_selected(self, index: QtCore.QModelIndex):

        item = self.item_selection_model.data(index, QtCore.Qt.UserRole)
        item_settings = self.config_widgets['settings']
        # model.
        # self.workspace.set_tool(tool)
        #################
        try:
            model = self.get_item_options_model(item)
            self.options_model = model
            item_settings.setModel(self.options_model)
        except Exception as e:
            tb = traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            message = "Unable to use {}. Reason: {}".format(item.name, e)
            warning_message_dialog = QtWidgets.QMessageBox(self.parent)
            spanner = QtWidgets.QSpacerItem(300, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
            warning_message_dialog.setWindowTitle("Settings Error")
            warning_message_dialog.setIcon(QtWidgets.QMessageBox.Warning)
            warning_message_dialog.setText(message)
            warning_message_dialog.setDetailedText("".join(tb))
            layout = warning_message_dialog.layout()
            layout.addItem(spanner, layout.rowCount(), 0, 1, layout.columnCount())
            warning_message_dialog.exec()

            self.log_manager.warning(message)
            raise

    def compose_tab_layout(self):
        self.tab_layout.addWidget(self.item_selector_view)
        self.tab_layout.addWidget(self.workspace)
        self.tab_layout.addLayout(self.actions_layout)


class ToolTab(ItemSelectionTab):
    def __init__(self, parent, tools, work_manager, log_manager):
        super().__init__("Tool", parent, forseti.models.ToolsListModel(tools), work_manager, log_manager)

        # self.actions_widgets, self.actions_layout = self.create_actions()
        # self.item_form = self.create_form(self.parent, self.config_widgets, model=self._tool_selection_model)

    def is_ready_to_start(self) -> bool:
        if len(self.item_selector_view.selectedIndexes()) != 1:
            print("Invalid number of selected Indexes. Expected 1. Found {}".format(
                len(self.item_selector_view.selectedIndexes())))
            return False
        return True

    def start(self):
        # logger = logging.getLogger(__name__)
        # logger.debug("Start button pressed")

        item = self.item_selection_model.data(self.item_selector_view.selectedIndexes()[0], QtCore.Qt.UserRole)
        if issubclass(item, forseti.tools.abstool.AbsTool):
            try:
                options = self.options_model.get()
                item.validate_user_options(**options)
            except Exception as e:
                msg = QtWidgets.QMessageBox(self.parent)
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setWindowTitle("Invalid Configuration")
                msg.setText(str(e))
                # msg.setDetailedText("".join(exception_message))
                msg.exec_()
                return
            self._tool = item

            # wrapped_strat = runner_strategies.UsingWorkWrapper()
            # runner = runner_strategies.RunRunner(wrapped_strat)

            manager_strat = runner_strategies.UsingExternalManager(manager=self.work_manager, on_success=self._on_success, on_failure=self._on_failed)
            # manager_strat = runner_strategies.UsingWorkManager()
            runner = runner_strategies.RunRunner(manager_strat)

            runner.run(self.parent, item(), options, self.work_manager.logger)

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
        user_args = self.options_model.get()
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

        # self._tool.setup_task(results=results,user_args=user_args)

        # QtWidgets.QMessageBox.about(self, "Finished", "Finished")

    def get_item_options_model(self, tool):
        model = forseti.models.ToolOptionsModel3(tool.get_user_options())
        return model


class WorkflowsTab(ItemSelectionTab):

    def __init__(self, parent: QtWidgets.QWidget, workflows, work_manager, log_manager) -> None:
        super().__init__("Workflow", parent, forseti.models.WorkflowListModel(workflows), work_manager, log_manager)

    def is_ready_to_start(self) -> bool:
        if len(self.item_selector_view.selectedIndexes()) != 1:
            print("Invalid number of selected Indexes. Expected 1. Found {}".format(
                len(self.item_selector_view.selectedIndexes())))
            return False
        return True

    def start(self):
        selected_workflow = self.item_selection_model.data(self.item_selector_view.selectedIndexes()[0], QtCore.Qt.UserRole)
        new_workflow = selected_workflow()
        assert isinstance(new_workflow, AbsWorkflow)
        user_options = (self.options_model.get())
        try:
            new_workflow.validate_user_options(**user_options)

            manager_strat = runner_strategies.UsingExternalManagerForAdapter(manager=self.work_manager)
            runner = runner_strategies.RunRunner(manager_strat)


                # task = new_workflow.create_new_task(**new_task_metadata)
                # print(task)
                # for subtask in task.subtasks:
                #     adapted_tool = forseti.tasks.SubtaskJobAdapter(subtask)
                #     print("** {}".format(subtask))
                #     print(adapted_tool)
            print("starting")
            runner.run(self.parent, new_workflow, user_options, self.work_manager.logger)
        except Exception as exc:
            msg = QtWidgets.QMessageBox(self.parent)
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle(exc.__class__.__name__)
            msg.setText(str(exc))
            msg.setDetailedText("".join(traceback.format_exception(type(exc), exc, tb=exc.__traceback__)))
            # msg.setDetailedText("".join(exception_message))
            msg.exec_()
            return
            #     runner


    def _on_success(self, results, callback):
        print("success")

    def _on_failed(self, exc):
        print("failed")

        # adapted_tool = forseti.tasks.SubtaskJobAdapter(subtask)
        # manager.add_job(adapted_tool, adapted_tool.settings)
        #
        # runner.run(self.parent, item, options, self._on_success, self._on_failed, self.wo

        # if len(self.item_selector_view.selectedIndexes()) != 1:
        #     print("Invalid number of selected Indexes. Expected 1. Found {}".format(
        #         len(self.item_selector_view.selectedIndexes())))
        #     return
        #
        # tool = self._tool_selection_model.data(self.item_selector_view.selectedIndexes()[0], QtCore.Qt.UserRole)
        # if issubclass(tool, forseti.tools.abstool.AbsTool):
        #     options = self.options_model.get()
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

    def get_item_options_model(self, workflow):
        model = forseti.models.ToolOptionsModel3(workflow().user_options())
        return model
        # return tool_.ToolsListModel(tool)


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
