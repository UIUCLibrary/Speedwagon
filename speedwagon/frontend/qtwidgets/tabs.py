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
from speedwagon.frontend.qtwidgets.widgets import DynamicForm

from speedwagon import runner_strategies
from speedwagon.frontend import qtwidgets

from speedwagon.exceptions import MissingConfiguration, InvalidConfiguration
from speedwagon.job import AbsWorkflow, NullWorkflow, Workflow
from speedwagon.frontend.qtwidgets import models

if typing.TYPE_CHECKING:
    from speedwagon.frontend.qtwidgets.worker import ToolJobManager
    from speedwagon.workflow import AbsOutputOptionDataType


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

        self.workspace_group_box = QtWidgets.QGroupBox(parent)
        self.workspace_group_box.setLayout(QtWidgets.QVBoxLayout())
        self.workspace_group_box.setTitle(self.tab_name)

        self._workspace_widget = \
            qtwidgets.widgets.get_workspace(
                self.item_selection_model,
                parent=parent
            )
        self.workspace_group_box.layout().addWidget(self._workspace_widget)
        self.settings_form = DynamicForm(parent=self.workspace_group_box)

        self.actions_widgets, self.actions_layout = self.create_actions()
        if self.item_selection_model.rowCount() == 0:
            self.item_selector_view.setVisible(False)
            self.workspace_group_box.setVisible(False)
            # self.workspace.setVisible(False)
            self._empty_tab_message = QtWidgets.QLabel()
            self._empty_tab_message.setText("No items available to display")
            self.tab_layout.addWidget(self._empty_tab_message)

        self.init_selection()
        self._workspace_widget.layout().replaceWidget(
            self._workspace_widget.settingsWidget,
            self.settings_form
        )
        self.tab_layout.addWidget(self.workspace_group_box)
        self.compose_tab_layout()

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
        selection_model = selector_view.selectionModel()
        selection_model.currentChanged.connect(  # type: ignore
            self._update_tool_selected
        )

        return selector_view

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
        self.settings_form.update_model()
        selected_workflow = cast(
            typing.Type[Workflow],
            self.item_selection_model.data(
                self.item_selector_view.selectedIndexes()[0],
                role=typing.cast(int, QtCore.Qt.ItemDataRole.UserRole)
            )
        )
        try:
            self.warn_user_of_invalid_settings(
                workflow=selected_workflow,
                checks=[
                    models.check_required_settings_have_values,
                ]
            )
        except InvalidConfiguration:
            return
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
                self._workspace_widget.tool_mapper.setCurrentModelIndex(
                    current
                )
        except Exception as error:
            if previous.isValid():
                self.item_selected(previous)
                self._workspace_widget.tool_mapper.setCurrentModelIndex(
                    previous
                )

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

        #################
        try:
            model = self.get_item_options_model(item)
            self.options_model = model
            self.settings_form.setModel(self.options_model)

            self.settings_form.setSizePolicy(ITEM_SETTINGS_POLICY)
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
            layout = cast(
                QtWidgets.QGridLayout,
                warning_message_dialog.layout()
            )

            layout.addItem(
                spanner, layout.rowCount(), 0, 1, layout.columnCount())

            warning_message_dialog.exec()

            self.log_manager.warning(message)
            raise

    def compose_tab_layout(self) -> None:
        """Build the tab widgets."""
        self.tab_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.tab_layout.addWidget(self.item_selector_view)
        self.tab_layout.addWidget(self.workspace_group_box)
        self.workspace_group_box.setFixedHeight(300)
        actions = QtWidgets.QWidget()
        actions.setLayout(self.actions_layout)
        self.tab_layout.addWidget(actions)

    def warn_user_of_invalid_settings(
            self,
            checks: List[
                typing.Callable[[AbsOutputOptionDataType], Optional[str]]
            ],
            workflow: Optional[Type[Workflow]] = None,
    ) -> None:
        if not self.options_model:
            return
        errors = models.get_settings_errors(self.options_model, checks)
        if workflow:
            workflow_error = \
                get_workflow_errors(self.options_model.get(), workflow)
            if workflow_error:
                errors.append(workflow_error)
        if not errors:
            return
        error_message = '\n'.join(errors)
        config_error_dialog = QtWidgets.QMessageBox(self.parent)
        config_error_dialog.setWindowTitle("Settings Error")
        config_error_dialog.setDetailedText(f"{error_message}")
        config_error_dialog.setText(
            "Speedwagon has a problem with current configuration "
            "settings"
        )
        config_error_dialog.exec_()
        raise InvalidConfiguration(errors)


def get_workflow_errors(options, workflow):
    try:
        workflow.validate_user_options(**options)
    except ValueError as error:
        return str(error)
    return None


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
        user_options = self.get_item_user_options(workflow)
        return \
            qtwidgets.models.ToolOptionsModel4(user_options)

    def get_item_user_options(self, workflow: typing.Type[Workflow]):
        if self.work_manager.user_settings is None:
            raise ValueError("user_settings not set")
        new_workflow = workflow(
            global_settings=dict(self.work_manager.user_settings)
        )
        return new_workflow.get_user_options()


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
