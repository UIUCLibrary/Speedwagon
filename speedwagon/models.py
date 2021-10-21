"""Data models for displaying data to user in the user interface."""

import sys
import typing
from typing import Type, Dict, List, Any, Union, Tuple, Optional, cast

try:
    from typing import Final
except ImportError:
    from typing_extensions import Final

import warnings
from abc import abstractmethod
from collections import namedtuple
import enum

from PyQt5 import QtCore  # type: ignore
from speedwagon import tabs, Workflow
from .job import AbsWorkflow
from .workflows import shared_custom_widgets

__all__ = [
    "ItemListModel",
    "WorkflowListModel",
    "WorkflowListModel2",
    "ToolOptionsPairsModel",
    "ToolOptionsModel3",
    "SettingsModel",
    "TabsModel"
]

QtConstant = int

# Qt has non-pythonic names for it's methods
# pylint: disable=invalid-name, unused-argument


class JobModelData(enum.Enum):
    NAME = 0
    DESCRIPTION = 1


class ItemListModel(QtCore.QAbstractTableModel):
    """List model for items."""

    def __init__(self, data: typing.Mapping[str, Type[Workflow]]) -> None:
        """Create a new ItemListModel qt list model for workflows."""
        super().__init__()
        self.jobs: List[Type[Workflow]] = list(data.values())

    def columnCount(self, *args, parent=QtCore.QModelIndex(), **kwargs) -> int:
        """Return 2.

        One for the label and one of the idem.
        """
        return 2

    def rowCount(self,
                 *args,
                 parent: QtCore.QModelIndex = None,
                 **kwargs) -> int:
        """Get the number of jobs in the model."""
        return len(self.jobs)

    @staticmethod
    def _extract_job_metadata(
            job: Type[AbsWorkflow],
            data_type: JobModelData
    ) -> Optional[str]:
        static_data_values: Dict[JobModelData, Optional[str]] = {
            JobModelData.NAME: job.name,
            JobModelData.DESCRIPTION: job.description
        }
        return static_data_values[data_type]


OptionPair = namedtuple("OptionPair", ("label", "data"))


class WorkflowListModel(ItemListModel):
    """Model for listing workflows."""

    def data(
            self,
            index: QtCore.QModelIndex,
            role: Optional[QtConstant] = None
    ) -> Union[str, Type[Workflow], QtCore.QSize, QtCore.QVariant]:
        """Get data at a specific index."""
        if index.isValid():
            data = self.jobs[index.row()]
            if role in [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole]:
                return self._extract_job_metadata(
                    job=data,
                    data_type=JobModelData(index.column())
                ) or QtCore.QVariant()

            if role == QtCore.Qt.UserRole:
                return self.jobs[index.row()]
            if role == QtCore.Qt.SizeHintRole:
                return QtCore.QSize(10, 20)

        return QtCore.QVariant()

    def sort(self, key=None, order=None):
        """Sort workflows.

        Defaults alphabetically by title.
        """
        self.layoutAboutToBeChanged.emit()

        self.jobs.sort(key=key or (lambda i: i.name))
        self.layoutChanged.emit()


class WorkflowListModel2(QtCore.QAbstractListModel):
    """Workflow Qt list model."""

    def __init__(self, parent: QtCore.QObject = None) -> None:
        """Create a new WorkflowListModel2 qt list model."""
        super().__init__(parent)
        self.workflows: List[Type[Workflow]] = []

    def __iadd__(self, other: Type["Workflow"]) -> "WorkflowListModel2":
        """Add a workflow to the model."""
        self.add_workflow(other)
        return self

    def __isub__(self, other: Type["Workflow"]) -> "WorkflowListModel2":
        """Remove a workflow from the model."""
        self.remove_workflow(other)
        return self

    def rowCount(self,
                 *args,
                 parent: QtCore.QModelIndex = None,
                 **kwargs) -> int:
        """Get the number of workflows loaded in the model."""
        return len(self.workflows)

    def data(
            self,
            index: QtCore.QModelIndex,
            role: Optional[QtConstant] = None
    ) -> Union[str, Type[Workflow], QtCore.QVariant]:
        """Get data at specific index."""
        if not index.isValid():
            return QtCore.QVariant()
        row = index.row()

        if role is None:
            return QtCore.QVariant()
        workflow: Dict[int, Optional[Union[str,
                                           Type[Workflow],
                                           QtCore.QVariant]]] = {
            QtCore.Qt.DisplayRole: self.workflows[row].name,
            QtCore.Qt.UserRole: self.workflows[row],
        }
        value = workflow.get(role)
        if value is not None:
            return value
        return QtCore.QVariant()

    def sort(self, key=None, order=None) -> None:
        """Sort workflows.

        Defaults alphabetically by title.
        """
        cast(QtCore.pyqtBoundSignal, self.layoutAboutToBeChanged).emit()

        self.workflows.sort(key=key or (lambda i: i.name))
        cast(QtCore.pyqtBoundSignal, self.layoutChanged).emit()

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
            self.dataChanged.emit(index, index, [QtCore.Qt.EditRole])
            self.endInsertRows()

    def setData(self,
                index: QtCore.QModelIndex,
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
        self.dataChanged.emit(index, index, [role])
        return True

    def remove_workflow(self, workflow: Type[Workflow]) -> None:
        """Remove workflow from the model."""
        if workflow in self.workflows:
            index = QtCore.QModelIndex()
            self.beginRemoveRows(index, 0, self.rowCount())
            self.workflows.remove(workflow)
            self.dataChanged.emit(index, index, [QtCore.Qt.EditRole])
            self.endRemoveRows()


class ToolOptionsModel(QtCore.QAbstractTableModel):
    """Tool options Qt table model."""

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        """Create a new ToolOptionsModel qt table model."""
        super().__init__(parent)
        self._data: List[Any] = []

    def rowCount(
            self,
            parent: typing.Optional[QtCore.QModelIndex] = None
    ) -> int:
        return len(self._data)

    def columnCount(
            self,
            parent: typing.Optional[QtCore.QModelIndex] = None
    ) -> int:
        if len(self._data) > 0:
            return 1
        return 0

    @abstractmethod
    def get(self):
        raise NotImplementedError

    def flags(self, index: QtCore.QModelIndex):
        """Get flags for a given index."""
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        column = index.column()

        if column == 0:
            return QtCore.Qt.ItemIsEnabled \
                   | QtCore.Qt.ItemIsSelectable \
                   | QtCore.Qt.ItemIsEditable
        print(column, file=sys.stderr)
        return QtCore.Qt.NoItemFlags


class ToolOptionsPairsModel(ToolOptionsModel):
    """Tool Options Pairs Qt table model.

    Warnings:
        This class is deprecated. Use ToolOptionsModel2 instead.
    """

    def __init__(self, data: Dict[str, str], parent=None) -> None:
        """Create a new ToolOptionsPairsModel model.

        Warnings:
            This is deprecated. Use ToolOptionsModel2 instead.
        """
        warnings.warn("Use ToolOptionsModel2 instead", DeprecationWarning)
        super().__init__(parent)
        for key, value in data.items():
            self._data.append(OptionPair(key, value))

    def data(self,
             index: QtCore.QModelIndex,
             role: Optional[QtConstant] = None):
        """Get data at a certain index."""
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return self._data[index.row()].data
            if role == QtCore.Qt.EditRole:
                return self._data[index.row()].data
        return QtCore.QVariant()

    def setData(
            self,
            index,
            data,
            role=None
    ) -> bool:
        """Set data at a certain index."""
        if not index.isValid():
            return False
        existing_data = self._data[index.row()]
        self._data[index.row()] = OptionPair(existing_data.label, data)
        return True

    def headerData(
            self,
            index: int,
            orientation: QtConstant,
            role: Optional[QtConstant] = None
    ) -> Union[str, QtCore.QVariant]:
        """Get header information."""
        if orientation == QtCore.Qt.Vertical \
                and role == QtCore.Qt.DisplayRole:
            title = self._data[index].label
            return str(title)
        return QtCore.QVariant()

    def get(self) -> dict:
        """Access all underlining data."""
        return {data.label: data.data for data in self._data}


def _lookup_constant(value: int) -> List[str]:
    res = []
    for m in [
        attr for attr in dir(QtCore.Qt)
        if not callable(getattr(QtCore.Qt, attr)) and not attr.startswith("_")
    ]:

        if getattr(QtCore.Qt, m) == value and "role" in m.lower():
            res.append(m)
    return res


class ToolOptionsModel3(ToolOptionsModel):
    """Model for tool options."""

    def __init__(
            self,
            data: List[shared_custom_widgets.UserOptionPythonDataType2],
            parent: QtCore.QObject = None
    ) -> None:
        """Create a new tool options Qt model."""
        if data is None:
            raise NotImplementedError
        super().__init__(parent)

        self._data: \
            List[shared_custom_widgets.UserOptionPythonDataType2] = data

    def data(
            self,
            index: QtCore.QModelIndex,
            role=QtCore.Qt.DisplayRole
    ) -> Union[QtCore.QVariant,
               QtCore.QSize,
               shared_custom_widgets.UserOption2,
               str]:
        """Get data at an index in the model."""
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                data = self._data[index.row()].data
                if data is not None:
                    return str(data)
                return ""
            if role == QtCore.Qt.EditRole:
                return self._data[index.row()].data
            if role == QtCore.Qt.UserRole:
                return self._data[index.row()]
            if role == QtCore.Qt.SizeHintRole:
                return QtCore.QSize(10, 25)

        return QtCore.QVariant()

    def get(self) -> Dict[str, Any]:
        """Access the key value settings for all options."""
        options: Dict[str, Any] = {}
        for data in self._data:
            options[data.label_text] = data.data
        return options

    def headerData(
            self,
            index: int,
            orientation: int,
            role: Optional[QtConstant] = None) -> Union[QtCore.QVariant, str]:
        """Get header data for a given index."""
        if orientation == QtCore.Qt.Vertical and \
                role == QtCore.Qt.DisplayRole:

            title = self._data[index].label_text
            return str(title)
        return QtCore.QVariant()

    def setData(
            self,
            index: QtCore.QModelIndex,
            data,
            role: Optional[QtConstant] = None
    ) -> bool:
        """Set tool option data in the model."""
        if not index.isValid():
            return False
        self._data[index.row()].data = data
        return True


class SettingsModel(QtCore.QAbstractTableModel):
    """Settings Qt table model."""

    columns: Final[int] = 2

    def __init__(self, *__args) -> None:
        """Create a new settings Qt model."""
        super().__init__(*__args)
        self._data: List[Tuple[str, str]] = []
        self._headers = {
            0: "Key",
            1: "Value"
        }

    def data(
            self,
            index: QtCore.QModelIndex,
            role: Optional[QtConstant] = None
    ) -> Union[str, QtCore.QVariant]:
        """Get role data from an index."""
        if not index.isValid():
            return QtCore.QVariant()

        if role == QtCore.Qt.DisplayRole:
            return self._data[index.row()][index.column()]

        if role == QtCore.Qt.EditRole:
            return self._data[index.row()][index.column()]

        return QtCore.QVariant()

    def rowCount(
            self,
            parent: typing.Optional[QtCore.QModelIndex] = None
    ) -> int:
        """Return the number of settings loaded in the model."""
        return len(self._data)

    def add_setting(self, name: str, value: str) -> None:
        """Add setting key value to the settings."""
        self._data.append((name, value))

    def columnCount(
            self,
            parent: typing.Optional[QtCore.QModelIndex] = None
    ) -> int:
        """Return number of columns.

        One for the heading and one for the content.
        """
        return self.columns

    def headerData(
            self,
            index: int,
            orientation: int,
            role: Optional[QtConstant] = None
    ) -> Union[str, QtCore.QVariant]:
        """Get header data from settings."""
        if orientation == QtCore.Qt.Horizontal and \
                role == QtCore.Qt.DisplayRole:
            return self._headers.get(index, "")
        return QtCore.QVariant()

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        """Manage display flags for a given index."""
        if self._headers.get(index.column(), "") == "Key":
            return cast(QtCore.Qt.ItemFlags, QtCore.Qt.NoItemFlags)

        if self._headers.get(index.column(), "") == "Value":
            return cast(QtCore.Qt.ItemFlags,
                        QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)

        return super().flags(index)

    def setData(
            self,
            index: QtCore.QModelIndex,
            data,
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
            self.dataChanged.emit(index, index, [QtCore.Qt.EditRole])

        return True


class TabsModel(QtCore.QAbstractListModel):
    """Tabs Qt list Model."""

    def __init__(self, parent: QtCore.QObject = None) -> None:
        """Create a new tab qt list model."""
        super().__init__(parent)
        self.tabs: List[tabs.TabData] = []

    def __contains__(self, value: str) -> bool:
        """Check if a tab is in the model."""
        return any(tab.tab_name == value for tab in self.tabs)

    def __iadd__(self, other: "tabs.TabData") -> "TabsModel":
        """Add a tab to the model."""
        self.add_tab(other)
        return self

    def __isub__(self, other: "tabs.TabData") -> "TabsModel":
        """Remove a tab from the model."""
        self.remove_tab(other)
        return self

    def data(self,
             index: QtCore.QModelIndex,
             role: Optional[QtConstant] = None
             ) -> Union[QtCore.QVariant, str, "tabs.TabData"]:
        """Get data about a tab for an index."""
        if not index.isValid():
            return QtCore.QVariant()

        row = index.row()
        if row > len(self.tabs):
            return QtCore.QVariant()

        if role is not None:
            workflow: Dict[int, Any] = {
                QtCore.Qt.DisplayRole: self.tabs[row].tab_name,
                QtCore.Qt.UserRole: self.tabs[row]
            }
            return workflow.get(role, QtCore.QVariant())
        return QtCore.QVariant()

    def rowCount(
            self,
            parent: typing.Optional[QtCore.QModelIndex] = None
    ) -> int:
        """Get the number of tabs loaded in the model."""
        return len(self.tabs)

    def add_tab(self, tab: "tabs.TabData") -> None:
        """Add a new tab to the model."""
        row = len(self.tabs)
        index = self.createIndex(row, 0)
        self.beginInsertRows(index, 0, self.rowCount())
        self.tabs.insert(row, tab)
        self.dataChanged.emit(index, index, [QtCore.Qt.EditRole])
        self.endInsertRows()

    def remove_tab(self, tab: "tabs.TabData") -> None:
        """Remove a tab from the model."""
        index = QtCore.QModelIndex()
        if tab in self.tabs:
            self.beginRemoveRows(index, 0, self.rowCount())
            self.tabs.remove(tab)
            self.dataChanged.emit(index, index, [QtCore.Qt.EditRole])
            self.endRemoveRows()

    def setData(
            self,
            index: QtCore.QModelIndex,
            tab: "tabs.TabData",
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
        self.dataChanged.emit(index, index, [role])
        return True
