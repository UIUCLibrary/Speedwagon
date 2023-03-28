"""Data models for displaying data to user in the user interface."""
from __future__ import annotations
import abc
from collections import namedtuple
import configparser
import enum
import os

import typing
from typing import Type, Dict, List, Any, Union, Tuple, Optional, cast

try:
    from typing import Final
except ImportError:  # pragma: no cover
    from typing_extensions import Final  # type: ignore
from dataclasses import dataclass
import sys


from PySide6.QtCore import QAbstractItemModel
from PySide6 import QtCore, QtGui  # type: ignore

if typing.TYPE_CHECKING:
    from speedwagon.frontend.qtwidgets import tabs
    from speedwagon.job import Workflow
    from speedwagon.workflow import AbsOutputOptionDataType, UserDataType
    from speedwagon.config import SettingsDataType, SettingsData
if sys.version_info < (3, 10):  # pragma: no cover
    import importlib_metadata as metadata
else:  # pragma: no cover
    from importlib import metadata


__all__ = [
    "WorkflowListModel2",
    "ToolOptionsModel4",
    "SettingsModel",
    "TabsModel"
]

QtConstant = int

# Qt has non-pythonic method names
# pylint: disable=invalid-name, unused-argument


class JobModelData(enum.Enum):
    NAME = 0
    DESCRIPTION = 1


OptionPair = namedtuple("OptionPair", ("label", "data"))


class WorkflowListModel2(QtCore.QAbstractListModel):
    """Workflow Qt list model."""

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        """Create a new WorkflowListModel2 qt list model."""
        super().__init__(parent)
        self._unmodified_data: List[Type[Workflow]] = []
        self.workflows: List[Type[Workflow]] = []

    @property
    def data_modified(self) -> bool:
        """Get if the data has been modified since originally added."""
        if len(self.workflows) != len(self._unmodified_data):
            return True
        for original, current in zip(self._unmodified_data, self.workflows):
            if original.name != current.name:
                return True
        return False

    def __iadd__(self, other: Type["Workflow"]) -> "WorkflowListModel2":
        """Add a workflow to the model."""
        self.add_workflow(other)
        return self

    def __isub__(self, other: Type["Workflow"]) -> "WorkflowListModel2":
        """Remove a workflow from the model."""
        self.remove_workflow(other)
        return self

    def rowCount(
            self,
            *args,
            parent: Optional[
                Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
            ] = None,
            **kwargs
    ) -> int:
        """Get the number of workflows loaded in the model."""
        return len(self.workflows)

    def data(
            self,
            index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
            role: Optional[QtConstant] = None
    ) -> Optional[Union[str, Type[Workflow], QtCore.QObject]]:
        """Get data at specific index."""
        if not index.isValid():
            return None
        row = index.row()

        if role is None:
            return None
        workflow: Dict[QtCore.Qt.ItemDataRole,
                       Optional[Union[str,
                                      Type[Workflow],
                                      QtCore.QObject]]] = {
            QtCore.Qt.ItemDataRole.DisplayRole: self.workflows[row].name,
            QtCore.Qt.ItemDataRole.UserRole: self.workflows[row],
        }
        value = workflow.get(typing.cast(QtCore.Qt.ItemDataRole, role))
        if value is not None:
            return value
        return None

    def sort(self, key=None, order=None) -> None:
        """Sort workflows.

        Defaults alphabetically by title.
        """
        # pylint: disable=no-member
        self.layoutAboutToBeChanged.emit()  # type: ignore

        self.workflows.sort(key=key or (lambda i: i.name))
        self.layoutChanged.emit()  # type: ignore

    def reset_modified(self) -> None:
        """Reset if the data has been modified.

        Running this and the current data will appear to be unaltered.
        """
        self._unmodified_data = self.workflows.copy()

    def add_workflow(self, workflow: Type[Workflow]) -> None:
        """Add workflow to model."""
        for existing_workflow in self.workflows:
            if workflow.name == existing_workflow.name:
                break
        else:
            row = len(self.workflows)
            index = self.createIndex(row, 0)
            self.beginInsertRows(index, 0, self.rowCount())
            self.workflows.insert(row, workflow)

            # pylint: disable=no-member
            self.dataChanged.emit(  # type: ignore
                index,
                index,
                [QtCore.Qt.ItemDataRole.EditRole]
            )
            self.endInsertRows()

    def setData(self,
                index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
                workflow: Type[Workflow],
                role: Optional[QtConstant] = None) -> bool:
        """Get data at a given index."""
        if not index.isValid():
            return False

        if workflow not in self.workflows:
            return False

        row = index.row()

        if len(self.workflows) <= row:
            return False

        self.workflows[row] = workflow

        # pylint: disable=no-member
        self.dataChanged.emit(index, index, [role])  # type: ignore
        return True

    def remove_workflow(self, workflow: Type[Workflow]) -> None:
        """Remove workflow from the model."""
        if workflow in self.workflows:
            index = QtCore.QModelIndex()
            self.beginRemoveRows(index, 0, self.rowCount())
            self.workflows.remove(workflow)

            # pylint: disable=no-member
            self.dataChanged.emit(  # type: ignore
                index,
                index,
                [QtCore.Qt.ItemDataRole.EditRole]
            )
            self.endRemoveRows()

    @classmethod
    def init_from_data(
            cls,
            workflows: typing.Iterable[Type[Workflow]],
            parent: Optional[QtCore.QObject] = None
    ) -> "WorkflowListModel2":
        """Create a new WorkflowListModel2 from workflow data."""
        new_class = cls(parent)

        for workflow in workflows:
            row = len(new_class.workflows)
            index = new_class.createIndex(row, 0)
            new_class.beginInsertRows(index, 0, new_class.rowCount())
            new_class.workflows.insert(row, workflow)
            new_class._unmodified_data.insert(row, workflow)
            # pylint: disable=no-member
            new_class.endInsertRows()
            # new_class.add_workflow(workflow)
        return new_class


class ToolOptionsModel(QtCore.QAbstractTableModel):
    """Tool options Qt table model."""

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        """Create a new ToolOptionsModel qt table model."""
        super().__init__(parent)
        self._data: List[Any] = []

    def rowCount(
            self,
            parent: Optional[
                Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
            ] = None
    ) -> int:
        return len(self._data)

    def columnCount(
            self,
            parent: Optional[
                Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
            ] = None
    ) -> int:
        if len(self._data) > 0:
            return 1
        return 0

    @abc.abstractmethod
    def get(self):
        raise NotImplementedError

    def flags(
            self,
            index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ):
        """Get flags for a given index."""
        if not index.isValid():
            return QtCore.Qt.ItemFlag.ItemIsEnabled

        column = index.column()

        if column == 0:
            return QtCore.Qt.ItemFlag.ItemIsEnabled \
                   | QtCore.Qt.ItemFlag.ItemIsSelectable \
                   | QtCore.Qt.ItemFlag.ItemIsEditable
        print(column, file=sys.stderr)
        return QtCore.Qt.ItemFlag.NoItemFlags


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


def get_settings_errors(
        model: ToolOptionsModel4,
        checks: List[typing.Callable[[AbsOutputOptionDataType], Optional[str]]]
) -> List[str]:
    errors = []
    for row_id in range(model.rowCount()):
        index = model.index(row_id)
        data = model.data(index, model.DataRole)
        for check_func in checks:
            error_check_result = check_func(data)
            if error_check_result is not None:
                errors.append(error_check_result)
    return errors


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


class TabsModel(QtCore.QAbstractListModel):
    """Tabs Qt list Model."""

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        """Create a new tab qt list model."""
        super().__init__(parent)
        self._unmodified_data: List[tabs.TabData] = []
        self.tabs: List[tabs.TabData] = []

    def reset_modified(self) -> None:
        """Reset if the data has been modified.

        Running this and the current data will appear to be unaltered.
        """
        self._unmodified_data = self.tabs.copy()
        index = self.index(0, 0)
        self.dataChanged.emit(  # type: ignore
            index,
            index,
            [QtCore.Qt.ItemDataRole.DisplayRole]
        )

    @property
    def data_modified(self) -> bool:
        """Get if the data has been modified since originally added."""
        if len(self._unmodified_data) != len(self.tabs):
            return True
        for original, current in zip(self._unmodified_data, self.tabs):
            if original[1] != current[1]:
                return True
        return False

    def __contains__(self, value: str) -> bool:
        """Check if a tab is in the model."""
        return any(tab.tab_name == value for tab in self.tabs)

    def __iadd__(self, other: tabs.TabData) -> "TabsModel":
        """Add a tab to the model."""
        self.add_tab(other)
        return self

    def __isub__(self, other: tabs.TabData) -> "TabsModel":
        """Remove a tab from the model."""
        self.remove_tab(other)
        return self

    def data(self,
             index: Union[
                 QtCore.QModelIndex,
                 QtCore.QPersistentModelIndex
             ],
             role: Optional[QtConstant] = None
             ) -> Optional[Union[str, tabs.TabData]]:
        """Get data about a tab for an index."""
        if not index.isValid():
            return None

        row = index.row()
        if row > len(self.tabs):
            return None

        if role is not None:
            workflow: Dict[QtCore.Qt.ItemDataRole, Any] = {
                QtCore.Qt.ItemDataRole.DisplayRole: self.tabs[row].tab_name,
                QtCore.Qt.ItemDataRole.UserRole: self.tabs[row]
            }
            return workflow.get(typing.cast(QtCore.Qt.ItemDataRole, role))
        return None

    def rowCount(
            self,
            parent: typing.Optional[
                Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
            ] = None
    ) -> int:
        """Get the number of tabs loaded in the model."""
        return len(self.tabs)

    def add_tab(self, tab: tabs.TabData) -> None:
        """Add a new tab to the model."""
        row = len(self.tabs)
        index = self.createIndex(row, 0)
        self.beginInsertRows(index, 0, self.rowCount())
        self.tabs.insert(row, tab)
        tab.workflows_model.dataChanged.connect(
            lambda source_index=index: self.dataChanged.emit(
                source_index, source_index, [QtCore.Qt.ItemDataRole.EditRole])
        )
        # pylint: disable=no-member
        self.dataChanged.emit(  # type: ignore
            index,
            index,
            [QtCore.Qt.ItemDataRole.EditRole]
        )
        self.endInsertRows()

    def remove_tab(self, tab: tabs.TabData) -> None:
        """Remove a tab from the model."""
        index = QtCore.QModelIndex()
        if tab in self.tabs:
            self.beginRemoveRows(index, 0, self.rowCount())
            self.tabs.remove(tab)

            # pylint: disable=no-member
            self.dataChanged.emit(  # type: ignore
                index,
                index,
                [QtCore.Qt.ItemDataRole.EditRole]
            )
            self.endRemoveRows()

    def setData(
            self,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ],
            tab: tabs.TabData,
            role: Optional[QtConstant] = None
    ) -> bool:
        """Set tab data."""
        if not index.isValid():
            return False

        if tabs in self.tabs:
            return False

        row = index.row()
        if len(self.tabs) <= row:
            return False

        self.tabs[row] = tab

        # pylint: disable=no-member
        self.dataChanged.emit(index, index, [role])  # type: ignore
        return True


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
