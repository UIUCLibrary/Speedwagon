"""Creating and managing tabs in the UI display."""
from __future__ import annotations

import abc
import logging
import os
import sys
import traceback
import enum
import typing
from typing import List, Optional, Tuple, Dict, Iterator, NamedTuple, cast, \
    Type, Any
from abc import ABCMeta

import yaml
from PySide6 import QtWidgets, QtCore, QtGui  # type: ignore

import speedwagon
from speedwagon.frontend.qtwidgets.widgets import QtWidgetDelegateSelection

from speedwagon import runner_strategies
from speedwagon.frontend import qtwidgets

from speedwagon.exceptions import MissingConfiguration
from speedwagon.job import AbsWorkflow, NullWorkflow, Workflow

if typing.TYPE_CHECKING:
    from speedwagon.frontend.qtwidgets.worker import ToolJobManager
    from speedwagon.frontend.qtwidgets import models


__all__ = [
    "ItemSelectionTab",
    "WorkflowsTab",
    "TabData",
    "read_tabs_yaml",
    "write_tabs_yaml",
    "extract_tab_information"
]

SELECTOR_VIEW_SIZE_POLICY = QtWidgets.QSizePolicy(
    QtWidgets.QSizePolicy.Policy.MinimumExpanding,
    QtWidgets.QSizePolicy.Policy.Maximum)

# There are correct
WORKFLOW_SIZE_POLICY = QtWidgets.QSizePolicy(
    QtWidgets.QSizePolicy.Policy.MinimumExpanding,
    QtWidgets.QSizePolicy.Policy.Maximum)

ITEM_SETTINGS_POLICY = QtWidgets.QSizePolicy(
    QtWidgets.QSizePolicy.Policy.MinimumExpanding,
    QtWidgets.QSizePolicy.Policy.Maximum)


class TabsFileError(speedwagon.exceptions.SpeedwagonException):
    """Error with Tabs File."""


class TabWidgets(enum.Enum):
    NAME = "name"
    DESCRIPTION = "description"
    SETTINGS = "settings"


class Tab:
    @abc.abstractmethod
    def compose_tab_layout(self) -> None:
        """Draw the layout of the tab."""

    @abc.abstractmethod
    def create_actions(self) -> Tuple[Dict[str, QtWidgets.QWidget],
                                      QtWidgets.QLayout]:
        """Generate action widgets."""

    def __init__(self,
                 parent: QtWidgets.QWidget,
                 work_manager: ToolJobManager
                 ) -> None:
        """Create a new tab."""
        self.parent = parent
        self.work_manager = work_manager
        self.tab_widget, self.tab_layout = self.create_tab()
        self.tab_widget.setSizePolicy(WORKFLOW_SIZE_POLICY)
        self.tab_layout.setSpacing(20)

    @staticmethod
    def create_tools_settings_view(
            parent: QtWidgets.QWidget
    ) -> QtWidgets.QTableView:

        tool_settings = QtWidgets.QTableView(parent=parent)
        tool_settings.setEditTriggers(
            typing.cast(
                QtWidgets.QAbstractItemView.EditTrigger,
                QtWidgets.QAbstractItemView.EditTrigger.AllEditTriggers
            )
        )

        tool_settings.setItemDelegate(QtWidgetDelegateSelection(parent))

        tool_settings.horizontalHeader().setVisible(False)
        tool_settings.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        tool_settings.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        v_header = tool_settings.verticalHeader()
        v_header.setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        v_header.setSectionsClickable(False)
        return tool_settings

    @classmethod
    def create_workspace_layout(cls, parent: QtWidgets.QWidget) \
            -> Tuple[
                Dict[TabWidgets, QtWidgets.QWidget],
                QtWidgets.QFormLayout
            ]:

        tool_config_layout = QtWidgets.QFormLayout()

        name_line = QtWidgets.QLineEdit()
        name_line.setReadOnly(True)

        description_information = QtWidgets.QTextBrowser()
        description_information.setMinimumHeight(75)

        settings = cls.create_tools_settings_view(parent)

        tool_config_layout.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        tool_config_layout.addRow(QtWidgets.QLabel("Selected"), name_line)
        tool_config_layout.addRow(QtWidgets.QLabel("Description"),
                                  description_information)
        tool_config_layout.addRow(QtWidgets.QLabel("Settings"), settings)

        new_widgets: Dict[TabWidgets, QtWidgets.QWidget] = {
            TabWidgets.NAME: name_line,
            TabWidgets.DESCRIPTION: description_information,
            TabWidgets.SETTINGS: settings,

        }
        return new_widgets, tool_config_layout

    @classmethod
    def create_workspace(cls, title: str, parent: QtWidgets.QWidget) -> \
            Tuple[QtWidgets.QGroupBox, Dict[
                TabWidgets, QtWidgets.QWidget], QtWidgets.QFormLayout]:
        tool_workspace = QtWidgets.QGroupBox()

        tool_workspace.setTitle(title)
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
    """Tab for selection of item."""

    def __init__(
            self,
            name: str,
            parent: QtWidgets.QWidget,
            item_model: models.WorkflowListModel,
            work_manager: ToolJobManager,
            log_manager: logging.Logger
    ) -> None:
        """Create a new item selection tab."""
        super().__init__(parent, work_manager)
        self.export_action = QtGui.QAction(text="summy")
        self.log_manager = log_manager
        self.item_selection_model = item_model
        self.options_model: Optional[models.ToolOptionsModel4] = None
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
        """Initialize selection.

        Set the first item.
        """
        index = self.item_selection_model.index(0, 0)
        self.item_selector_view.setCurrentIndex(index)

    def _create_selector_view(
            self,
            parent: QtWidgets.QWidget,
            model: QtCore.QAbstractTableModel
    ) -> QtWidgets.QListView:

        selector_view = QtWidgets.QListView(parent)
        selector_view.setAlternatingRowColors(True)
        selector_view.setUniformItemSizes(True)
        selector_view.setModel(model)

        min_rows_vis = 4

        if model.rowCount() < min_rows_vis:
            min_rows = model.rowCount()
        else:
            min_rows = min_rows_vis

        selector_view.setFixedHeight(
            (selector_view.sizeHintForRow(0) * min_rows) + 4
        )

        selector_view.setSizePolicy(SELECTOR_VIEW_SIZE_POLICY)

        selector_view.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )

        cast(
            QtCore.SignalInstance,
            selector_view.selectionModel().currentChanged
        ).connect(self._update_tool_selected)

        return selector_view

    @staticmethod
    def create_form(
            parent: QtWidgets.QWidget,
            config_widgets: Dict[TabWidgets, QtWidgets.QWidget],
            model: models.WorkflowListModel
    ) -> QtWidgets.QDataWidgetMapper:
        """Generate form for the selected item."""
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
    def start(self, item: typing.Type[Workflow]) -> None:
        """Start item."""

    @abc.abstractmethod
    def get_item_options_model(
            self,
            workflow: Type[Workflow]
    ) -> models.ToolOptionsModel4:
        """Get item options model."""

    def create_actions(self) -> Tuple[Dict[str, QtWidgets.QWidget],
                                      QtWidgets.QLayout]:
        """Create actions."""
        tool_actions_layout = QtWidgets.QHBoxLayout()

        start_button = QtWidgets.QPushButton()

        start_button.setText("Start")
        start_button.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        # pylint: disable=no-member
        start_button.clicked.connect(self._start)  # type: ignore

        tool_actions_layout.addSpacerItem(
            QtWidgets.QSpacerItem(
                0,
                40,
                QtWidgets.QSizePolicy.Policy.Expanding
            )
        )

        tool_actions_layout.addWidget(start_button)
        actions = {
            "start_button": cast(QtWidgets.QWidget, start_button)
        }
        return actions, tool_actions_layout

    def _start(self) -> None:
        selected_workflow = cast(
            typing.Type[Workflow],
            self.item_selection_model.data(
                self.item_selector_view.selectedIndexes()[0],
                role=typing.cast(int, QtCore.Qt.ItemDataRole.UserRole)
            )
        )
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
        """Check if the workflow is ready to start."""

    def _update_tool_selected(
            self,
            current: QtCore.QModelIndex,
            previous: QtCore.QModelIndex
    ) -> None:
        try:
            if current.isValid():
                self.item_selected(current)
                self.item_form.setCurrentModelIndex(current)
        except Exception as error:
            if previous.isValid():
                self.item_selected(previous)
                self.item_form.setCurrentModelIndex(previous)
            else:
                traceback.print_tb(error.__traceback__)
            self.item_selector_view.setCurrentIndex(previous)

    def item_selected(self, index: QtCore.QModelIndex) -> None:
        """Set the current selection based on the index."""
        item = cast(
            typing.Type[Workflow],
            self.item_selection_model.data(
                index, role=typing.cast(int, QtCore.Qt.ItemDataRole.UserRole)
            )
        )

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
        except Exception as error:
            traceback.print_exc()
            stack_trace = traceback.format_exception(type(error),
                                                     value=error,
                                                     tb=error.__traceback__)
            item_name = cast(AbsWorkflow, item).name
            class_name = str(error.__class__.__name__)
            message = f"Unable to use {item_name}. Reason: {class_name}"

            warning_message_dialog = QtWidgets.QMessageBox(self.parent)
            spanner = QtWidgets.QSpacerItem(
                300,
                0,
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Expanding
            )

            warning_message_dialog.setWindowTitle("Settings Error")
            warning_message_dialog.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            warning_message_dialog.setText(message)
            warning_message_dialog.setDetailedText("".join(stack_trace))
            layout: QtWidgets.QGridLayout = warning_message_dialog.layout()

            layout.addItem(
                spanner, layout.rowCount(), 0, 1, layout.columnCount())

            warning_message_dialog.exec()

            self.log_manager.warning(message)
            raise

    def compose_tab_layout(self) -> None:
        """Build the tab widgets."""
        self.tab_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.tab_layout.addWidget(self.item_selector_view)
        self.tab_layout.addWidget(self.workspace)
        actions = QtWidgets.QWidget()
        actions.setLayout(self.actions_layout)
        self.tab_layout.addWidget(actions)


class WorkflowSignals(QtCore.QObject):
    start_workflow = QtCore.Signal(str, dict)


class WorkflowsTab(ItemSelectionTab):
    """Workflow tab."""

    def __init__(
            self,
            parent: QtWidgets.QWidget,
            workflows: typing.Mapping[str, Type[speedwagon.job.Workflow]],
            work_manager=None,
            log_manager=None) -> None:
        """Create a new workflow tab."""
        super().__init__("Workflow", parent,
                         qtwidgets.models.WorkflowListModel(workflows),
                         work_manager,
                         log_manager)
        self.workflows = workflows

    def is_ready_to_start(self) -> bool:
        """Get if the workflow is ready to start.

        Returns:
            Returns True is ready, false if not ready.
        """
        number_of_selected_indexes = \
            len(self.item_selector_view.selectedIndexes())

        if number_of_selected_indexes != 1:
            print(
                "Invalid number of selected Indexes. "
                f"Expected 1. Found {number_of_selected_indexes}"
            )

            return False
        return True

    def run(self, workflow: AbsWorkflow, options: Dict[str, Any]) -> None:
        """Run a workflow with a given set of options."""
        try:
            workflow.validate_user_options(**options)

            manager_strat = speedwagon.frontend.qtwidgets.runners.QtRunner(
                parent=self.parent)
            runner = runner_strategies.RunRunner(manager_strat)
            runner.run(workflow, options, self.work_manager.logger)

        except ValueError as exc:
            msg = self._create_error_message_box_from_exception(exc)
            msg.exec_()

        except speedwagon.exceptions.JobCancelled as job_cancel_exception:
            msg = self._create_error_message_box_from_exception(
                job_cancel_exception,
                window_title="Job Cancelled"
            )
            if job_cancel_exception.expected is True:
                msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
            else:
                msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
                traceback.print_tb(job_cancel_exception.__traceback__)
                print(job_cancel_exception, file=sys.stderr)
            msg.exec_()
            return

        except Exception as exc:
            traceback.print_tb(exc.__traceback__)
            print(exc, file=sys.stderr)
            msg = self._create_error_message_box_from_exception(exc)
            msg.setDetailedText(
                "".join(traceback.format_exception(type(exc),
                                                   exc,
                                                   tb=exc.__traceback__))
            )
            msg.exec_()
            return

    def _create_error_message_box_from_exception(
            self,
            exc: BaseException,
            window_title: Optional[str] = None,
            message: Optional[str] = None
    ) -> QtWidgets.QMessageBox:

        message_box = QtWidgets.QMessageBox(self.parent)
        message_box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        window_title = window_title or exc.__class__.__name__
        message_box.setWindowTitle(window_title)
        message = message or str(exc)
        message_box.setText(message)
        return message_box

    def start(self, item: typing.Type[Workflow]) -> None:
        """Start a workflow."""
        if self.work_manager.user_settings is None:
            raise RuntimeError("user_settings is not set")
        new_workflow = item(dict(self.work_manager.user_settings))

        # Add global settings to workflow
        assert isinstance(new_workflow, AbsWorkflow)

        # new_workflow.global_settings.update(
        #     dict(self.work_manager.user_settings))
        if self.options_model is None:
            raise RuntimeError("options_model not set")

        user_options = self.options_model.get()

        self.run(new_workflow, user_options)

    def get_item_options_model(
            self,
            workflow: typing.Type[Workflow]
    ) -> models.ToolOptionsModel4:
        """Get item options model."""
        if self.work_manager.user_settings is None:
            raise ValueError("user_settings not set")
        new_workflow = workflow(
            global_settings=dict(self.work_manager.user_settings)
        )
        return \
            qtwidgets.models.ToolOptionsModel4(new_workflow.get_user_options())


class WorkflowsTab2(WorkflowsTab):
    def __init__(self, parent: QtWidgets.QWidget,
                 workflows: typing.Mapping[str, Type[speedwagon.job.Workflow]],
                 # work_manager
                 ) -> None:
        super().__init__(parent, workflows)
        self._workflows = workflows
        self.signals = WorkflowSignals()

    def get_item_options_model(self, workflow):
        """Get item options model."""
        new_workflow = workflow(global_settings=self.parent.user_settings)
        return \
            qtwidgets.models.ToolOptionsModel4(new_workflow.get_user_options())

    def start(self, item: typing.Type[Workflow]) -> None:
        if self.options_model is None:
            raise RuntimeError("options_model not set")

        self.signals.start_workflow.emit(item.name, self.options_model.get())


class MyDelegate(QtWidgets.QStyledItemDelegate):

    def createEditor(  # pylint: disable=C0103
            self,
            parent: QtWidgets.QWidget,
            option: QtWidgets.QStyleOptionViewItem,
            index: typing.Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]
    ) -> QtWidgets.QWidget:

        if index.isValid():
            tool_settings = \
                index.data(
                    role=typing.cast(int, QtCore.Qt.ItemDataRole.UserRole)
                )

            browser_widget = tool_settings.edit_widget()
            if browser_widget:
                assert isinstance(
                    browser_widget,
                    qtwidgets.shared_custom_widgets.CustomItemWidget
                )
                browser_widget.editingFinished.connect(self.update_custom_item)
                browser_widget.setParent(parent)

                return browser_widget
        editor = super().createEditor(parent, option, index)
        editor.setAutoFillBackground(True)
        return editor

    # noinspection PyUnresolvedReferences
    def update_custom_item(self) -> None:
        # pylint: disable=no-member
        self.commitData.emit(self.sender())

    def setEditorData(  # pylint: disable=C0103
            self,
            editor: QtWidgets.QWidget,
            index: typing.Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]
    ) -> None:
        if index.isValid():
            i = index.data(
                role=typing.cast(int, QtCore.Qt.ItemDataRole.UserRole)
            )
            if isinstance(
                    editor,
                    qtwidgets.shared_custom_widgets.CustomItemWidget
            ):
                editor.data = i.data
        super().setEditorData(editor, index)

    def setModelData(  # pylint: disable=C0103
            self,
            widget: QtWidgets.QWidget,
            model: QtCore.QAbstractItemModel,
            index: typing.Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ],
    ) -> None:

        if isinstance(
                widget,
                qtwidgets.shared_custom_widgets.CustomItemWidget
        ):
            model.setData(index, widget.data)
            return
        super().setModelData(widget, model, index)


class TabData(NamedTuple):
    """Tab data."""

    tab_name: str
    workflows_model: models.WorkflowListModel2


def read_tabs_yaml(yaml_file: str) -> Iterator[TabData]:
    """Read a custom tab yaml file."""
    tabs_file_size = os.path.getsize(yaml_file)
    if tabs_file_size > 0:
        try:
            with open(yaml_file, encoding="utf-8") as file:
                tabs_config_data = \
                    yaml.load(file.read(), Loader=yaml.SafeLoader)
            if not isinstance(tabs_config_data, dict):
                raise TabsFileError("Failed to parse file")

            for tab_name in tabs_config_data:
                model = qtwidgets.models.WorkflowListModel2()
                for workflow_name in tabs_config_data.get(tab_name, []):
                    empty_workflow = \
                        cast(
                            Type[Workflow],
                            type(
                                workflow_name,
                                (NullWorkflow,),
                                {
                                    "name": workflow_name
                                }
                            )
                        )
                    model.add_workflow(empty_workflow)
                new_tab = TabData(tab_name, model)
                yield new_tab

        except FileNotFoundError as error:
            print(
                f"Custom tabs file not found. Reason: {error}",
                file=sys.stderr
            )
            raise
        except AttributeError as error:
            print(
                f"Custom tabs file failed to load. Reason: {error}",
                file=sys.stderr
            )
            raise

        except yaml.YAMLError as yaml_error:
            print(
                f"{yaml_file} file failed to load. "
                f"Reason: {yaml_error}",
                file=sys.stderr
            )
            raise


def write_tabs_yaml(yaml_file: str, tabs: List[TabData]) -> None:
    """Write out tab custom information to a yaml file."""
    tabs_data = {}
    for tab in tabs:
        tab_model = tab.workflows_model

        tabs_data[tab.tab_name] = \
            [workflow.name for workflow in tab_model.workflows]

    with open(yaml_file, "w", encoding="utf-8") as file_handle:
        yaml.dump(tabs_data, file_handle, default_flow_style=False)


def extract_tab_information(
        model: qtwidgets.models.TabsModel
) -> List[TabData]:
    """Get tab information."""
    tabs = []
    for tab in model.tabs:
        new_tab = TabData(tab.tab_name, tab.workflows_model)
        tabs.append(new_tab)
    return tabs
