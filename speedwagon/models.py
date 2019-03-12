import sys
from typing import Type, Dict, List, Any, Union, Tuple
import warnings
from abc import abstractmethod
from collections import namedtuple
import enum

from .job import AbsJob
from PyQt5 import QtCore  # type: ignore

from .import tools


class JobModelData(enum.Enum):
    NAME = 0
    DESCRIPTION = 1


class ItemListModel(QtCore.QAbstractTableModel):
    # NAME = 0
    # DESCRIPTION = 1

    def __init__(self, data: Dict["str", Type[AbsJob]]) -> None:
        super().__init__()
        self.jobs: List[Type[AbsJob]] = []
        for k, v in data.items():
            self.jobs.append(v)

    def flags(self, index):
        # if index.isValid():
        return super().flags(index)

    def setData(self, QModelIndex, Any, role=None):
        return super().setData(QModelIndex, Any, role)

    def columnCount(self, parent=QtCore.QModelIndex(), *args, **kwargs):
        return 2

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self.jobs)

    @staticmethod
    def _extract_job_metadata(job: Type[AbsJob],
                              data_type: JobModelData):
        static_data_values: Dict[JobModelData, Any] = {
            JobModelData.NAME: job.name,
            JobModelData.DESCRIPTION: job.description
        }
        return static_data_values[data_type]


OptionPair = namedtuple("OptionPair", ("label", "data"))


class ToolsListModel(ItemListModel):

    def data(self, index, role=None) -> \
            Union[str, Type[AbsJob],
                  QtCore.QSize, QtCore.QVariant]:

        if index.isValid():
            data = self.jobs[index.row()]
            if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
                return self._extract_job_metadata(
                    job=data,
                    data_type=JobModelData(index.column())
                )

            if role == QtCore.Qt.UserRole:
                return self.jobs[index.row()]
            if role == QtCore.Qt.SizeHintRole:
                return QtCore.QSize(10, 20)
        return QtCore.QVariant()


class WorkflowListModel(ItemListModel):
    def data(self, index, role=None) -> \
            Union[str, Type[AbsJob], QtCore.QSize, QtCore.QVariant]:

        if index.isValid():
            data = self.jobs[index.row()]
            if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
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


class ToolOptionsModel(QtCore.QAbstractTableModel):
    def __init__(self, parent):
        super().__init__(parent)
        self._data = []

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self._data)

    def columnCount(self, parent=None, *args, **kwargs):
        if len(self._data) > 0:
            return 1
        else:
            return 0

    @abstractmethod
    def get(self):
        raise NotImplementedError

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        column = index.column()

        if column == 0:
            return QtCore.Qt.ItemIsEnabled \
                   | QtCore.Qt.ItemIsSelectable \
                   | QtCore.Qt.ItemIsEditable
        else:
            print(column, file=sys.stderr)


class ToolOptionsPairsModel(ToolOptionsModel):

    def __init__(self, data: Dict[str, str], parent=None) -> None:
        warnings.warn("Use ToolOptionsModel2 instead", DeprecationWarning)
        super().__init__(parent)
        for k, v in data.items():
            self._data.append(OptionPair(k, v))

    def data(self, index, role=None):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return self._data[index.row()].data
            if role == QtCore.Qt.EditRole:
                return self._data[index.row()].data
        return QtCore.QVariant()

    def setData(self, index, data, role=None):
        if not index.isValid():
            return False
        existing_data = self._data[index.row()]
        self._data[index.row()] = OptionPair(existing_data.label, data)
        return True
        # return super().setData(QModelIndex, data, role)

    def headerData(self, index, Qt_Orientation, role=None):
        if Qt_Orientation == QtCore.Qt.Vertical:
            if role == QtCore.Qt.DisplayRole:
                title = self._data[index].label
                return str(title)
        return QtCore.QVariant()
        # return super().headerData(index, Qt_Orientation, role)

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

        if getattr(QtCore.Qt, m) == value:
            if "role" in m.lower():
                res.append(m)
    return res


class ToolOptionsModel3(ToolOptionsModel):

    def __init__(
            self,
            data: List[tools.options.UserOptionPythonDataType2],
            parent=None
    ) -> None:

        if data is None:
            raise NotImplementedError
        super().__init__(parent)

        self._data: List[tools.options.UserOptionPythonDataType2] = data

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                data = self._data[index.row()].data
                if data is not None:
                    return str(data)
                else:
                    return ""
            if role == QtCore.Qt.EditRole:
                return self._data[index.row()].data
            if role == QtCore.Qt.UserRole:
                return self._data[index.row()]
            if role == QtCore.Qt.SizeHintRole:
                return QtCore.QSize(10, 25)

        return QtCore.QVariant()

    def get(self):
        options = dict()
        for data in self._data:
            options[data.label_text] = data.data
        return options

    def headerData(self, index, Qt_Orientation, role=None):
        if Qt_Orientation == QtCore.Qt.Vertical:
            if role == QtCore.Qt.DisplayRole:
                title = self._data[index].label_text
                return str(title)
        return QtCore.QVariant()

    def setData(self, index, data, role=None):
        if not index.isValid():
            return False
        # existing_data = self._data[index.row()]
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

    def data(self, index: QtCore.QModelIndex, role=None) -> Any:
        if not index.isValid():
            return QtCore.QVariant()

        if role == QtCore.Qt.DisplayRole:
            return self._data[index.row()][index.column()]

        if role == QtCore.Qt.EditRole:
            return self._data[index.row()][index.column()]

        return QtCore.QVariant()

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self._data)

    def add_setting(self, name, value):
        self._data.append((name, value))

    def columnCount(self, parent=None, *args, **kwargs):
        return 2

    def headerData(self, index, Qt_Orientation, role=None):
        if Qt_Orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return self._headers.get(index, "")
        return QtCore.QVariant()

    def flags(self, index: QtCore.QModelIndex):
        if self._headers.get(index.column(), "") == "Key":
            return QtCore.Qt.NoItemFlags

        if self._headers.get(index.column(), "") == "Value":
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

        return super().flags(index)

    def setData(self, index: QtCore.QModelIndex, data, role: QtCore.Qt = None):
        if not index.isValid():
            return False
        row = index.row()
        original_data = self._data[row]

        # Only update the model if the data is actually different
        if data != original_data[1]:
            self._data[row] = (self._data[row][0], data)
            self.dataChanged.emit(index, index, [QtCore.Qt.EditRole])

        return True
