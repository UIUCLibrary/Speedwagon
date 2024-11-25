"""Tabs model code."""

from __future__ import annotations

import abc
from typing import (
    Optional,
    Type,
    Union,
    overload,
    Dict,
    List,
    cast,
    Iterator,
    Any,
    TYPE_CHECKING,
)

from PySide6 import QtCore, QtGui

import speedwagon.config.tabs as tabs_config
from speedwagon.config.config import StandardConfigFileLocator
import speedwagon.job
from .common import WorkflowItem, WorkflowClassRole, AbsWorkflowList
if TYPE_CHECKING:
    from speedwagon.config import AbsTabsConfigDataManagement

__all__ = ["TabsTreeModel", "TabStandardItem", "TabProxyModel"]

DEFAULT_QMODEL_INDEX = QtCore.QModelIndex()


class TabsTreeModel(QtCore.QAbstractItemModel):
    """Tree model containing user defined tabs and the containing workflows."""

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        """Create a new tab tree model.

        Args:
            parent: Parent widget to control widget lifespan
        """
        super().__init__(parent)
        self.root_item = QtGui.QStandardItem()
        self._starting_rows = self.rowCount()

    def append_workflow_tab(
        self,
        name: str,
        workflows: Optional[List[Type[speedwagon.job.Workflow]]] = None,
    ) -> None:
        """Add a new tab."""
        new_tab = TabStandardItem(name, workflows or [])
        self.root_item.appendRow(new_tab)
        self.modelReset.emit()

    @property
    def data_modified(self) -> bool:
        """Get if the data contained has changed since last reset."""
        if self._starting_rows != self.rowCount():
            return True
        return any(tab.data_modified for tab in self.tabs)

    @property
    def tabs(self) -> Iterator[TabStandardItem]:
        """Get all the tbs in the tree model."""
        for row_id in range(self.rowCount()):
            yield cast(TabStandardItem, self.get_item(self.index(row_id, 0)))

    def columnCount(  # pylint: disable=invalid-name
        self,
        parent: Union[  # pylint: disable=unused-argument
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> int:
        """Get column count."""
        return 2

    def rowCount(  # pylint: disable=invalid-name
        self,
        parent: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> int:
        """Get the number of tabs in the model."""
        if parent.isValid() and parent.column() > 2:
            return 0
        parent_item = self.get_item(parent)
        return parent_item.rowCount() if parent_item else 0

    def index(
        self,
        row: int,
        column: int = 0,
        parent: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> QtCore.QModelIndex:
        """Get index."""
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        child_item = self.get_item(parent).child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        return QtCore.QModelIndex()

    @overload
    def parent(
        self, child: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.QModelIndex:
        ...

    @overload
    def parent(self) -> QtCore.QObject:
        ...

    def parent(
        self,
        child: Union[
            QtCore.QModelIndex,
            QtCore.QPersistentModelIndex,
        ] = DEFAULT_QMODEL_INDEX,
    ) -> Union[QtCore.QModelIndex, QtCore.QObject]:
        """Get the parent object or object."""
        if not child.isValid():
            return QtCore.QModelIndex()
        child_item = self.get_item(child)
        parent_item = child_item.parent()
        if parent_item == self.root_item or not parent_item:
            return QtCore.QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    @staticmethod
    def get_workflow_item_data(
        item: WorkflowItem, column: int, role: int
    ) -> Any:
        """Get the right data for the data model for a given role."""
        if role == QtGui.Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return str(item.name or "")
            if column == 1:
                return (
                    ""
                    if item.workflow is None
                    else str(item.workflow.description or "")
                )
        return item.workflow if role == WorkflowClassRole else None

    def data(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Get data."""
        if not index.isValid():
            return None
        item = self.get_item(index)
        if isinstance(item, TabStandardItem):
            return item.data(role=role) if index.column() == 0 else None
        if isinstance(item, WorkflowItem):
            return self.get_workflow_item_data(item, index.column(), role)
        return None

    def get_item(
        self,
        index: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> Union[QtGui.QStandardItem, TabStandardItem, WorkflowItem]:
        """Get item at a given index."""
        if index.isValid():
            item = index.internalPointer()
            if item:
                return cast(TabStandardItem, item)
        return self.root_item

    def headerData(  # pylint: disable=invalid-name
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtGui.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Get header data."""
        if (
            orientation == QtCore.Qt.Orientation.Horizontal
            and role == QtGui.Qt.ItemDataRole.DisplayRole
        ):
            if section == 0:
                return "Name"
            if section == 1:
                return "Description"
        return super().headerData(section, orientation, role)

    def get_tab(self, tab_name: str) -> Optional[TabStandardItem]:
        """Get a tab of a given name."""
        for i in range(self.rowCount()):
            index = self.index(i, 0)
            if self.data(index) == tab_name:
                return cast(TabStandardItem, self.get_item(index))
        return None

    def append_workflow_to_tab(
        self, tab_name: str, workflow: Type[speedwagon.Workflow]
    ) -> None:
        """Append a workflow to a tab with a given name."""
        tab = self.get_tab(tab_name)
        if tab is None:
            raise ValueError(f"No tab named {tab_name}")
        tab.append_workflow(workflow)

    @property
    def tab_names(self) -> List[str]:
        """Get the tabs of the tabs in the model."""
        return [self.data(self.index(i, 0)) for i in range(self.rowCount())]

    def removeRow(  # pylint: disable=invalid-name
        self,
        row: int,
        parent: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> bool:
        """Remove row from model."""
        if parent.isValid():
            item = self.get_item(parent)
            if isinstance(item, TabStandardItem):
                item.removeRow(row)
                return True
            return False
        original_row_count = self.root_item.rowCount()
        self.root_item.removeRow(row)
        resulting_row_count = self.root_item.rowCount()
        return resulting_row_count < original_row_count

    def reset_modified(self) -> None:
        """Reset the data so that appears unmodified."""
        self._starting_rows = self.rowCount()
        for tab in self.tabs:
            tab.reset_modified()
        self.dataChanged.emit(self.root_item.index(), [])

    def tab_information(self) -> List[tabs_config.CustomTabData]:
        """Get the custom tab data for all the tabs in the model."""
        return [
            tabs_config.CustomTabData(
                tab.name, [work.name or "" for work in tab.workflows]
            )
            for tab in self.tabs
        ]

    def __len__(self) -> int:
        """Get the size in terms of rows."""
        return self.rowCount()

    def __getitem__(self, item: int) -> TabStandardItem:
        """Get item via a numerical index."""
        for i, tab in enumerate(self.tabs):
            if i == item:
                return tab
        raise IndexError(f"{item} not found in model.")

    def clear(self) -> None:
        """Clear all the data in the model."""
        for row_id in range(self.rowCount()):
            self.removeRow(row_id)

    def setData(  # pylint: disable=invalid-name
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        value: Any,
        role: int = QtGui.Qt.ItemDataRole.DisplayRole,
    ) -> bool:
        """Set data."""
        if role == WorkflowClassRole:
            cast(WorkflowItem, self.get_item(index)).workflow = value
            return True
        return super().setData(index, value, role)


class TabProxyModel(QtCore.QAbstractProxyModel, AbsWorkflowList):
    """Proxy model for tab tree model data.

    For limiting the scope to a single tab.
    """

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        """Create a new tab proxy model.

        Args:
            parent: Parent widget to control widget lifespan
        """
        super().__init__(parent)
        self.source_tab: Optional[str] = None

    def add_workflow(self, workflow: Type[speedwagon.Workflow]) -> None:
        """Add workflow to list."""
        if self.source_tab is None:
            raise RuntimeError("source_tab not set")
        base_index = self.get_source_tab_index(self.source_tab)
        if not base_index.isValid():
            return
        item = base_index.internalPointer()
        if isinstance(item, TabStandardItem):
            if workflow in item:
                return
            self.beginResetModel()
            item.append_workflow(workflow)
            self.endResetModel()

    def remove_workflow(self, workflow: Type[speedwagon.Workflow]):
        """Remove workflow from list."""
        if self.source_tab is None:
            raise RuntimeError("source_tab not set")
        source_model = self.sourceModel()
        self.beginResetModel()
        base_index = self.get_source_tab_index(self.source_tab)
        for row_id in reversed(
            range(source_model.rowCount(parent=base_index))
        ):
            if (
                source_model.data(
                    source_model.index(row_id, 0, parent=base_index),
                    role=WorkflowClassRole,
                )
                == workflow
            ):
                self.beginRemoveRows(base_index, row_id, row_id + 1)
                source_model.removeRow(row_id, parent=base_index)
                self.endRemoveRows()

    def sort(
        self,
        column: int,
        order: QtCore.Qt.SortOrder = QtCore.Qt.SortOrder.AscendingOrder,
    ) -> None:
        """Sort data."""
        if self.source_tab is None:
            return
        base_index = self.get_source_tab_index(self.source_tab)
        if not base_index.isValid():
            return
        item = base_index.internalPointer()
        if isinstance(item, TabStandardItem):
            item.sortChildren(column, order)
        super().sort(column, order)

    def set_source_tab(self, tab_name: str) -> None:
        """Set the source tab from the source model to use."""
        self.beginResetModel()
        self.source_tab = tab_name
        self.endResetModel()

    def get_source_tab_index(self, tab_name: str) -> QtCore.QModelIndex:
        """Get the index of a tab with a given name."""
        source_model = self.sourceModel()
        if source_model is None:
            return QtCore.QModelIndex()

        for row_id in range(source_model.rowCount()):
            index = source_model.index(row_id, 0)
            if (
                source_model.data(index, QtCore.Qt.ItemDataRole.DisplayRole)
                == tab_name
            ):
                return index
        return QtCore.QModelIndex()

    def rowCount(  # pylint: disable=invalid-name
        self,
        parent: Union[  # pylint: disable=unused-argument
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> int:
        """Get the number of workflows in the list."""
        if self.source_tab is None:
            return 0
        index = self.get_source_tab_index(self.source_tab)
        source_model = self.sourceModel()
        if source_model is None:
            return 0
        return source_model.rowCount(index) if index.isValid() else 0

    def mapFromSource(  # pylint: disable=invalid-name
        self,
        sourceIndex: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
    ) -> QtCore.QModelIndex:
        """Map from source index."""
        return (
            self.index(row=sourceIndex.row(), column=0)
            if sourceIndex.isValid()
            else QtCore.QModelIndex()
        )

    def columnCount(  # pylint: disable=invalid-name
        self,
        parent: Optional[  # pylint: disable=unused-argument
            Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ] = None,
    ) -> int:
        """Get column count."""
        return 1

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

    def mapToSource(  # pylint: disable=invalid-name
        self,
        proxyIndex: Union[  # pylint: disable=invalid-name
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ],
    ) -> QtCore.QModelIndex:
        """Map to source index."""
        if self.source_tab is None:
            return QtCore.QModelIndex()
        base_index = self.get_source_tab_index(self.source_tab)
        if not proxyIndex.isValid() and base_index is not None:
            return QtCore.QModelIndex()

        source_model = self.sourceModel()
        proxy_index = proxyIndex
        return source_model.index(
            row=proxy_index.row(),
            column=proxy_index.column(),
            parent=base_index,
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

    def get_tab_index(self) -> QtCore.QModelIndex:
        """Get cyrrent tab index."""
        if self.source_tab is None:
            raise RuntimeError("source model not set")
        return self.get_source_tab_index(self.source_tab)


class AbsLoadTabDataModelStrategy(abc.ABC):  # pylint: disable=R0903
    @abc.abstractmethod
    def load(self, model: TabsTreeModel) -> None:
        """Load data."""


class TabDataModelYAMLLoader(AbsLoadTabDataModelStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.yml_file: Optional[str] = None

    @staticmethod
    def prep_data(
        data_load_strategy: AbsTabsConfigDataManagement,
    ) -> Dict[str, List[Type[speedwagon.Workflow]]]:
        all_workflows = speedwagon.job.available_workflows()

        sorted_workflows = sorted(
            list(all_workflows.values()), key=lambda item: item.name
        )

        workflow_tabs_data: Dict[str, List[Type[speedwagon.Workflow]]] = {
            "All": sorted_workflows
        }
        for tab_data in data_load_strategy.data():
            tab_workflows = []
            for workflow_name in tab_data.workflow_names:
                if workflow_name in all_workflows:
                    workflow_klass = all_workflows[workflow_name]
                    tab_workflows.append(workflow_klass)
            workflow_tabs_data[tab_data.tab_name] = tab_workflows

        return workflow_tabs_data

    def load(self, model: TabsTreeModel) -> None:
        if self.yml_file is None:
            return
        data = self.prep_data(
            data_load_strategy=speedwagon.config.tabs.CustomTabsYamlConfig(
                self.yml_file
            )
        )
        for tab_name, workflows in data.items():
            model.append_workflow_tab(tab_name, workflows)
        model.reset_modified()
        model.modelReset.emit()


class TabDataModelConfigLoader(TabDataModelYAMLLoader):
    def __init__(self) -> None:
        super().__init__()
        config_strategy = StandardConfigFileLocator()
        self.yml_file = config_strategy.get_tabs_file()


class TabStandardItem(QtGui.QStandardItem):
    """QStandardItem that contains tab workflows data."""

    def __init__(
        self,
        name: Optional[str] = None,
        workflows: Optional[List[Type[speedwagon.Workflow]]] = None,
    ) -> None:
        """Create a new TabStandardItem."""
        super().__init__()
        if name:
            self.setText(name)
        self._unmodified_workflows: List[WorkflowItem] = []
        self.reset_modified()
        for workflow in workflows or []:
            self.append_workflow(workflow)

    @property
    def workflows(self) -> list[WorkflowItem]:
        """Get the list of workflows in the tab."""
        return [
            cast(WorkflowItem, self.child(row_id, 0))
            for row_id in range(self.rowCount())
        ]

    @property
    def data_modified(self) -> bool:
        """Get if the data contained has changed since last reset."""
        if len(self.workflows) != len(self._unmodified_workflows):
            return True

        return any(
            current.workflow != unmodified.workflow
            for current, unmodified in zip(
                self.workflows, self._unmodified_workflows
            )
        )

    def reset_modified(self) -> None:
        """Reset the data so that appears unmodified."""
        self._unmodified_workflows = self.workflows.copy()

    @property
    def name(self) -> str:
        """Get the name used by the tab."""
        return self.text()

    def append_workflow(self, workflow: Type[speedwagon.Workflow]) -> None:
        """Add a workflow to the list."""
        if workflow not in self:
            self.appendRow(WorkflowItem(workflow))
            self.emitDataChanged()

    def __contains__(self, workflow: Type[speedwagon.Workflow]) -> bool:
        """Check if workflow in already in item."""
        for row_id in range(self.rowCount()):
            item = cast(WorkflowItem, self.child(row_id, 0))
            if item.workflow == workflow:
                return True
        return False

    def remove_workflow(self, workflow: Type[speedwagon.Workflow]) -> None:
        """Remove workflow from list."""

        def _find_row_with_matching_workflow() -> Optional[int]:
            for row_id in range(self.rowCount()):
                item = cast(WorkflowItem, self.child(row_id, 0))
                if item.workflow == workflow:
                    return row_id
            return None

        while True:
            row_id_to_delete = _find_row_with_matching_workflow()
            if row_id_to_delete is None:
                break
            self.removeRow(row_id_to_delete)
