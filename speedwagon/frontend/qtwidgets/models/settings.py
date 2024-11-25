"""Settings model code."""

from __future__ import annotations

import abc
import configparser
import os

import typing
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
    TYPE_CHECKING
)

try:
    from typing import Final
except ImportError:  # pragma: no cover
    from typing_extensions import Final  # type: ignore

from PySide6 import QtCore
from speedwagon.config import SettingsData, SettingsDataType

if TYPE_CHECKING:
    import speedwagon.job

WorkflowsSettings = Dict[str, SettingsData]
WorkflowDataType = List[Union[str, int, bool, None]]
__all__ = ["SettingsModel"]

QtConstant = int

DEFAULT_QMODEL_INDEX = QtCore.QModelIndex()


class SettingsModel(QtCore.QAbstractTableModel):
    """Settings Qt table model."""

    COLUMNS: Final[int] = 2

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
        role: Optional[QtConstant] = None,
    ) -> Optional[Union[str, QtCore.QObject]]:
        """Get role data from an index."""
        if not index.isValid():
            return None

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._data[index.row()][index.column()]

        if role == QtCore.Qt.ItemDataRole.EditRole:
            return self._data[index.row()][index.column()]

        return None

    def rowCount(  # pylint: disable=invalid-name
        self,
        parent: Optional[  # pylint: disable=unused-argument
            Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ] = None,
    ) -> int:
        """Return the number of settings loaded in the model."""
        return len(self._data)

    def add_setting(self, name: str, value: str) -> None:
        """Add setting key value to the settings."""
        self._data.append((name, value))
        self._unmodified_data.append((name, value))

    def columnCount(  # pylint: disable=invalid-name
        self,
        parent: Optional[  # pylint: disable=unused-argument
            Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ] = None,
    ) -> int:
        """Return number of columns.

        One for the heading and one for the content.
        """
        return self.COLUMNS

    def headerData(  # pylint: disable=invalid-name
        self,
        index: int,
        orientation: QtCore.Qt.Orientation,
        role: Optional[QtConstant] = None,
    ) -> Optional[Union[str, QtCore.QObject]]:
        """Get header data from settings."""
        if (
            orientation == QtCore.Qt.Orientation.Horizontal
            and role == QtCore.Qt.ItemDataRole.DisplayRole
        ):
            return self._headers.get(index, "")
        return None

    def flags(
        self, index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.Qt.ItemFlag:
        """Manage display flags for a given index."""
        if self._headers.get(index.column(), "") == "Key":
            return QtCore.Qt.ItemFlag.NoItemFlags

        if self._headers.get(index.column(), "") == "Value":
            return (
                QtCore.Qt.ItemFlag.ItemIsEnabled
                | QtCore.Qt.ItemFlag.ItemIsEditable
            )

        return super().flags(index)

    def setData(  # pylint: disable=invalid-name
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        data: Any,
        role: Optional[QtConstant] = None,  # pylint: disable=W0613
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
                index, index, [QtCore.Qt.ItemDataRole.EditRole]
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


def unpack_global_settings_model(
    model: QtCore.QAbstractItemModel,
) -> SettingsData:
    global_data: SettingsData = {}

    for i in range(model.rowCount()):
        key: str = model.index(i, 0).data()
        value: SettingsDataType = model.index(i, 1).data()
        global_data[key] = value
    return global_data


class AbsWorkflowSettingItem(abc.ABC):
    @abc.abstractmethod
    def column_count(self) -> int:
        """Column Count."""

    @abc.abstractmethod
    def parent(self) -> Optional["AbsWorkflowSettingItem"]:
        """Get parent."""

    @abc.abstractmethod
    def child_number(self) -> int:
        """Get child number."""

    @abc.abstractmethod
    def child_count(self) -> int:
        """Get child count."""

    @abc.abstractmethod
    def child(self, number: int) -> Optional["AbsWorkflowSettingItem"]:
        """Get Child."""

    @abc.abstractmethod
    def flags(
        self, index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.Qt.ItemFlag:
        """Get flags."""

    def set_data(
        self,
        _: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        __: Union[str, bool, int, None],
        ___: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        return False


class WorkflowSettingsItemWorkflow(AbsWorkflowSettingItem):
    def __init__(
        self,
        workflow: Optional[speedwagon.job.Workflow] = None,
        parent: Optional[WorkflowSettingsRoot] = None,
    ) -> None:
        super().__init__()
        self._workflow = workflow
        self.parent_item = parent
        self.child_items: List[WorkflowSettingsMetadata] = []

    @property
    def workflow(self) -> Optional[speedwagon.job.Workflow]:
        return self._workflow

    @workflow.setter
    def workflow(self, value: speedwagon.job.Workflow) -> None:
        self._workflow = value
        options = value.workflow_options()
        for option in options:
            item = WorkflowSettingsMetadata(option, self)
            item.value = value.get_workflow_configuration_value(option.label)
            self.child_items.insert(0, item)

    def column_count(self) -> int:
        return 0 if self.workflow is None else 2

    def child(self, number: int) -> Optional[WorkflowSettingsMetadata]:
        if number < 0 or number >= len(self.child_items):
            return None
        return self.child_items[number]

    def child_count(self) -> int:
        return len(self.child_items)

    def data_column(
        self, column: int, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Union[str, bool, int, None]:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if column == 0:
                if self.workflow is not None:
                    return (
                        self.workflow.name
                        if self.workflow.name is not None
                        else ""
                    )
                return ""
            return None
        return None

    def last_child(self) -> Optional[WorkflowSettingsMetadata]:
        return self.child_items[-1] if self.child_items else None

    def parent(self) -> Optional[WorkflowSettingsRoot]:
        return self.parent_item

    def child_number(self) -> int:
        return (
            self.parent_item.child_items.index(self) if self.parent_item else 0
        )

    def remove_children(self, position: int, count: int) -> bool:
        if position < 0 or position + count > len(self.child_items):
            return False
        for _ in range(count):
            self.child_items.pop(position)
        return True

    def flags(
        self, index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.Qt.ItemFlag:
        return QtCore.Qt.ItemFlag.ItemIsEnabled


class EditSettingsDataRole:
    def __init__(self, parent: WorkflowSettingsMetadata):
        self.parent = parent
        self._role_methods: Dict[
            QtCore.Qt.ItemDataRole, Callable[[int], Any]
        ] = {
            QtCore.Qt.ItemDataRole.DisplayRole: self.display_role,
            QtCore.Qt.ItemDataRole.EditRole: self.edit_role,
        }

    def display_role(self, column: int) -> SettingsDataType:
        label = (
            self.parent.option.label if self.parent.option is not None else ""
        )
        return {0: label, 1: self.parent.value}.get(column)

    def edit_role(self, column: int) -> SettingsDataType:
        return {1: self.parent.value}.get(column)

    def data(
        self, column: int, role: QtCore.Qt.ItemDataRole
    ) -> SettingsDataType:
        method = self._role_methods.get(role)
        return None if method is None else method(column)


class WorkflowSettingsMetadata(AbsWorkflowSettingItem):
    def __init__(
        self,
        option: Optional[speedwagon.job.AbsOutputOptionDataType] = None,
        parent: Optional[WorkflowSettingsItemWorkflow] = None,
    ) -> None:
        super().__init__()
        self.value: Union[str, bool, int, None] = None
        self.data_strategy = EditSettingsDataRole(self)
        self.option: Optional[speedwagon.job.AbsOutputOptionDataType] = option
        self.parent_item = parent
        self.child_items: List[AbsWorkflowSettingItem] = []

    def column_count(self) -> int:
        return 2 if self.option else 0

    def child(self, number: int) -> Optional[AbsWorkflowSettingItem]:
        if number < 0 or number >= len(self.child_items):
            return None
        return self.child_items[number]

    def child_count(self) -> int:
        return len(self.child_items)

    @property
    def label(self) -> Optional[str]:
        return None if self.option is None else self.option.label

    def insert_children(self, _: int, __: int, ___: int) -> bool:
        return False

    # pylint: disable=unused-argument
    def set_data(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        value: Union[str, bool, int, None],
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        if index.column() == 1:
            self.value = value
            return True
        return False

    # pylint: enable=unused-argument

    def data_column(
        self, column: int, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> SettingsDataType:
        return self.data_strategy.data(column, QtCore.Qt.ItemDataRole(role))

    def flags(
        self, index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.Qt.ItemFlag:
        if index.column() == 1:
            return (
                QtCore.Qt.ItemFlag.ItemIsEnabled
                | QtCore.Qt.ItemFlag.ItemIsSelectable
                | QtCore.Qt.ItemFlag.ItemIsEditable
            )
        return (
            QtCore.Qt.ItemFlag.ItemIsEnabled
            | QtCore.Qt.ItemFlag.ItemIsSelectable
        )

    def last_child(self) -> Optional[AbsWorkflowSettingItem]:
        return self.child_items[-1] if self.child_items else None

    def parent(self) -> Optional[WorkflowSettingsItemWorkflow]:
        return self.parent_item

    def child_number(self) -> int:
        return (
            self.parent_item.child_items.index(self) if self.parent_item else 0
        )

    def remove_children(self, _: int, __: int) -> bool:
        return False


class WorkflowSettingsRoot(AbsWorkflowSettingItem):
    def __init__(
        self, parent: Optional["WorkflowSettingsRoot"] = None
    ) -> None:
        super().__init__()
        self.item_data: WorkflowDataType = ["Property", "Value"]
        self.workflow: Optional[speedwagon.job.Workflow] = None
        self.parent_item = parent
        self.child_items: List[WorkflowSettingsItemWorkflow] = []

    def column_count(self) -> int:
        return len(self.item_data)

    def child(self, number: int) -> Optional[WorkflowSettingsItemWorkflow]:
        if number < 0 or number >= len(self.child_items):
            return None
        return self.child_items[number]

    def child_count(self) -> int:
        return len(self.child_items)

    def insert_children(self, position: int, count: int, _: int) -> bool:
        if position < 0 or position > len(self.child_items):
            return False

        for _ in range(count):
            item = WorkflowSettingsItemWorkflow(None, self)
            self.child_items.insert(position, item)
        return True

    def data_column(
        self, column: int, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Union[str, bool, int, None]:
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if column < 0 or column >= len(self.item_data):
                return None
            return self.item_data[column]
        return None

    def flags(
        self, index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.Qt.ItemFlag:
        return QtCore.Qt.ItemFlag.NoItemFlags

    def data(self, column: int):
        if column < 0 or column >= len(self.item_data):
            return None
        return self.item_data[column]

    def last_child(self) -> Optional["WorkflowSettingsItemWorkflow"]:
        return self.child_items[-1] if self.child_items else None

    def parent(self) -> Optional[AbsWorkflowSettingItem]:
        return self.parent_item

    def child_number(self) -> int:
        return (
            typing.cast(
                List[AbsWorkflowSettingItem], self.parent_item.child_items
            ).index(self)
            if self.parent_item
            else 0
        )

    def remove_children(self, position: int, count: int) -> bool:
        if position < 0 or position + count > len(self.child_items):
            return False
        for _ in range(count):
            self.child_items.pop(position)
        return True


class WorkflowSettingsModel(QtCore.QAbstractItemModel):
    _headers: Dict[int, str] = {
        0: "Property",
        1: "Value",
    }

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.root_item = WorkflowSettingsRoot()
        self._unmodified_data = str(self.results())

    def columnCount(  # pylint: disable=invalid-name
        self,
        parent: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> int:
        if parent.isValid():
            item = self.get_item(parent)
            return item.column_count()
        return self.root_item.column_count()

    def flags(
        self, index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.Qt.ItemFlag:
        return (
            self.get_item(index).flags(index)
            if index.isValid()
            else QtCore.Qt.ItemFlag.NoItemFlags
        )

    def setData(  # pylint: disable=invalid-name
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        value: Any,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        if role != QtCore.Qt.ItemDataRole.EditRole:
            return False
        results = self.get_item(index).set_data(index, value, role)
        if results is True:
            self.dataChanged.emit(
                index,
                index,
                [
                    QtCore.Qt.ItemDataRole.EditRole,
                    QtCore.Qt.ItemDataRole.DisplayRole,
                ],
            )
        return results

    def headerData(  # pylint: disable=invalid-name
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if (
            orientation == QtCore.Qt.Orientation.Horizontal
            and role == QtCore.Qt.ItemDataRole.DisplayRole
        ):
            return self.root_item.data(section)
        if all(
            [
                orientation == QtCore.Qt.Orientation.Vertical,
                role == QtCore.Qt.ItemDataRole.DisplayRole,
                section < len(self.root_item.child_items),
            ]
        ):
            return section + 1
        return None

    def rowCount(  # pylint: disable=invalid-name
        self,
        parent: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> int:
        if parent.isValid() and parent.column() > 0:
            return 0
        parent_item = typing.cast(
            Optional[WorkflowSettingsRoot], self.get_item(parent)
        )

        if not parent_item:
            return 0
        return parent_item.child_count()

    def index(
        self,
        row: int,
        column: int = 0,
        parent: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = DEFAULT_QMODEL_INDEX,
    ) -> QtCore.QModelIndex:
        if parent.isValid() and parent.column() != 0:
            return QtCore.QModelIndex()
        parent_item = self.get_item(parent)
        if not parent_item:
            return QtCore.QModelIndex()
        child_item = parent_item.child(row)
        if child_item:
            if column >= child_item.column_count():
                return QtCore.QModelIndex()
            return self.createIndex(row, column, child_item)
        return QtCore.QModelIndex()

    def add_workflow(self, workflow: speedwagon.job.Workflow) -> None:
        self.root_item.insert_children(
            self.root_item.child_count(), 1, self.root_item.column_count()
        )
        workflow_item: Optional[
            WorkflowSettingsItemWorkflow
        ] = self.root_item.last_child()

        if workflow_item is None:
            return
        workflow_item.workflow = workflow

    def clear(self) -> None:
        self.root_item.remove_children(0, self.rowCount())

    def remove_workflow(self, workflow: speedwagon.job.Workflow) -> None:
        for i in range(self.root_item.child_count()):
            child_item = self.root_item.child(i)
            if child_item is None:
                continue
            if child_item.workflow == workflow:
                self.root_item.remove_children(i, 1)
                break
        else:
            raise ValueError(f"{workflow} not in")

    def data(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Union[str, bool, int, None]:
        if not index.isValid():
            return None
        item = typing.cast(WorkflowSettingsRoot, self.get_item(index))
        return item.data_column(index.column(), role)

    @typing.overload
    def parent(
        self, child: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.QModelIndex:
        ...

    @typing.overload
    def parent(self) -> QtCore.QObject:
        ...

    def parent(
        self,
        child: Union[
            QtCore.QModelIndex,
            QtCore.QPersistentModelIndex,
        ] = DEFAULT_QMODEL_INDEX,
    ) -> Union[QtCore.QModelIndex, QtCore.QObject]:
        if not child.isValid():
            return QtCore.QModelIndex()
        child_item = self.get_item(child)
        parent_item: Optional[AbsWorkflowSettingItem] = (
            child_item.parent() if child_item else None
        )
        if parent_item == self.root_item or not parent_item:
            return QtCore.QModelIndex()
        return self.createIndex(parent_item.child_number(), 0, parent_item)

    def get_item(
        self,
        index: Union[
            QtCore.QModelIndex,
            QtCore.QPersistentModelIndex,
        ] = DEFAULT_QMODEL_INDEX,
    ) -> AbsWorkflowSettingItem:
        if index.isValid():
            item = typing.cast(WorkflowSettingsRoot, index.internalPointer())
            if item:
                return item

        return self.root_item

    def results(self) -> WorkflowsSettings:
        results: WorkflowsSettings = {}
        for workflow_row_id in range(self.rowCount()):
            workflow_index = self.index(workflow_row_id, 0)
            item = typing.cast(
                WorkflowSettingsItemWorkflow, self.get_item(workflow_index)
            )
            if item.workflow is None:
                continue

            settings: SettingsData = {
                str(
                    self.data(self.index(row, 0, parent=workflow_index))
                ): self.data(self.index(row, 1, parent=workflow_index))
                for row in range(self.rowCount(parent=workflow_index))
            }
            workflow_name = (
                item.workflow.name if item.workflow.name is not None else ""
            )
            results[workflow_name] = settings
        return results

    def modified(self) -> bool:
        return str(self.results()) != self._unmodified_data

    def reset_modified(self) -> None:
        self._unmodified_data = str(self.results())

    @property
    def workflows(self) -> Iterable[WorkflowSettingsItemWorkflow]:
        return [
            typing.cast(
                WorkflowSettingsItemWorkflow, self.get_item(self.index(i, 0))
            )
            for i in range(self.rowCount())
        ]
