"""Creating and managing tabs in the UI display."""
from __future__ import annotations

import typing
from typing import Optional, Type, Dict

from PySide6 import QtWidgets, QtCore  # type: ignore

from speedwagon.frontend.qtwidgets.models import workflows as workflow_models
from speedwagon.frontend.qtwidgets.models.common import WorkflowClassRole

import speedwagon
from speedwagon.config import StandardConfig, FullSettingsData
from speedwagon.job import Workflow
from speedwagon.frontend import qtwidgets

if typing.TYPE_CHECKING:
    from speedwagon.frontend.qtwidgets.widgets import (
        Workspace,
        SelectWorkflow,
        UserDataType,
    )


try:  # pragma: no cover
    from importlib.resources import as_file
    from importlib import resources
except ImportError:  # pragma: no cover
    import importlib_resources as resources  # type: ignore
    from importlib_resources import as_file


__all__ = ["WorkflowsTab3"]


class WorkflowsTab3UI(QtWidgets.QWidget):
    start_button: QtWidgets.QPushButton
    workspace: Workspace
    workflow_selector: SelectWorkflow

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        with as_file(
            resources.files("speedwagon.frontend.qtwidgets.ui").joinpath(
                "create_job_tab.ui"
            )
        ) as ui_file:
            qtwidgets.ui_loader.load_ui(str(ui_file), self)


class WorkflowsTab3(WorkflowsTab3UI):
    """Workflows tab - version 3."""

    start_workflow = QtCore.Signal(str, dict)
    workflow_selected = QtCore.Signal(object)
    settings_changed = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        """Create a new WorkflowTab3 object."""
        super().__init__(parent)
        self._parent = parent
        self.set_model(workflow_models.WorkflowList())
        self.app_settings_lookup_strategy = StandardConfig()
        self.start_button.clicked.connect(self.submit_job)
        self.workflow_selector.selected_index_changed.connect(
            self._handle_selector_changed
        )
        self._workflow_selected: Optional[Type[speedwagon.Workflow]] = None
        self.settings_changed.connect(self._update_okay_button)
        self.settings_changed.emit()

    def model(self) -> workflow_models.AbsWorkflowList:
        """Get the model used by the current tab."""
        return self._model

    def set_model(self, model: workflow_models.AbsWorkflowList) -> None:
        """Set the current model used by the tab."""
        self._model = model
        self.workflow_selector.model = self._model

    def _handle_selector_changed(self, index: QtCore.QModelIndex) -> None:
        workflow = self._model.data(index, WorkflowClassRole)

        self.workspace.set_workflow(workflow)
        self._handle_workflow_changed(workflow)

    def set_current_workflow(self, workflow_name: str) -> None:
        """Set current workflow by name."""
        self.workflow_selector.set_current_by_name(workflow_name)

    def set_current_workflow_settings(
        self, data: Dict[str, UserDataType]
    ) -> None:
        """Set settings for the current workflow."""
        workflow_klass = self.workflow_selector.get_current_workflow_type()
        if workflow_klass is None:
            raise ValueError(
                "Current Workflow not set. Workflow must be set first."
            )
        workflow_inst = workflow_klass(
            self.workspace.app_settings_lookup_strategy.settings()
        )
        qtwidgets.gui.load_job_settings_model(
            data, self.workspace.settings_form, workflow_inst.job_options()
        )

    def _handle_workflow_changed(
        self, workflow_klass: typing.Type[Workflow]
    ) -> None:
        self._workflow_selected = workflow_klass
        self.workspace.app_settings_lookup_strategy = (
            self.app_settings_lookup_strategy
        )
        self.settings_changed.emit()
        self.workflow_selected.emit(workflow_klass)

    def get_app_config(self) -> FullSettingsData:
        """Get app configuration."""
        return self.app_settings_lookup_strategy.settings()

    def _update_okay_button(self) -> None:
        if self._workflow_selected is None:
            self.start_button.setEnabled(False)
        else:
            self.start_button.setEnabled(True)

    def submit_job(self) -> None:
        """Submit new job."""
        if not self.workspace.is_valid():
            message = "\n".join(self.workspace.settings_form.issues)
            config_error_dialog = QtWidgets.QMessageBox(self)
            config_error_dialog.setWindowTitle("Settings Error")
            config_error_dialog.setDetailedText(f"{message}")
            config_error_dialog.setText(
                "Speedwagon has a problem with current configuration "
                "settings"
            )
            config_error_dialog.exec_()
            return
        self.start_workflow.emit(
            self.workspace.name, self.workspace.configuration
        )

    @property
    def workflows(self) -> Dict[str, Type[speedwagon.Workflow]]:
        """Get all workflows."""
        workflows = {}
        for row_id in range(self._model.rowCount()):
            index = self._model.index(row_id, 0)
            workflow_name = self._model.data(index)
            workflows[workflow_name] = self._model.data(
                index, role=WorkflowClassRole
            )
        return workflows

    def add_workflow(self, workflow: Type[speedwagon.Workflow]) -> None:
        """Add a new workflow to the tab."""
        if self._model is None:
            return
        self._model.add_workflow(workflow)

    def current_workflow(self) -> str:
        """Get the name of the current workflow."""
        return self._model.data(
            self.workflow_selector.workflowSelectionView.currentIndex()
        )
