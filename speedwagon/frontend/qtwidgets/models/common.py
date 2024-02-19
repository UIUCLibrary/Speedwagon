"""Common items used by all model code.

This is mainly to avoid circular imports.
"""
from __future__ import annotations

import abc
from typing import (
    Optional,
    Type,
    Union,
    Any,
    Generic,
    cast,
    Callable,
    List,
    TypeVar,
    Sequence,
    TYPE_CHECKING
)
from copy import deepcopy

from PySide6 import QtGui, QtCore

if TYPE_CHECKING:
    from speedwagon.job import Workflow

__all__ = [
    "WorkflowItem",
    "WorkflowClassRole",
    "AbsWorkflowList",
    "WorkflowItemData",
    "AbsWorkflowItemData",
    "ItemTableModel"
]


class AbsWorkflowList(  # pylint: disable=too-few-public-methods
    QtCore.QAbstractListModel
):
    """Abstract workflow list model."""

    def add_workflow(self, workflow: Type[Workflow]) -> None:
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


class AbsWorkflowItemData(abc.ABC):  # noqa: B024 pylint: disable=R0903
    """Abstract base class for workflow item data."""

    def data(  # noqa: B027
        self,
        workflow: Type[Workflow],
        role: Union[int, QtCore.Qt.ItemDataRole],
    ) -> Any:
        """Get the data from workflow.

        By default, this method is a no-op unless overridden.
        """


WorkflowClassRole = cast(int, QtCore.Qt.ItemDataRole.UserRole) + 1


class WorkflowItemData(  # pylint: disable=too-few-public-methods
    AbsWorkflowItemData
):
    """Workflow Item Data."""

    def data(
        self,
        workflow: Type[Workflow],
        role: Union[int, QtCore.Qt.ItemDataRole],
    ) -> Any:
        """Get the data from workflow."""
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return workflow.name
        if role == WorkflowClassRole:
            return workflow
        return None


T = TypeVar("T")
_RT = TypeVar("_RT")


class ItemTableModel(QtCore.QAbstractTableModel, Generic[T, _RT]):
    """Qt tablemodel for generic tabular date."""

    keys: Sequence[str]

    OptionsRole = QtCore.Qt.ItemDataRole.UserRole + 1

    def __init__(
        self,
        keys: Sequence[str],
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        """Create a new ItemTableModel Object."""
        super().__init__(parent)
        self.keys = keys
        self.rows: List[Sequence[T]] = []

        self.is_editable_rule: Callable[
            [
                Sequence[T],
                Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
            ],
            bool
        ] = lambda item, index: False

        self.display_role: Callable[
            [
                Sequence[T],
                Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
            ],
            Union[str, None]
        ] = lambda item, index: str(self.rows[index.row()])

        self.process_results: Callable[
            [List[Sequence[T]]], Optional[_RT]
        ] = lambda data: None

        self.options_role: Callable[
            [
                Sequence[T],
                Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
            ],
            Sequence[str]
        ] = lambda item, index: []
        self.update_data: Callable[
            [
                str,
                Sequence[T],
                Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
            ],
            Sequence[T]
        ] = lambda value, existing_row, index: existing_row

    def columnCount(
        self,
        parent: Optional[  # pylint: disable=unused-argument
            Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ] = None
    ) -> int:
        """Column count."""
        return len(self.keys)

    def rowCount(
        self,
        parent: Optional[  # pylint: disable=unused-argument
            Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ] = None
    ) -> int:
        """Row count."""
        return len(self.rows)

    def add_item(self, item: Sequence[T]) -> None:
        """Add row."""
        self.rows.append(item)

    def headerData(  # pylint: disable=C0103
        self,
        index: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Union[str, QtCore.QObject]:
        """Get model header information."""
        if (
                role == QtCore.Qt.ItemDataRole.DisplayRole
                and orientation == QtCore.Qt.Orientation.Horizontal
        ):
            try:
                return self.keys[index]
            except IndexError:
                return ""
        return super().headerData(index, orientation, role)

    def flags(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.Qt.ItemFlag:
        """Set flags for index."""
        default_flags = QtCore.QAbstractItemModel.flags(self, index)
        if self.is_editable_rule(self.rows[index.row()], index):
            return cast(
                QtCore.Qt.ItemFlag,
                (
                    QtCore.Qt.ItemFlag.ItemIsEditable |
                    QtCore.Qt.ItemFlag.ItemIsEnabled |
                    default_flags
                )
            )
        return default_flags

    def data(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        role=QtCore.Qt.ItemDataRole.DisplayRole
    ):
        """Get data."""
        row = self.rows[index.row()]
        if role == self.OptionsRole:
            return self.options_role(row, index)
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self.display_role(row, index)
        return None

    def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
        """Set data."""
        if role == QtCore.Qt.ItemDataRole.EditRole:
            existing_row = deepcopy(self.rows[index.row()])
            new_row_data = self.update_data(
                value,
                self.rows[index.row()],
                index
            )
            if new_row_data == existing_row:
                return False
            self.rows[index.row()] = new_row_data
            return True

        return False

    def results(self) -> Optional[_RT]:
        """Get the results of the module after being processed."""
        return self.process_results(self.rows)
