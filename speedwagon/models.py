"""Data models for displaying data to user in the user interface"""

import sys
from typing import Type, Dict, List, Any, Union, Tuple, Optional
import warnings
from abc import abstractmethod
from collections import namedtuple
import enum

from PyQt5 import QtCore  # type: ignore
from speedwagon import tabs, Workflow
from .job import AbsWorkflow
from .workflows import shared_custom_widgets

QtConstant = int

# Qt has non-pythonic names for it's methods
# pylint: disable=invalid-name, unused-argument


class JobModelData(enum.Enum):
    NAME = 0
    DESCRIPTION = 1


class ItemListModel(QtCore.QAbstractTableModel):

    def __init__(self, data: Dict["str", Type[AbsWorkflow]]) -> None:
        super().__init__()
        self.jobs: List[Type[AbsWorkflow]] = list(data.values())

    def columnCount(self, *args, parent=QtCore.QModelIndex(), **kwargs) -> int:
        return 2

    def rowCount(self, *args, parent=None, **kwargs) -> int:
        return len(self.jobs)

    @staticmethod
    def _extract_job_metadata(job: Type[AbsWorkflow],
                              data_type: JobModelData):
        static_data_values: Dict[JobModelData, Any] = {
            JobModelData.NAME: job.name,
            JobModelData.DESCRIPTION: job.description
        }
        return static_data_values[data_type]


OptionPair = namedtuple("OptionPair", ("label", "data"))


class WorkflowListModel(ItemListModel):
    def data(
            self,
            index: QtCore.QModelIndex,
            role: QtConstant = None
    ) -> Union[str, Type[AbsWorkflow], QtCore.QSize, QtCore.QVariant]:

        if index.isValid():
            data = self.jobs[index.row()]
            if role in [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole]:
                return self._extract_job_metadata(
                    job=data,
                    data_type=JobModelData(index.column())
                )

            if role == QtCore.Qt.UserRole:
                job = self.jobs[index.row()]
                return job
            if role == QtCore.Qt.SizeHintRole:
                return QtCore.QSize(10, 20)

        return QtCore.QVariant()

    def sort(self, key=None, order=None):
        self.layoutAboutToBeChanged.emit()

        self.jobs.sort(key=key or (lambda i: i.name))
        self.layoutChanged.emit()


class WorkflowListModel2(QtCore.QAbstractListModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.workflows: List[Workflow] = []

    def __iadd__(self, other: "Workflow") -> "WorkflowListModel2":
        self.add_workflow(other)
        return self

    def __isub__(self, other: "Workflow") -> "WorkflowListModel2":
        self.remove_workflow(other)
        return self

    def rowCount(self, parent=None, *args, **kwargs) -> int:
        return len(self.workflows)

    def data(
            self,
            index: QtCore.QModelIndex,
            role: QtConstant = None
    ) -> Union[str, Workflow, QtCore.QVariant]:
        if not index.isValid():
            return QtCore.QVariant()
        row = index.row()

        if role is None:
            return QtCore.QVariant()
        workflow: Dict[int, Optional[Union[str,
                                           Workflow,
                                           QtCore.QVariant]]] = {
            QtCore.Qt.DisplayRole: self.workflows[row].name,
            QtCore.Qt.UserRole: self.workflows[row],
        }
        value = workflow.get(role)
        if value is not None:
            return value
        return QtCore.QVariant()

    def sort(self, key=None, order=None):
        self.layoutAboutToBeChanged.emit()

        self.workflows.sort(key=key or (lambda i: i.name))
        self.layoutChanged.emit()

    def add_workflow(self, workflow: Workflow) -> None:
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

    def setData(self, index: QtCore.QModelIndex,
                workflow: Workflow, role: QtConstant = None) -> bool:

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

    def remove_workflow(self, workflow: Workflow) -> None:
        if workflow in self.workflows:
            index = QtCore.QModelIndex()
            self.beginRemoveRows(index, 0, self.rowCount())
            self.workflows.remove(workflow)
            self.dataChanged.emit(index, index, [QtCore.Qt.EditRole])
            self.endRemoveRows()


class ToolOptionsModel(QtCore.QAbstractTableModel):
    def __init__(self, parent):
        super().__init__(parent)
        self._data = []

    def rowCount(self, parent=None, *args, **kwargs) -> int:
        return len(self._data)

    def columnCount(self, parent=None, *args, **kwargs) -> int:
        if len(self._data) > 0:
            return 1
        return 0

    @abstractmethod
    def get(self):
        raise NotImplementedError

    def flags(self, index: QtCore.QModelIndex):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        column = index.column()

        if column == 0:
            return QtCore.Qt.ItemIsEnabled \
                   | QtCore.Qt.ItemIsSelectable \
                   | QtCore.Qt.ItemIsEditable
        print(column, file=sys.stderr)


class ToolOptionsPairsModel(ToolOptionsModel):

    def __init__(self, data: Dict[str, str], parent=None) -> None:
        warnings.warn("Use ToolOptionsModel2 instead", DeprecationWarning)
        super().__init__(parent)
        for key, value in data.items():
            self._data.append(OptionPair(key, value))

    def data(self, index: QtCore.QModelIndex, role: QtConstant = None):
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
        if not index.isValid():
            return False
        existing_data = self._data[index.row()]
        self._data[index.row()] = OptionPair(existing_data.label, data)
        return True

    def headerData(
            self,
            index: int,
            orientation: QtConstant,
            role=None
    ) -> Union[str, QtCore.QVariant]:
        if orientation == QtCore.Qt.Vertical \
                and role == QtCore.Qt.DisplayRole:
            title = self._data[index].label
            return str(title)
        return QtCore.QVariant()

    def get(self) -> dict:
        options = dict()
        for data in self._data:
            options[data.label] = data.data
        return options


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

    def __init__(
            self,
            data: List[shared_custom_widgets.UserOptionPythonDataType2],
            parent: QtCore.QObject = None
    ) -> None:

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
        options: Dict[str, Any] = {}
        for data in self._data:
            options[data.label_text] = data.data
        return options

    def headerData(
            self,
            index: int,
            orientation: int,
            role=None) -> Union[QtCore.QVariant, str]:

        if orientation == QtCore.Qt.Vertical and \
                role == QtCore.Qt.DisplayRole:

            title = self._data[index].label_text
            return str(title)
        return QtCore.QVariant()

    def setData(
            self,
            index: QtCore.QModelIndex,
            data,
            role: QtConstant = None
    ) -> bool:

        if not index.isValid():
            return False
        self._data[index.row()].data = data
        return True


class SettingsModel(QtCore.QAbstractTableModel):

    def __init__(self, *__args) -> None:
        super().__init__(*__args)
        self._data: List[Tuple[str, str]] = []
        self._headers = {
            0: "Key",
            1: "Value"
        }

    def data(
            self,
            index: QtCore.QModelIndex,
            role: QtConstant = None
    ) -> Union[str, QtCore.QVariant]:

        if not index.isValid():
            return QtCore.QVariant()

        if role == QtCore.Qt.DisplayRole:
            return self._data[index.row()][index.column()]

        if role == QtCore.Qt.EditRole:
            return self._data[index.row()][index.column()]

        return QtCore.QVariant()

    def rowCount(self,  *args, parent=None, **kwargs) -> int:
        return len(self._data)

    def add_setting(self, name: str, value: str) -> None:
        self._data.append((name, value))

    def columnCount(self, *args, parent=None, **kwargs) -> int:
        return 2

    def headerData(
            self,
            index: int,
            orientation: int,
            role: QtConstant = None
    ) -> Union[str, QtCore.QVariant]:

        if orientation == QtCore.Qt.Horizontal and \
                role == QtCore.Qt.DisplayRole:
            return self._headers.get(index, "")
        return QtCore.QVariant()

    def flags(self, index: QtCore.QModelIndex):
        if self._headers.get(index.column(), "") == "Key":
            return QtCore.Qt.NoItemFlags

        if self._headers.get(index.column(), "") == "Value":
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

        return super().flags(index)

    def setData(
            self,
            index: QtCore.QModelIndex,
            data,
            role: QtConstant = None
    ) -> bool:

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

    def __init__(self, parent: QtCore.QObject = None) -> None:
        super().__init__(parent)
        self.tabs: List[tabs.TabData] = []

    def __contains__(self, value: "tabs.TabData") -> bool:
        # Looks for the tab based on the tab_name string
        for tab in self.tabs:
            if tab.tab_name == value:
                return True
        return False

    def __iadd__(self, other: "tabs.TabData") -> "TabsModel":
        self.add_tab(other)
        return self

    def __isub__(self, other: "tabs.TabData") -> "TabsModel":
        self.remove_tab(other)
        return self

    def data(self,
             index: QtCore.QModelIndex,
             role: QtConstant = None
             ) -> Union[QtCore.QVariant, str, "tabs.TabData"]:

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

    def rowCount(self, parent=None, *args, **kwargs) -> int:
        return len(self.tabs)

    def add_tab(self, tab: "tabs.TabData") -> None:
        row = len(self.tabs)
        index = self.createIndex(row, 0)
        self.beginInsertRows(index, 0, self.rowCount())
        self.tabs.insert(row, tab)
        self.dataChanged.emit(index, index, [QtCore.Qt.EditRole])
        self.endInsertRows()

    def remove_tab(self, tab: "tabs.TabData") -> None:
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
            role: QtConstant = None
    ) -> bool:

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
