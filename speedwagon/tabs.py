import abc
import io
import os
import sys
import traceback
import enum
# import typing
from typing import List, Optional, Tuple, Dict, Iterator
from abc import ABCMeta, abstractmethod

import yaml
from PyQt5 import QtWidgets, QtCore  # type: ignore

import speedwagon.dialog.dialogs
from . import runner_strategies
from . import models
from .tools import options
from .job import AbsWorkflow, AbsTool, NullWorkflow

SELECTOR_VIEW_SIZE_POLICY = QtWidgets.QSizePolicy(
    QtWidgets.QSizePolicy.MinimumExpanding,
    QtWidgets.QSizePolicy.Maximum)

# There are correct
WORKFLOW_SIZE_POLICY = QtWidgets.QSizePolicy(
    QtWidgets.QSizePolicy.MinimumExpanding,
    QtWidgets.QSizePolicy.Maximum)

ITEM_SETTINGS_POLICY = QtWidgets.QSizePolicy(
    QtWidgets.QSizePolicy.MinimumExpanding,
    QtWidgets.QSizePolicy.Maximum)


class TabWidgets(enum.Enum):
    NAME = "name"
    DESCRIPTION = "description"
    SETTINGS = "settings"


class AbsTab(metaclass=ABCMeta):
    @abc.abstractmethod
    def compose_tab_layout(self):
        pass

    @abc.abstractmethod
    def create_actions(self):
        pass

    @staticmethod
    @abstractmethod
    def create_tools_settings_view(parent):
        pass

    @classmethod
    @abstractmethod
    def create_workspace_layout(cls, parent):
        pass

    @classmethod
    @abstractmethod
    def create_workspace(cls, title, parent):
        pass


class Tab(AbsTab):
    def compose_tab_layout(self):
        return super().compose_tab_layout()

    def create_actions(self):
        return super().create_actions()

    def __init__(self, parent, work_manager):
        self.parent = parent
        self.work_manager = work_manager
        self.tab, self.tab_layout = self.create_tab()
        self.tab.setSizePolicy(WORKFLOW_SIZE_POLICY)
        self.tab.setMinimumHeight(400)
        self.tab_layout.setSpacing(20)
        # self.tab.setFixedHeight(500)

    @staticmethod
    def create_tools_settings_view(parent):
        tool_settings = QtWidgets.QTableView(parent=parent)
        tool_settings.setEditTriggers(
            QtWidgets.QAbstractItemView.AllEditTriggers)
        tool_settings.setItemDelegate(MyDelegate(parent))
        tool_settings.horizontalHeader().setVisible(False)
        tool_settings.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        tool_settings.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch)
        v_header = tool_settings.verticalHeader()
        v_header.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        v_header.setSectionsClickable(False)
        v_header.setDefaultSectionSize(25)
        return tool_settings

    @classmethod
    def create_workspace_layout(
            cls,
            parent
    ) -> Tuple[Dict[TabWidgets, QtWidgets.QWidget],
                      QtWidgets.QLayout]:
        tool_config_layout = QtWidgets.QFormLayout()

        name_line = QtWidgets.QLineEdit()
        name_line.setReadOnly(True)

        description_information = QtWidgets.QTextBrowser()
        description_information.setMinimumHeight(75)

        settings = cls.create_tools_settings_view(parent)

        tool_config_layout.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.ExpandingFieldsGrow)
        tool_config_layout.addRow(QtWidgets.QLabel("Selected"), name_line)
        tool_config_layout.addRow(QtWidgets.QLabel("Description"),
                                  description_information)
        tool_config_layout.addRow(QtWidgets.QLabel("Settings"), settings)

        widgets = {
            TabWidgets.NAME: name_line,
            TabWidgets.DESCRIPTION: description_information,
            TabWidgets.SETTINGS: settings,

        }
        return widgets, tool_config_layout

    @classmethod
    def create_workspace(cls, title, parent) -> \
            Tuple[QtWidgets.QWidget, Dict[
                TabWidgets, QtWidgets.QWidget], QtWidgets.QLayout]:
        tool_workspace = QtWidgets.QGroupBox()

        tool_workspace.setTitle(title)
        tool_workspace.setMinimumHeight(100)
        workspace_widgets, layout = cls.create_workspace_layout(parent)
        tool_workspace.setLayout(layout)
        tool_workspace.setSizePolicy(WORKFLOW_SIZE_POLICY)
        return tool_workspace, workspace_widgets, layout

    @staticmethod
    def create_tab() -> Tuple[QtWidgets.QWidget, QtWidgets.QLayout]:
        tab_tools = QtWidgets.QWidget()
        tab_tools.setObjectName("tab")
        tab_tools_layout = QtWidgets.QVBoxLayout(tab_tools)
        tab_tools_layout.setObjectName("tab_layout")
        return tab_tools, tab_tools_layout


class ItemSelectionTab(Tab, metaclass=ABCMeta):
    def __init__(self, name, parent: QtWidgets.QWidget, item_model,
                 work_manager, log_manager) -> None:

        super().__init__(parent, work_manager)
        self.log_manager = log_manager
        self.item_selection_model = item_model
        self.options_model: Optional[models.ItemListModel] = None
        self.tab_name = name

        self.item_selector_view = self._create_selector_view(
            parent,
            model=self.item_selection_model
        )

        self.workspace, self.workspace_widgets, self.workspace_layout = \
            self.create_workspace(self.tab_name, parent)

        self.item_form = self.create_form(self.parent,
                                          self.workspace_widgets,
                                          model=self.item_selection_model)

        self.actions_widgets, self.actions_layout = self.create_actions()
        if self.item_selection_model.rowCount() == 0:
            self.item_selector_view.setVisible(False)
            self.workspace.setVisible(False)
            self.actions_widgets['start_button'].setEnabled(False)
            self._empty_tab_message = QtWidgets.QLabel()
            self._empty_tab_message.setText("No items available to display")
            self.tab_layout.addWidget(self._empty_tab_message)
        self.compose_tab_layout()
        self.init_selection()

    def init_selection(self):
        # Set the first item
        index = self.item_selection_model.index(0, 0)
        self.item_selector_view.setCurrentIndex(index)

    def _create_selector_view(self, parent, model: QtCore.QAbstractTableModel):
        selector_view = QtWidgets.QListView(parent)
        selector_view.setAlternatingRowColors(True)
        selector_view.setUniformItemSizes(True)
        selector_view.setModel(model)

        MIN_ROWS_VIS = 4
        # MAX_ROWS_VIS = 5

        if model.rowCount() < MIN_ROWS_VIS:
            min_rows = model.rowCount()
        else:
            min_rows = MIN_ROWS_VIS

        selector_view.setFixedHeight(
            (selector_view.sizeHintForRow(0) * min_rows) + 4
        )

        selector_view.setSizePolicy(SELECTOR_VIEW_SIZE_POLICY)

        selector_view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )

        selector_view.selectionModel().currentChanged.connect(
            self._update_tool_selected
        )

        return selector_view

    @staticmethod
    def create_form(parent, config_widgets, model):
        tool_mapper = QtWidgets.QDataWidgetMapper(parent)
        tool_mapper.setModel(model)
        tool_mapper.addMapping(config_widgets[TabWidgets.NAME], 0)

        tool_mapper.addMapping(config_widgets[TabWidgets.DESCRIPTION],
                               1,
                               b"plainText")

        return tool_mapper

    @abc.abstractmethod
    def start(self, item) -> None:
        pass

    @abc.abstractmethod
    def get_item_options_model(self, item):
        pass

    def create_actions(self) -> Tuple[Dict[str,
                                                         QtWidgets.QWidget],
                                             QtWidgets.QLayout]:

        tool_actions_layout = QtWidgets.QHBoxLayout()

        start_button = QtWidgets.QPushButton()
        start_button.setText("Start")
        start_button.clicked.connect(self._start)

        tool_actions_layout.addSpacerItem(
            QtWidgets.QSpacerItem(0, 40, QtWidgets.QSizePolicy.Expanding)
        )

        tool_actions_layout.addWidget(start_button)
        actions = {
            "start_button": start_button
        }
        return actions, tool_actions_layout

    def _start(self):
        selected_workflow = self.item_selection_model.data(
            self.item_selector_view.selectedIndexes()[0],
            QtCore.Qt.UserRole)

        if self.is_ready_to_start():
            self.start(selected_workflow)

    @abc.abstractmethod
    def is_ready_to_start(self) -> bool:
        pass

    def _update_tool_selected(self, current, previous):
        # selection_settings_widget = self.workspace_widgets['settings']
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
        item_settings = self.workspace_widgets[TabWidgets.SETTINGS]
        # item_settings = self.workspace_widgets['settings']
        # model.
        # self.workspace.set_tool(tool)
        #################
        try:
            model = self.get_item_options_model(item)
            self.options_model = model
            item_settings.setModel(self.options_model)

            item_settings.setFixedHeight(
                ((item_settings.sizeHintForRow(0) - 1) * model.rowCount()) + 2
            )

            item_settings.setSizePolicy(ITEM_SETTINGS_POLICY)
            # item_settings.resize()
        except Exception as e:
            tb = traceback.format_exception(etype=type(e),
                                            value=e,
                                            tb=e.__traceback__)

            message = "Unable to use {}. Reason: {}".format(
                item.name, str(e.__class__.__name__))

            warning_message_dialog = QtWidgets.QMessageBox(self.parent)
            spanner = QtWidgets.QSpacerItem(300,
                                            0,
                                            QtWidgets.QSizePolicy.Minimum,
                                            QtWidgets.QSizePolicy.Expanding)

            warning_message_dialog.setWindowTitle("Settings Error")
            warning_message_dialog.setIcon(QtWidgets.QMessageBox.Warning)
            warning_message_dialog.setText(message)
            warning_message_dialog.setDetailedText("".join(tb))
            layout = warning_message_dialog.layout()

            layout.addItem(
                spanner, layout.rowCount(), 0, 1, layout.columnCount())

            warning_message_dialog.exec()

            self.log_manager.warning(message)
            raise

    def compose_tab_layout(self):
        self.tab_layout.setAlignment(QtCore.Qt.AlignTop)
        self.tab_layout.addWidget(self.item_selector_view)
        self.tab_layout.addWidget(self.workspace)
        self.tab_layout.addLayout(self.actions_layout)


class ToolTab(ItemSelectionTab):
    def __init__(self, parent, tools, work_manager, log_manager) -> None:
        super().__init__("Tool",
                         parent,
                         models.ToolsListModel(tools),
                         work_manager,
                         log_manager)
        self._tool: Optional[AbsTool] = None

    def is_ready_to_start(self) -> bool:
        number_of_selected = self.item_selector_view.selectedIndexes()
        if len(number_of_selected) != 1:
            print(
                "Invalid number of selected Indexes. "
                "Expected 1. Found {}".format(number_of_selected)
            )
            return False
        return True

    def start(self, item) -> None:

        if issubclass(item, AbsTool):
            try:
                if self.options_model is None:
                    raise Exception("Tools not loaded")

                selected_options = self.options_model.get()
                item.validate_user_options(**selected_options)
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

            manager_strat = runner_strategies.UsingExternalManager(
                manager=self.work_manager,
                on_success=self._on_success,
                on_failure=self._on_failed
            )

            # manager_strat = runner_strategies.UsingWorkManager()
            runner = runner_strategies.RunRunner(manager_strat)

            runner.run(self.parent, item(),
                       selected_options, self.work_manager.logger)

        else:
            QtWidgets.QMessageBox.warning(self.parent,
                                          "No op", "No tool selected.")

    def _on_failed(self, exc):
        self.log_manager.error("Process failed. Reason: {}".format(exc))
        # print("************** {}".format(exc))
        if exc:
            traceback.print_tb(exc.__traceback__)
            # self.log_manager.notify(str(exc))
            self.log_manager.warning(str(exc))

            exception_message = traceback.format_exception(
                type(exc),
                exc,
                tb=exc.__traceback__
            )

            msg = speedwagon.dialog.dialogs.ErrorDialogBox(self.parent)
            msg.setWindowTitle(str(type(exc).__name__))
            msg.setText(str(exc))
            msg.setDetailedText("".join(exception_message))
            # msg.setStyleSheet("QLabel{min-width: 700px;}")
            msg.exec_()

    def _on_success(self, results, callback):
        self.log_manager.info("Done!")
        user_args = self.options_model.get()
        callback(results=results, user_args=user_args)
        report = self._tool.generate_report(results=results,
                                            user_args=user_args)
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
        model = models.ToolOptionsModel3(tool.get_user_options())
        return model


class WorkflowsTab(ItemSelectionTab):

    def __init__(self, parent: QtWidgets.QWidget, workflows, work_manager=None,
                 log_manager=None) -> None:

        super().__init__("Workflow", parent,
                         models.WorkflowListModel(workflows), work_manager,
                         log_manager)
        self._worflows = workflows

    def is_ready_to_start(self) -> bool:
        if len(self.item_selector_view.selectedIndexes()) != 1:
            print(
                "Invalid number of selected Indexes. "
                "Expected 1. Found {}".format(
                    len(self.item_selector_view.selectedIndexes()))
            )

            return False
        return True

    def run(self, workflow: AbsWorkflow, options) -> None:
        try:
            workflow.validate_user_options(**options)

            manager_strat = runner_strategies.UsingExternalManagerForAdapter(
                manager=self.work_manager)
            runner = runner_strategies.RunRunner(manager_strat)

            print("starting")

            runner.run(self.parent,
                       workflow,
                       options,
                       self.work_manager.logger)

        except ValueError as exc:
            msg = QtWidgets.QMessageBox(self.parent)
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle(exc.__class__.__name__)
            msg.setText(str(exc))
            msg.exec()

        except Exception as exc:
            traceback.print_tb(exc.__traceback__)
            print(exc, file=sys.stderr)
            msg = QtWidgets.QMessageBox(self.parent)
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle(exc.__class__.__name__)
            msg.setText(str(exc))
            msg.setDetailedText(
                "".join(traceback.format_exception(type(exc),
                                                   exc,
                                                   tb=exc.__traceback__))
            )
            # msg.setDetailedText("".join(exception_message))
            msg.exec_()
            return

    def start(self, item):

        new_workflow = item()

        # Add global settings to workflow
        assert isinstance(new_workflow, AbsWorkflow)

        new_workflow.global_settings.update(
            dict(self.work_manager.user_settings))

        user_options = (self.options_model.get())

        self.run(new_workflow, user_options)

    def _on_success(self, results, callback):
        print("success")

    def _on_failed(self, exc):
        print("failed")

    def get_item_options_model(self, workflow):
        new_workflow = workflow()

        new_workflow.global_settings.update(
            dict(self.work_manager.user_settings))

        model = models.ToolOptionsModel3(new_workflow.user_options())
        return model
        # return tool_.ToolsListModel(tool)


class MyDelegate(QtWidgets.QStyledItemDelegate):

    def createEditor(
            self,
            parent,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
    ):
        if index.isValid():
            tool_settings = index.data(QtCore.Qt.UserRole)
            browser_widget = tool_settings.edit_widget()
            if browser_widget:
                assert isinstance(browser_widget, options.CustomItemWidget)
                browser_widget.editingFinished.connect(self.update_custom_item)
                browser_widget.setParent(parent)

                return browser_widget
        return super().createEditor(parent, option, index)

    # noinspection PyUnresolvedReferences
    def update_custom_item(self):
        self.commitData.emit(self.sender())

    def setEditorData(
            self,
            editor: QtWidgets.QPushButton,
            index: QtCore.QModelIndex
    ):

        if index.isValid():
            i = index.data(QtCore.Qt.UserRole)
            if isinstance(editor, options.CustomItemWidget):
                editor.data = i.data
            # i.browse()
        super().setEditorData(editor, index)

    def setModelData(self, widget: QtWidgets.QWidget,
                     model: QtCore.QAbstractItemModel, index):

        if isinstance(widget, options.CustomItemWidget):
            model.setData(index, widget.data)
            return
        super().setModelData(widget, model, index)

    def destroyEditor(self, QWidget, QModelIndex):
        super().destroyEditor(QWidget, QModelIndex)


class TabData:
    def __init__(self) -> None:
        self.tab_name = ""
        self.workflows = models.WorkflowListModel2()


def read_tabs_yaml(yaml_file) -> Iterator[TabData]:
    tabs_file_size = os.path.getsize(yaml_file)
    if tabs_file_size > 0:
        try:
            with open(yaml_file) as f:
                tabs_config_data = yaml.load(f.read(), Loader=yaml.SafeLoader)
            if not isinstance(tabs_config_data, dict):
                raise Exception(f"Failed to parse file")

            for tab_name in tabs_config_data:
                new_tab = TabData()
                new_tab.tab_name = tab_name
                for workflow_name in tabs_config_data.get(tab_name, []):
                    empty_workflow = NullWorkflow()
                    empty_workflow.name = workflow_name
                    new_tab.workflows.add_workflow(empty_workflow)
                yield new_tab

        except FileNotFoundError as e:
            print("Custom tabs file not found. "
                  "Reason: {}".format(e), file=sys.stderr)
            raise
        except AttributeError as e:
            print("Custom tabs file failed to load. "
                  "Reason: {}".format(e), file=sys.stderr)
            raise

        except yaml.YAMLError as e:
            print("{} file failed to load. "
                  "Reason: {}".format(yaml_file, e), file=sys.stderr)
            raise


def write_tabs_yaml(yaml_file, tabs: List[TabData]):
    tabs_data = dict()
    for tab in tabs:
        print(tab.tab_name)
        tabs = list()
        for workflow in tab.workflows.workflows:
            tabs.append(workflow.name)
        tabs_data[tab.tab_name] = tabs
    with open(yaml_file, "w") as f:
        yaml.dump(tabs_data, f, default_flow_style=False)

