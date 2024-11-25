"""Workflows model code."""

from __future__ import annotations

import typing
from typing import (
    Type,
    Optional,
    List,
    cast,
    Union,
    overload,
    Any,
)

from PySide6 import QtCore

import speedwagon.job
from .common import (
    AbsWorkflowItemData,
    WorkflowItemData,
    WorkflowClassRole,
    AbsWorkflowList,
)
from .tabs import TabStandardItem, TabsTreeModel

__all__ = [
    "WorkflowList",
    "WorkflowListProxyModel",
]

DEFAULT_QMODEL_INDEX = QtCore.QModelIndex()


class WorkflowList(AbsWorkflowList):
    """List of workflow uninitiated classes."""

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        """Create a new workflow list model.

        Args:
            parent: Parent widget to control widget lifespan
        """
        super().__init__(parent)
        self._workflows: List[Type[speedwagon.job.Workflow]] = []
        self.data_strategy: AbsWorkflowItemData = WorkflowItemData()

    def rowCount(  # pylint: disable=invalid-name
        self,
        parent: Union[  # pylint: disable=unused-argument
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> int:
        """Get the number of workflows in the list."""
        return len(self._workflows)

    def add_workflow(self, workflow: Type[speedwagon.job.Workflow]) -> None:
        """Add workflow to list."""
        self._workflows.append(workflow)
        self.dataChanged.emit(len(self._workflows), len(self._workflows), 0)

    def data(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Get data."""
        return (
            self.data_strategy.data(self._workflows[index.row()], role)
            if index.isValid()
            else None
        )

    def insertRow(  # pylint: disable=invalid-name
        self,
        row: int,
        parent: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> bool:
        """Insert row with a Null Workflow."""
        self._workflows.insert(row, speedwagon.job.NullWorkflow)
        return super().insertRow(row, parent)

    def removeRow(  # pylint: disable=invalid-name
        self,
        row: int,
        parent: Union[  # pylint: disable=unused-argument
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> bool:
        """Remove row from model."""
        if row > len(self._workflows):
            return False
        self._workflows.pop(row)
        return True

    def setData(  # pylint: disable=invalid-name
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        value: Any,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        """Set data."""
        if not index.isValid():
            return False
        if role in [
            QtCore.Qt.ItemDataRole.EditRole,
            WorkflowClassRole,
        ]:
            self._workflows[index.row()] = value
            return True
        return super().setData(index, value, role)


class WorkflowListProxyModel(QtCore.QAbstractProxyModel, AbsWorkflowList):
    """Proxy model for workflows.

    Uses the tab index of tree model to proxy list model data.
    """

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        """Create a new workflow list proxy model.

        Args:
            parent: Parent widget to control widget lifespan
        """
        super().__init__(parent)
        self._tab_index = 0
        self._current_tab_item: Optional[TabStandardItem] = None

    def set_tab_index(self, index: int) -> None:
        """Set the current tab used by tab's index."""
        source_model = typing.cast(Optional[TabsTreeModel], self.sourceModel())
        if source_model is None:
            return

        self.beginResetModel()
        self._tab_index = index
        item_index = source_model.index(self._tab_index, 0)
        self._current_tab_item = typing.cast(
            TabStandardItem, source_model.get_item(item_index)
        )
        self.endResetModel()

    def rowCount(  # pylint: disable=invalid-name
        self,
        parent: Union[  # pylint: disable=unused-argument
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> int:
        """Get the number of workflows in the list."""
        source_model = typing.cast(Optional[TabsTreeModel], self.sourceModel())
        if source_model is None:
            return 0
        return source_model.rowCount(source_model.index(self._tab_index, 0))

    def columnCount(  # pylint: disable=invalid-name
        self,
        parent: Union[  # pylint: disable=unused-argument
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> int:
        """Get column count."""
        return 0 if self.sourceModel() is None else 1

    def index(
        self,
        row: int,
        column: int = 0,
        parent: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> QtCore.QModelIndex:
        """Get index."""
        if parent.isValid():
            return QtCore.QModelIndex()
        return self.createIndex(row, column)

    def mapFromSource(  # pylint: disable=invalid-name
        self,
        source_index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
    ) -> QtCore.QModelIndex:
        """Map from source index."""
        return (
            self.index(row=source_index.row(), column=0)
            if source_index.isValid()
            else QtCore.QModelIndex()
        )

    def mapToSource(  # pylint: disable=invalid-name
        self,
        proxy_index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
    ) -> QtCore.QModelIndex:
        """Map to source index."""
        source_model = typing.cast(Optional[TabsTreeModel], self.sourceModel())
        if not proxy_index.isValid() or source_model is None:
            return QtCore.QModelIndex()

        return source_model.index(
            row=proxy_index.row(),
            column=proxy_index.column(),
            parent=source_model.index(self._tab_index, 0),
        )

    @overload
    def parent(
        self, index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.QModelIndex:
        ...

    @overload
    def parent(self) -> QtCore.QObject:
        ...

    def parent(
        self,
        index: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex, None
        ] = None,
    ) -> Union[QtCore.QModelIndex, QtCore.QObject]:
        """Get the parent object or object."""
        return QtCore.QObject() if index is None else QtCore.QModelIndex()

    def set_by_name(self, name: str) -> None:
        """Get active tab using the name of the tab."""
        source_model = cast(Optional[TabsTreeModel], self.sourceModel())
        if source_model is None:
            return

        for i in range(source_model.rowCount()):
            item = cast(
                TabStandardItem,
                source_model.get_item(source_model.index(row=i, column=0)),
            )
            if item.name == name:
                self.set_tab_index(i)
                break
        else:
            raise ValueError(f"Parent model does not contain tab {name}")

    @property
    def current_tab_name(self) -> Optional[str]:
        """Get current tab name."""
        return (
            None
            if self._current_tab_item is None
            else self._current_tab_item.name
        )

    def add_workflow(self, workflow: Type[speedwagon.job.Workflow]) -> None:
        """Add workflow to list."""
        if self._current_tab_item is None:
            raise RuntimeError("model not set")
        start_index = self._current_tab_item.index()
        self.beginInsertRows(
            start_index,
            self._current_tab_item.rowCount(),
            self._current_tab_item.rowCount(),
        )
        self._current_tab_item.append_workflow(workflow)
        source_model = self.sourceModel()
        source_model.dataChanged.emit(
            source_model.index(self._tab_index, 0), source_model.rowCount()
        )
        self.endInsertRows()

    def remove_workflow(self, workflow: Type[speedwagon.job.Workflow]) -> None:
        """Remove workflow from list."""
        if self._current_tab_item is None:
            raise RuntimeError("model not set")
        self.beginRemoveRows(
            self._current_tab_item.index(),
            0,
            self._current_tab_item.rowCount(),
        )
        self._current_tab_item.remove_workflow(workflow)
        self.endRemoveRows()
