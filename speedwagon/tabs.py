"""Creating and managing tabs in the UI display"""
import abc
import os
import sys
import traceback
import enum
from typing import List, Optional, Tuple, Dict, Iterator, NamedTuple, cast
from abc import ABCMeta

import yaml
from PyQt5 import QtWidgets, QtCore  # type: ignore

from . import runner_strategies
from . import models
from .exceptions import MissingConfiguration
from .workflows import shared_custom_widgets as options
from .job import AbsWorkflow, NullWorkflow


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


class Tab:
    @abc.abstractmethod
    def compose_tab_layout(self) -> None:
        """Draw the layout of the tab"""

    @abc.abstractmethod
    def create_actions(self):
        """Generate action widgets"""

    def __init__(self, parent, work_manager) -> None:
        self.parent = parent
        self.work_manager = work_manager
        self.tab, self.tab_layout = self.create_tab()
        self.tab.setSizePolicy(WORKFLOW_SIZE_POLICY)
        self.tab.setMinimumHeight(400)
        self.tab_layout.setSpacing(20)

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
    def create_workspace_layout(cls, parent) \
            -> Tuple[Dict[TabWidgets, QtWidgets.QWidget], QtWidgets.QLayout]:

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

    def init_selection(self) -> None:
        # Set the first item
        index = self.item_selection_model.index(0, 0)
        self.item_selector_view.setCurrentIndex(index)

    def _create_selector_view(self, parent, model: QtCore.QAbstractTableModel):
        selector_view = QtWidgets.QListView(parent)
        selector_view.setAlternatingRowColors(True)
        selector_view.setUniformItemSizes(True)
        selector_view.setModel(model)

        MIN_ROWS_VIS = 4

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

        # PlainText mapping because without the descriptions render without
        # newline
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

    def create_actions(self) -> Tuple[Dict[str, QtWidgets.QWidget],
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
            "start_button": cast(QtWidgets.QWidget, start_button)
        }
        return actions, tool_actions_layout

    def _start(self) -> None:
        selected_workflow = self.item_selection_model.data(
            self.item_selector_view.selectedIndexes()[0],
            QtCore.Qt.UserRole)

        if self.is_ready_to_start():
            try:
                self.start(selected_workflow)
            except MissingConfiguration as error_message:
                config_error_dialog = QtWidgets.QMessageBox(self.parent)
                config_error_dialog.setWindowTitle("Settings Error")
                config_error_dialog.setDetailedText(f"{error_message}")
                config_error_dialog.setText(
                    "Speedwagon has a problem with current configuration "
                    "settings"
                )
                config_error_dialog.exec_()

    @abc.abstractmethod
    def is_ready_to_start(self) -> bool:
        pass

    def _update_tool_selected(self, current, previous) -> None:
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
                self.item_selector_view.setCurrentIndex(previous)

    def item_selected(self, index: QtCore.QModelIndex) -> None:

        item = self.item_selection_model.data(index, QtCore.Qt.UserRole)
        item_settings = self.workspace_widgets[TabWidgets.SETTINGS]
        #################
        try:
            model = self.get_item_options_model(item)
            self.options_model = model
            item_settings.setModel(self.options_model)

            item_settings.setFixedHeight(
                ((item_settings.sizeHintForRow(0) - 1) * model.rowCount()) + 2
            )

            item_settings.setSizePolicy(ITEM_SETTINGS_POLICY)
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

    def compose_tab_layout(self) -> None:
        self.tab_layout.setAlignment(QtCore.Qt.AlignTop)
        self.tab_layout.addWidget(self.item_selector_view)
        self.tab_layout.addWidget(self.workspace)
        self.tab_layout.addLayout(self.actions_layout)


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

            runner.run(self.parent, workflow, options,
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
            msg.exec_()
            return

    def start(self, item):

        new_workflow = item(dict(self.work_manager.user_settings))

        # Add global settings to workflow
        assert isinstance(new_workflow, AbsWorkflow)

        # new_workflow.global_settings.update(
        #     dict(self.work_manager.user_settings))

        user_options = (self.options_model.get())

        self.run(new_workflow, user_options)

    def get_item_options_model(self, workflow):
        new_workflow = workflow(
            global_settings=dict(self.work_manager.user_settings)
        )
        model = models.ToolOptionsModel3(new_workflow.user_options())
        return model


class MyDelegate(QtWidgets.QStyledItemDelegate):

    def createEditor(self, parent, option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex):

        if index.isValid():
            tool_settings = index.data(QtCore.Qt.UserRole)
            browser_widget = tool_settings.edit_widget()
            if browser_widget:
                assert isinstance(browser_widget, options.CustomItemWidget)
                browser_widget.editingFinished.connect(self.update_custom_item)
                browser_widget.setParent(parent)

                return browser_widget
        editor = super().createEditor(parent, option, index)
        editor.setAutoFillBackground(True)
        return editor

    # noinspection PyUnresolvedReferences
    def update_custom_item(self):
        self.commitData.emit(self.sender())

    def setEditorData(
            self,
            editor: QtWidgets.QWidget,
            index: QtCore.QModelIndex
    ):
        if index.isValid():
            i = index.data(QtCore.Qt.UserRole)
            if isinstance(editor, options.CustomItemWidget):
                editor.data = i.data
        super().setEditorData(editor, index)

    def setModelData(self, widget: QtWidgets.QWidget,
                     model: QtCore.QAbstractItemModel, index):

        if isinstance(widget, options.CustomItemWidget):
            model.setData(index, widget.data)
            return
        super().setModelData(widget, model, index)

    def destroyEditor(self, QWidget, QModelIndex):
        super().destroyEditor(QWidget, QModelIndex)


class TabData(NamedTuple):
    tab_name: str
    workflows_model: "models.WorkflowListModel2"


def read_tabs_yaml(yaml_file: str) -> Iterator[TabData]:
    tabs_file_size = os.path.getsize(yaml_file)
    if tabs_file_size > 0:
        try:
            with open(yaml_file) as f:
                tabs_config_data = yaml.load(f.read(), Loader=yaml.SafeLoader)
            if not isinstance(tabs_config_data, dict):
                raise Exception("Failed to parse file")

            for tab_name in tabs_config_data:
                model = models.WorkflowListModel2()
                for workflow_name in tabs_config_data.get(tab_name, []):
                    empty_workflow = NullWorkflow()
                    empty_workflow.name = workflow_name
                    model.add_workflow(empty_workflow)
                new_tab = TabData(tab_name, model)
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


def write_tabs_yaml(yaml_file: str, tabs: List[TabData]) -> None:
    tabs_data = dict()
    for tab in tabs:
        tab_model = tab.workflows_model

        tabs_data[tab.tab_name] = \
            [workflow.name for workflow in tab_model.workflows]

    with open(yaml_file, "w") as f:
        yaml.dump(tabs_data, f, default_flow_style=False)


def extract_tab_information(model: "speedwagon.models.TabsModel"):
    tabs = []
    for tab in model.tabs:
        new_tab = TabData(tab.tab_name, tab.workflows_model)
        tabs.append(new_tab)
    return tabs
