import typing
import warnings
from abc import abstractmethod
from collections import namedtuple

from PyQt5 import QtCore

from forseti.tools import AbsTool, options
from forseti.tools.options import ToolOptionDataType


class ItemListModel(QtCore.QAbstractTableModel):
    NAME = 0
    DESCRIPTION = 1

    def __init__(self, data: typing.Dict["str", AbsTool]) -> None:
        super().__init__()
        self._data: typing.List[AbsTool] = []
        for k, v in data.items():
            self._data.append(v)

    def flags(self, index):
        # if index.isValid():
        return super().flags(index)

    def setData(self, QModelIndex, Any, role=None):
        return super().setData(QModelIndex, Any, role)

    def columnCount(self, parent=QtCore.QModelIndex(), *args, **kwargs):
        return 2

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self._data)


OptionPair = namedtuple("OptionPair", ("label", "data"))


class ToolsListModel(ItemListModel):

    def data(self, index, role=None):
        if index.isValid():
            data = self._data[index.row()]
            if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
                if index.column() == self.NAME:
                    return data.name
                if index.column() == self.DESCRIPTION:
                    return data.description
                else:
                    print(index.column())
            if role == QtCore.Qt.UserRole:
                return self._data[index.row()]

        return QtCore.QVariant()


class WorkflowListModel(ItemListModel):

    def data(self, index, role=None):
        if index.isValid():
            data = self._data[index.row()]
            if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
                if index.column() == self.NAME:
                    return data.name
                if index.column() == self.DESCRIPTION:
                    return data.description
                else:
                    print(index.column())
            if role == QtCore.Qt.UserRole:
                return self._data[index.row()]

        return QtCore.QVariant()


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
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable


class ToolOptionsPairsModel(ToolOptionsModel):

    def __init__(self, data: typing.Dict[str, str], parent=None) -> None:
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


class ToolOptionsModel2(ToolOptionsModel):

    def __init__(self, data: typing.List[ToolOptionDataType], parent=None) -> None:
        warnings.warn("Use ToolOptionsModel3 instead", DeprecationWarning)
        super().__init__(parent)
        self._data: typing.List[ToolOptionDataType] = data

    def data(self, index, role=None):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return str(self._data[index.row()].data)
            if role == QtCore.Qt.EditRole:
                return self._data[index.row()].data
            if role == QtCore.Qt.UserRole:
                return self._data[index.row()]
        return QtCore.QVariant()

    def get(self):
        options = dict()
        for data in self._data:
            options[data.name] = data.data
        return options

    def headerData(self, index, Qt_Orientation, role=None):
        if Qt_Orientation == QtCore.Qt.Vertical:
            if role == QtCore.Qt.DisplayRole:
                title = self._data[index].name
                return str(title)
        return QtCore.QVariant()

    def setData(self, index, data, role=None):
        if not index.isValid():
            return False
        existing_data = self._data[index.row()]
        self._data[index.row()].data = data
        return True


class ToolOptionsModel3(ToolOptionsModel):

    def __init__(self, data: typing.List[options.UserOptionPythonDataType], parent=None) -> None:
        if data is None:
            raise NotImplementedError
        super().__init__(parent)

        self._data: typing.List[options.UserOptionPythonDataType] = data

    def data(self, index, role=None):
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
        existing_data = self._data[index.row()]
        self._data[index.row()].data = data
        return True
