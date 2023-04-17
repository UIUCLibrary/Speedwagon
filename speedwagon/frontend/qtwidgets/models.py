"""Data models for displaying data to user in the user interface."""
from __future__ import annotations
import abc
from collections import namedtuple
import configparser
import enum
import os

import typing
from typing import \
    Type, \
    Dict, \
    List, \
    Any, \
    Union, \
    Tuple, \
    Optional, \
    cast, \
    Iterator, \
    overload


try:
    from typing import Final
except ImportError:  # pragma: no cover
    from typing_extensions import Final  # type: ignore
from dataclasses import dataclass
import sys

from PySide6.QtCore import QAbstractItemModel
from PySide6 import QtCore, QtGui  # type: ignore

from speedwagon.config import CustomTabData
import speedwagon

if typing.TYPE_CHECKING:
    from speedwagon.job import Workflow
    from speedwagon.workflow import AbsOutputOptionDataType, UserDataType
    from speedwagon.config import (
        SettingsDataType,
        SettingsData,
        AbsTabsConfigDataManagement
    )
if sys.version_info < (3, 10):  # pragma: no cover
    import importlib_metadata as metadata
else:  # pragma: no cover
    from importlib import metadata


__all__ = [
    # "WorkflowListModel2",
    "ToolOptionsModel4",
    "SettingsModel",
    # "TabsModel"
]

QtConstant = int

# Qt has non-pythonic method names
# pylint: disable=invalid-name, unused-argument


class JobModelData(enum.Enum):
    NAME = 0
    DESCRIPTION = 1


OptionPair = namedtuple("OptionPair", ("label", "data"))


class AbsWorkflowList(QtCore.QAbstractListModel):

    def add_workflow(self, workflow: Type[Workflow]) -> None:
        raise NotImplementedError


class WorkflowListProxyModel(QtCore.QAbstractProxyModel, AbsWorkflowList):

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._tab_index = 0
        self._current_tab_item: Optional[TabStandardItem] = None

    def set_tab_index(self, index: int) -> None:
        source_model = typing.cast(
            Optional[TabsTreeModel],
            self.sourceModel()
        )
        if source_model is None:
            return

        self.beginResetModel()
        self._tab_index = index
        item_index = source_model.index(self._tab_index, 0)
        self._current_tab_item = \
            typing.cast(TabStandardItem, source_model.get_item(item_index))
        self.endResetModel()

    def rowCount(
            self,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = QtCore.QModelIndex()
    ) -> int:
        source_model = typing.cast(
            Optional[TabsTreeModel],
            self.sourceModel()
        )
        if source_model is None:
            return 0
        return source_model.rowCount(source_model.index(self._tab_index, 0))

    def columnCount(
            self,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex] = QtCore.QModelIndex()
    ) -> int:
        return 0 if self.sourceModel() is None else 1

    def index(
            self,
            row: int,
            column: int = 0,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = QtCore.QModelIndex()
    ) -> QtCore.QModelIndex:
        if parent.isValid():
            return QtCore.QModelIndex()
        return self.createIndex(row, column)

    def mapFromSource(
            self,
            source_index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]
    ) -> QtCore.QModelIndex:
        return (
            self.index(row=source_index.row(), column=0)
            if source_index.isValid()
            else QtCore.QModelIndex()
        )

    def mapToSource(
            self,
            proxy_index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]
    ) -> QtCore.QModelIndex:
        source_model = typing.cast(Optional[TabsTreeModel], self.sourceModel())
        if not proxy_index.isValid() or source_model is None:
            return QtCore.QModelIndex()

        return source_model.index(
            row=proxy_index.row(),
            column=proxy_index.column(),
            parent=source_model.index(self._tab_index, 0)
        )

    @overload
    def parent(self) -> QtCore.QObject:
        ...

    @overload
    def parent(
            self,
            index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.QModelIndex:
        ...

    def parent(
            self,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex,
                None
            ] = None
    ) -> Union[QtCore.QModelIndex, QtCore.QObject]:
        return QtCore.QObject() if index is None else QtCore.QModelIndex()

    def set_by_name(self, name: str) -> None:
        source_model = cast(Optional[TabsTreeModel], self.sourceModel())
        if source_model is None:
            return

        for i in range(source_model.rowCount()):
            item = cast(
                TabStandardItem,
                source_model.get_item(source_model.index(row=i, column=0))
            )
            if item.name == name:
                self.set_tab_index(i)
                break
        else:
            raise ValueError(f"Parent model does not contain tab {name}")

    @property
    def current_tab_name(self) -> Optional[str]:
        return (
            None if self._current_tab_item is None
            else self._current_tab_item.name
        )

    def add_workflow(self, workflow: Type[Workflow]) -> None:
        if self._current_tab_item is None:
            raise RuntimeError("model not set")
        start_index = self._current_tab_item.index()
        self.beginInsertRows(
            start_index,
            self._current_tab_item.rowCount(),
            self._current_tab_item.rowCount()
        )
        self._current_tab_item.append_workflow(workflow)
        source_model = self.sourceModel()
        source_model.dataChanged.emit(
            source_model.index(self._tab_index, 0),
            source_model.rowCount()
        )
        self.endInsertRows()

    def remove_workflow(self, workflow: Type[Workflow]) -> None:
        if self._current_tab_item is None:
            raise RuntimeError("model not set")
        self.beginRemoveRows(
            self._current_tab_item.index(),
            0,
            self._current_tab_item.rowCount()
        )
        self._current_tab_item.remove_workflow(workflow)
        self.endRemoveRows()


class TabProxyModel(QtCore.QAbstractProxyModel, AbsWorkflowList):

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.source_tab: Optional[str] = None

    def add_workflow(self, workflow: Type[Workflow]) -> None:
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

    def remove_workflow(self, workflow: Type[Workflow]):
        if self.source_tab is None:
            raise RuntimeError("source_tab not set")
        source_model = self.sourceModel()
        self.beginResetModel()
        base_index = self.get_source_tab_index(self.source_tab)
        for row_id in reversed(
                range(source_model.rowCount(parent=base_index))
        ):
            if source_model.data(
                    source_model.index(row_id, 0, parent=base_index),
                    role=TabsTreeModel.WorkflowClassRole
            ) == workflow:
                self.beginRemoveRows(base_index, row_id, row_id + 1)
                source_model.removeRow(row_id, parent=base_index)
                self.endRemoveRows()

    def sort(
            self,
            column: int,
            order: QtCore.Qt.SortOrder = QtCore.Qt.SortOrder.AscendingOrder
    ) -> None:
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
        self.beginResetModel()
        self.source_tab = tab_name
        self.endResetModel()

    def get_source_tab_index(self, tab_name: str) -> QtCore.QModelIndex:
        source_model = self.sourceModel()
        if source_model is None:
            return QtCore.QModelIndex()

        for row_id in range(source_model.rowCount()):
            index = source_model.index(row_id, 0)
            if source_model.data(
                    index,
                    QtCore.Qt.ItemDataRole.DisplayRole
            ) == tab_name:
                return index
        return QtCore.QModelIndex()

    def rowCount(
            self,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = QtCore.QModelIndex()) -> int:
        if self.source_tab is None:
            return 0
        index = self.get_source_tab_index(self.source_tab)
        source_model = self.sourceModel()
        if source_model is None:
            return 0
        return source_model.rowCount(index) if index.isValid() else 0

    def mapFromSource(
            self,
            sourceIndex: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]
    ) -> QtCore.QModelIndex:
        return (
            self.index(row=sourceIndex.row(), column=0)
            if sourceIndex.isValid()
            else QtCore.QModelIndex()
        )

    def columnCount(
            self,
            parent: Optional[
                Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
            ] = None
    ) -> int:
        return 1

    def index(
            self,
            row: int,
            column: int = 0,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = QtCore.QModelIndex()
    ) -> QtCore.QModelIndex:
        if parent.isValid():
            return QtCore.QModelIndex()
        return self.createIndex(row, column)

    def mapToSource(
            self,
            proxyIndex: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]
    ) -> QtCore.QModelIndex:
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
                parent=base_index
            )

    @overload
    def parent(self) -> QtCore.QObject:
        ...

    @overload
    def parent(
            self,
            index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.QModelIndex:
        ...

    def parent(
            self,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex,
                None
            ] = None
    ) -> Union[QtCore.QModelIndex, QtCore.QObject]:
        return QtCore.QObject() if index is None else QtCore.QModelIndex()

    def get_tab_index(self) -> QtCore.QModelIndex:
        if self.source_tab is None:
            raise RuntimeError('source model not set')
        return self.get_source_tab_index(self.source_tab)


class ToolOptionsModel4(QtCore.QAbstractListModel):
    """Tool Model Options."""

    JsonDataRole = cast(int, QtCore.Qt.ItemDataRole.UserRole) + 1
    DataRole = JsonDataRole + 1

    def __init__(
            self,
            data: Optional[List[AbsOutputOptionDataType]] = None,
            parent: Optional[QtCore.QObject] = None
    ) -> None:
        """Create a new ToolOptionsModel4 object."""
        super().__init__(parent)
        self._data = data or []

    def __setitem__(
            self,
            key: str,
            value: Optional[Union[str, int, bool]]
    ) -> None:
        """Set the [key] operator.

        This allows for looking up the data based on the key.
        """
        if self._data is None:
            raise IndexError("No data")

        for item in self._data:
            if item.label == key:
                item.value = value
                break
        else:
            raise KeyError(f"Key not found: {key}")

    def flags(
            self,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]) -> QtCore.Qt.ItemFlag:
        """Get Qt Widget item flags used for an index."""
        return QtCore.Qt.ItemFlag.ItemIsSelectable | \
            QtCore.Qt.ItemFlag.ItemIsEnabled | \
            QtCore.Qt.ItemFlag.ItemIsEditable

    def rowCount(
            self,
            parent: Optional[
                Union[
                    QtCore.QModelIndex,
                    QtCore.QPersistentModelIndex
                ]
            ] = None
    ) -> int:
        """Get the amount of entries in the model."""
        return len(self._data)

    def headerData(
            self,
            section: int,
            orientation: QtCore.Qt.Orientation,
            role: int = cast(int, QtCore.Qt.ItemDataRole.DisplayRole)
    ) -> Any:
        """Get model header data."""
        if orientation == QtCore.Qt.Orientation.Vertical and \
                role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._data[section].label
        return None

    def data(
            self,
            index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
            role: int = typing.cast(int, QtCore.Qt.ItemDataRole.DisplayRole)
    ) -> Optional[Any]:
        """Get data from model."""
        if not index.isValid():
            return None

        formatter = ModelDataFormatter(self)
        return formatter.format(
            setting=self._data[index.row()],
            role=typing.cast(QtCore.Qt.ItemDataRole, role)
        )

    def setData(
            self,
            index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
            value: Optional[Any],
            role: int = typing.cast(int, QtCore.Qt.ItemDataRole.EditRole)
    ) -> bool:
        """Set model data.

        Returns:
            True if successful
        """
        if value is None:
            return False

        if role == typing.cast(int, QtCore.Qt.ItemDataRole.EditRole):
            self._data[index.row()].value = value
            self.dataChanged.emit(index, index, [role])  # type: ignore
            return True
        return super().setData(index, value, role)

    def serialize(self) -> Dict[str, UserDataType]:
        """Serialize model data to a dictionary."""
        return {data.label: data.value for data in self._data}

    def get(self) -> Dict[str, UserDataType]:
        """Access the key value settings for all options."""
        return self.serialize()


def check_required_settings_have_values(
        option_data: AbsOutputOptionDataType
) -> Optional[str]:
    if option_data.required is False:
        return None
    if option_data.value is None or option_data.value == "":
        return f"Required setting '{option_data.label}' is missing value"
    return None


class ModelDataFormatter:
    def __init__(self, model: ToolOptionsModel4):
        self._model = model

    @classmethod
    def _select_display_role(
            cls,
            item: AbsOutputOptionDataType
    ) -> Optional[SettingsDataType]:
        if cls._should_use_placeholder_text(item) is True:
            return item.placeholder_text
        if isinstance(item.value, bool):
            return item.value
        if item.value is None:
            return item.value
        return item.value

    @staticmethod
    def _should_use_placeholder_text(
            item: AbsOutputOptionDataType
    ) -> bool:
        if item.value is not None:
            return False
        if item.placeholder_text is None:
            return False
        return True

    def font_role(
            self,
            setting: AbsOutputOptionDataType
    ) -> Optional[QtGui.QFont]:
        if self._should_use_placeholder_text(setting) is True:
            font = QtGui.QFont()
            font.setItalic(True)
            return font
        return None

    def display_role(
            self,
            setting: AbsOutputOptionDataType
    ) -> Optional[SettingsDataType]:
        return self._select_display_role(setting)

    def format(
            self,
            setting: AbsOutputOptionDataType,
            role: QtCore.Qt.ItemDataRole
    ) -> Optional[Any]:
        formatter = {
            QtCore.Qt.ItemDataRole.DisplayRole: self.display_role,
            QtCore.Qt.ItemDataRole.EditRole: lambda setting_: setting_.value,
            QtCore.Qt.ItemDataRole.FontRole: self.font_role,
            self._model.JsonDataRole:
                lambda setting_: setting_.build_json_data(),
            self._model.DataRole: lambda setting_: setting_
        }.get(role)

        if formatter is not None:
            return formatter(setting)

        return None


class SettingsModel(QtCore.QAbstractTableModel):
    """Settings Qt table model."""

    columns: Final[int] = 2

    def __init__(self, *__args) -> None:
        """Create a new settings Qt model."""
        super().__init__(*__args)
        self._unmodified_data: List[Tuple[str, str]] = []
        self._data: List[Tuple[str, str]] = []
        self._headers = {0: "Key", 1: "Value"}
        self.data_modified = False
        self.dataChanged.connect(self._update_modified)

    def _update_modified(self) -> None:
        for original, current in zip(self._unmodified_data, self._data):
            if original[1] != current[1]:
                self.data_modified = True
                return
        self.data_modified = False

    def data(
            self,
            index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
            role: Optional[QtConstant] = None
    ) -> Optional[Union[str, QtCore.QObject]]:
        """Get role data from an index."""
        if not index.isValid():
            return None

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._data[index.row()][index.column()]

        if role == QtCore.Qt.ItemDataRole.EditRole:
            return self._data[index.row()][index.column()]

        return None

    def rowCount(
            self,
            parent: Optional[
                Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
            ] = None
    ) -> int:
        """Return the number of settings loaded in the model."""
        return len(self._data)

    def add_setting(self, name: str, value: str) -> None:
        """Add setting key value to the settings."""
        self._data.append((name, value))
        self._unmodified_data.append((name, value))

    def columnCount(
            self,
            parent: Optional[
                Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
            ] = None
    ) -> int:
        """Return number of columns.

        One for the heading and one for the content.
        """
        return self.columns

    def headerData(
            self,
            index: int,
            orientation: QtCore.Qt.Orientation,
            role: Optional[QtConstant] = None
    ) -> Optional[Union[str, QtCore.QObject]]:
        """Get header data from settings."""
        if orientation == QtCore.Qt.Orientation.Horizontal and \
                role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._headers.get(index, "")
        return None

    def flags(
            self,
            index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.Qt.ItemFlag:
        """Manage display flags for a given index."""
        if self._headers.get(index.column(), "") == "Key":
            return cast(QtCore.Qt.ItemFlag, QtCore.Qt.ItemFlag.NoItemFlags)

        if self._headers.get(index.column(), "") == "Value":
            return cast(
                QtCore.Qt.ItemFlag,
                QtCore.Qt.ItemFlag.ItemIsEnabled |
                QtCore.Qt.ItemFlag.ItemIsEditable
            )

        return super().flags(index)

    def setData(
            self,
            index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
            data: Any,
            role: Optional[QtConstant] = None
    ) -> bool:
        """Set data in model."""
        if not index.isValid():
            return False
        row = index.row()
        original_data = self._data[row]

        # Only update the model if the data is actually different
        if data != original_data[1]:
            self._data[row] = (self._data[row][0], data)

            # pylint: disable=no-member
            self.dataChanged.emit(  # type: ignore
                index,
                index,
                [QtCore.Qt.ItemDataRole.EditRole]
            )

            return True
        return False


def build_setting_qt_model(config_file: str) -> SettingsModel:
    """Read a configuration file and generate a SettingsModel."""
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"No existing Configuration in ${config_file}")

    config = configparser.ConfigParser()
    config.read(config_file)
    global_settings = config["GLOBAL"]
    my_model = SettingsModel()
    for key, value in global_settings.items():
        my_model.add_setting(key, value)
    return my_model


def unpack_global_settings_model(model: QAbstractItemModel) -> SettingsData:
    global_data: SettingsData = {}

    for i in range(model.rowCount()):
        key: str = model.index(i, 0).data()
        value: SettingsDataType = model.index(i, 1).data()
        global_data[key] = value
    return global_data


@dataclass
class PluginModelItem:
    entrypoint: metadata.EntryPoint
    enabled: bool


class PluginActivationModel(QtCore.QAbstractListModel):
    ModuleRole = cast(int, QtCore.Qt.ItemDataRole.UserRole) + 1

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.data_modified = False
        self._starting_data: List[PluginModelItem] = []
        self._data: List[PluginModelItem] = []
        self.dataChanged.connect(self._update_modified)

    def _update_modified(self) -> None:
        for original, current in zip(self._starting_data, self._data):
            if original.enabled != current.enabled:
                self.data_modified = True
                return
        self.data_modified = False

    def rowCount(
            self,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex,
                None
            ] = None
    ) -> int:
        return len(self._data)

    def add_entry_point(
            self,
            entry_point: metadata.EntryPoint,
            enabled: bool = False
    ) -> None:
        self._starting_data.append(PluginModelItem(entry_point, enabled))
        self._data.append(PluginModelItem(entry_point, enabled))

    def flags(
        self, index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.Qt.ItemFlag:
        if index.isValid():
            return (
                QtCore.Qt.ItemFlag.ItemIsUserCheckable
                | QtCore.Qt.ItemFlag.ItemIsSelectable
                | QtCore.Qt.ItemFlag.ItemIsEnabled
            )
        return super().flags(index)

    def data(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:

        if role == QtCore.Qt.ItemDataRole.CheckStateRole:

            return (
                QtCore.Qt.CheckState.Checked
                if self._data[index.row()].enabled
                else QtCore.Qt.CheckState.Unchecked
            )

        if role == self.ModuleRole:
            return self._data[index.row()].entrypoint.module

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._data[index.row()].entrypoint.name
        return None

    def setData(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        value: Any,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        if role == QtCore.Qt.ItemDataRole.CheckStateRole:
            self._data[index.row()].enabled = (
                value == QtCore.Qt.CheckState.Checked.value
            )
            self.dataChanged.emit(index, index, (role,))
            return True

        return super().setData(index, value, role)


class TabStandardItem(QtGui.QStandardItem):

    def __init__(
            self,
            name: Optional[str] = None,
            workflows: Optional[List[Type[Workflow]]] = None
    ) -> None:
        super().__init__()
        if name:
            self.setText(name)
        self._unmodified_workflows: List[WorkflowItem] = []
        self.reset_modified()
        for workflow in (workflows or []):
            self.append_workflow(workflow)

    @property
    def workflows(self) -> list[WorkflowItem]:
        return [
            cast(WorkflowItem, self.child(row_id, 0))
            for row_id in range(self.rowCount())
        ]

    @property
    def data_modified(self) -> bool:
        if len(self.workflows) != len(self._unmodified_workflows):
            return True

        return any(
            current.workflow != unmodified.workflow
            for current, unmodified in zip(
                self.workflows, self._unmodified_workflows
            )
        )

    def reset_modified(self) -> None:
        self._unmodified_workflows = self.workflows.copy()

    @property
    def name(self) -> str:
        return self.text()

    def append_workflow(self, workflow: Type[Workflow]) -> None:
        if workflow not in self:
            self.appendRow(WorkflowItem(workflow))
            self.emitDataChanged()

    def __contains__(self, workflow: Type[Workflow]) -> bool:
        for row_id in range(self.rowCount()):
            item = cast(WorkflowItem, self.child(row_id, 0))
            if item.workflow == workflow:
                return True
        return False

    def remove_workflow(self, workflow: Type[Workflow]) -> None:
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


class WorkflowItem(QtGui.QStandardItem):

    def __init__(self, workflow: Optional[Type[Workflow]]) -> None:
        super().__init__()
        self.workflow = workflow
        if workflow is not None and workflow.name is not None:
            self.setText(workflow.name)

    def columnCount(self) -> int:
        return 2

    @property
    def name(self) -> Optional[str]:
        return None if self.workflow is None else self.workflow.name


class TabsTreeModel(QtCore.QAbstractItemModel):
    WorkflowClassRole = cast(int, QtCore.Qt.ItemDataRole.UserRole) + 1

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.root_item = QtGui.QStandardItem()
        self._starting_rows = self.rowCount()

    def append_workflow_tab(
            self,
            name: str,
            workflows: Optional[List[Type[Workflow]]] = None
    ) -> None:
        new_tab = TabStandardItem(name, workflows or [])
        self.root_item.appendRow(new_tab)
        self.modelReset.emit()

    @property
    def data_modified(self) -> bool:
        if self._starting_rows != self.rowCount():
            return True
        return any(tab.data_modified for tab in self.tabs)

    @property
    def tabs(self) -> Iterator[TabStandardItem]:
        for row_id in range(self.rowCount()):
            yield cast(TabStandardItem, self.get_item(self.index(row_id, 0)))

    def columnCount(
            self, parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = QtCore.QModelIndex()
    ) -> int:
        return 2

    def rowCount(
            self,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = QtCore.QModelIndex()
    ) -> int:
        if parent.isValid() and parent.column() > 2:
            return 0
        parent_item = self.get_item(parent)
        return parent_item.rowCount() if parent_item else 0

    def index(
            self,
            row: int,
            column: int = 0,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = QtCore.QModelIndex()
    ) -> QtCore.QModelIndex:

        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        if parent.isValid() and parent.column() != 0:
            return QtCore.QModelIndex()
        parent_item = self.get_item(parent)
        if not parent_item:
            return QtCore.QModelIndex()
        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        return QtCore.QModelIndex()

    @overload
    def parent(self) -> QtCore.QObject:
        ...

    @overload
    def parent(
            self,
            child: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.QModelIndex:
        ...

    def parent(
            self,
            child: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex,
            ] = QtCore.QModelIndex()
    ) -> Union[QtCore.QModelIndex, QtCore.QObject]:
        if not child.isValid():
            return QtCore.QModelIndex()
        child_item = self.get_item(child)
        parent_item = child_item.parent()
        if parent_item == self.root_item or not parent_item:
            return QtCore.QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    @staticmethod
    def get_workflow_item_data(
            item: WorkflowItem,
            column: int,
            role: int
    ) -> Any:
        if role == QtGui.Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return str(item.name or "")
            if column == 1:
                return "" if item.workflow is None \
                    else str(item.workflow.description or "")
        return (
            item.workflow if role == TabsTreeModel.WorkflowClassRole
            else None
        )

    def data(
            self,
            index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
            role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> Any:
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
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = QtCore.QModelIndex()
    ) -> Union[QtGui.QStandardItem, TabStandardItem, WorkflowItem]:
        if index.isValid():
            item = index.internalPointer()
            if item:
                return cast(TabStandardItem, item)
        return self.root_item

    def headerData(self, section: int,
                   orientation: QtCore.Qt.Orientation,
                   role: int = QtGui.Qt.ItemDataRole.DisplayRole) -> Any:

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
        for i in range(self.rowCount()):
            index = self.index(i, 0)
            if self.data(index) == tab_name:
                return cast(TabStandardItem, self.get_item(index))
        return None

    def append_workflow_to_tab(
            self,
            tab_name: str,
            workflow: Type[Workflow]
    ) -> None:
        tab = self.get_tab(tab_name)
        if tab is None:
            raise ValueError(f"No tab named {tab_name}")
        tab.append_workflow(workflow)

    @property
    def tab_names(self) -> List[str]:
        return [
            self.data(self.index(i, 0)) for i in range(self.rowCount())
        ]

    def removeRow(
            self,
            row: int,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = QtCore.QModelIndex()) -> bool:
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
        self._starting_rows = self.rowCount()
        for tab in self.tabs:
            tab.reset_modified()
        self.dataChanged.emit(self.root_item.index(), [])

    def tab_information(self) -> List[CustomTabData]:
        return [
            CustomTabData(
                tab.name,
                [work.name or "" for work in tab.workflows]
            ) for tab in self.tabs
        ]

    def __len__(self) -> int:
        return self.rowCount()

    def __getitem__(self, item: int) -> TabStandardItem:
        for i, tab in enumerate(self.tabs):
            if i == item:
                return tab
        raise IndexError(f'{item} not found in model.')

    def clear(self) -> None:
        for row_id in range(self.rowCount()):
            self.removeRow(row_id)

    def setData(
            self,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ],
            value: Any,
            role: int = QtGui.Qt.ItemDataRole.DisplayRole
    ) -> bool:
        if role == TabsTreeModel.WorkflowClassRole:
            cast(WorkflowItem,  self.get_item(index)).workflow = value
            return True
        return super().setData(index, value, role)


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
            data_load_strategy: AbsTabsConfigDataManagement
    ) -> Dict[str, List[Type[Workflow]]]:
        all_workflows = speedwagon.job.available_workflows()

        sorted_workflows = \
            sorted(list(all_workflows.values()), key=lambda item: item.name)

        workflow_tabs_data: Dict[str, List[Type[Workflow]]] = {
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
            data_load_strategy=speedwagon.config.CustomTabsYamlConfig(
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
        config_strategy = speedwagon.config.StandardConfigFileLocator()
        self.yml_file = config_strategy.get_tabs_file()


class AbsWorkflowItemData(abc.ABC):
    def data(
            self,
            workflow: Type[speedwagon.Workflow],
            role: Union[int, QtCore.Qt.ItemDataRole]
    ) -> Any:
        """Get the data from workflow"""


class WorkflowItemData(AbsWorkflowItemData):
    def data(
            self,
            workflow: Type[speedwagon.Workflow],
            role: Union[int, QtCore.Qt.ItemDataRole]
    ) -> Any:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return workflow.name
        if role == TabsTreeModel.WorkflowClassRole:
            return workflow
        return None


class WorkflowList(AbsWorkflowList):

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._workflows: List[Type[Workflow]] = []
        self.data_strategy: AbsWorkflowItemData = WorkflowItemData()

    def rowCount(
            self,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = QtCore.QModelIndex()) -> int:
        return len(self._workflows)

    def add_workflow(self, workflow: Type[Workflow]) -> None:
        self._workflows.append(workflow)
        self.dataChanged.emit(len(self._workflows), len(self._workflows), 0)

    def data(
            self,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ],
            role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:
        return (
            self.data_strategy.data(self._workflows[index.row()], role)
            if index.isValid() else None
        )

    def insertRow(
            self,
            row: int,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = QtCore.QModelIndex()) -> bool:
        self._workflows.insert(row, speedwagon.job.NullWorkflow)
        return super().insertRow(row, parent)

    def removeRow(
            self,
            row: int,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = QtCore.QModelIndex()) -> bool:
        if row > len(self._workflows):
            return False
        self._workflows.pop(row)
        return True

    def setData(
            self,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ],
            value: Any,
            role: int = QtCore.Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False
        if role in [
            QtCore.Qt.ItemDataRole.EditRole,
            TabsTreeModel.WorkflowClassRole,
        ]:
            self._workflows[index.row()] = value
            return True
        return super().setData(index, value, role)
