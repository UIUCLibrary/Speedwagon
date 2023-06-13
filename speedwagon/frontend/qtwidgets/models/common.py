"""Common items used by all model code.

This is mainly to avoid circular imports.
"""
from __future__ import annotations

import abc
from typing import Optional, Type, Union, Any, cast

from PySide6 import QtGui, QtCore

import speedwagon
from speedwagon.job import Workflow

__all__ = [
    "WorkflowItem",
    "WorkflowClassRole",
    "AbsWorkflowList",
    "WorkflowItemData",
    "AbsWorkflowItemData",
]


class AbsWorkflowList(  # pylint: disable=too-few-public-methods
    QtCore.QAbstractListModel
):
    """Abstract workflow list model."""

    def add_workflow(self, workflow: Type[speedwagon.Workflow]) -> None:
        """Add a workflow to the model."""
        raise NotImplementedError


class WorkflowItem(QtGui.QStandardItem):
    """Workflow metadata data."""

    def __init__(self, workflow: Optional[Type[Workflow]]) -> None:
        """Create a new Workflow item.

        Args:
            workflow:  Speedwagon Workflow
        """
        super().__init__()
        self.workflow = workflow
        if workflow is not None and workflow.name is not None:
            self.setText(workflow.name)

    def columnCount(self) -> int:  # pylint: disable=invalid-name
        """Get column count."""
        return 2

    @property
    def name(self) -> Optional[str]:
        """Get the name used by the workflow."""
        return None if self.workflow is None else self.workflow.name


class AbsWorkflowItemData(abc.ABC):  # pylint: disable=too-few-public-methods
    """Abstract base class for workflow item data."""

    def data(
        self,
        workflow: Type[speedwagon.Workflow],
        role: Union[int, QtCore.Qt.ItemDataRole],
    ) -> Any:
        """Get the data from workflow."""


WorkflowClassRole = cast(int, QtCore.Qt.ItemDataRole.UserRole) + 1


class WorkflowItemData(  # pylint: disable=too-few-public-methods
    AbsWorkflowItemData
):
    """Workflow Item Data."""

    def data(
        self,
        workflow: Type[speedwagon.Workflow],
        role: Union[int, QtCore.Qt.ItemDataRole],
    ) -> Any:
        """Get the data from workflow."""
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return workflow.name
        if role == WorkflowClassRole:
            return workflow
        return None
