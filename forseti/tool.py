import abc
import importlib
import inspect
import typing
import warnings
from abc import abstractmethod
from collections import namedtuple

from forseti.tools.tool_options import ToolOptionDataType
from forseti.tools import tool_options
from . import tools
from forseti.tools.abstool import AbsTool
import os
from PyQt5 import QtWidgets, QtCore

OptionPair = namedtuple("OptionPair", ("label", "data"))


class AbsToolData(metaclass=abc.ABCMeta):

    def __init__(self, parent=None):
        self._parent = parent
        self.label = ""
        self.widget = self.get_widget()

    @abc.abstractmethod
    def get_widget(self):
        pass

    @property
    def data(self):
        return self.widget.value


class SelectDirectory(AbsToolData):

    def get_widget(self):
        # return PathSelector2()
        return PathSelector()


class PathSelector2:
    def __init__(self, parent=None):
        self.parent = parent


class PathSelector(QtWidgets.QWidget):

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        # self._parent = parent
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._value = ""
        self.line = QtWidgets.QLineEdit(parent=self)
        self.line.editingFinished.connect(self._update_value)
        self.button = QtWidgets.QPushButton(parent=self)
        self.button.setText("Browse")
        self.button.clicked.connect(self.get_path)
        layout.addWidget(self.line)
        layout.addWidget(self.button)
        self.setLayout(layout)

    @property
    def valid(self) -> bool:
        return self._is_valid(self._value)

    def get_path(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Find path")
        if self._is_valid(path):
            self.value = path

    def _update_value(self):
        print("Value is {}".format(self.value))

    @staticmethod
    def _is_valid(value):
        if os.path.exists(value) and os.path.isdir(value):
            return True

    @property
    def value(self):
        return self.line.text()

    @value.setter
    def value(self, value):
        print("My value is now {}".format(value))
        # self._value = value
        self.line.setText(value)

    def destroy(self, destroyWindow=True, destroySubWindows=True):
        print("destroyed")
        super().destroy(destroyWindow, destroySubWindows)


class ToolsListModel(QtCore.QAbstractTableModel):
    NAME = 0
    DESCRIPTION = 1

    def __init__(self, data: typing.Dict["str", AbsTool], parent=None) -> None:
        super().__init__(parent)
        self._data: typing.List[AbsTool] = []
        for k, v in data.items():
            self._data.append(v)

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self._data)

    def data(self, index, role=None):
        if index.isValid():
            data = self._data[index.row()]
            if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
                if index.column() == ToolsListModel.NAME:
                    return data.name
                if index.column() == ToolsListModel.DESCRIPTION:
                    return data.description
                else:
                    print(index.column())
            if role == QtCore.Qt.UserRole:
                return self._data[index.row()]

        return QtCore.QVariant()

    def flags(self, index):
        # if index.isValid():
        return super().flags(index)

    def setData(self, QModelIndex, Any, role=None):
        return super().setData(QModelIndex, Any, role)

    def columnCount(self, parent=QtCore.QModelIndex(), *args, **kwargs):
        return 2


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
        super().__init__(parent)
        warnings.warn("Use ToolOptionsModel2 instead", DeprecationWarning)
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

    def __init__(self, data: typing.List[tool_options.UserOptionPythonDataType], parent=None) -> None:
        super().__init__(parent)
        self._data: typing.List[tool_options.UserOptionPythonDataType] = data

    def data(self, index, role=None):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                data = self._data[index.row()].data
                if data:
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

def available_tools() -> dict:
    """
    Locate all tools that can be loaded

    Returns: Dictionary of all tools

    """
    located_tools = dict()
    root = os.path.join(os.path.dirname(__file__), "tools")
    tree = os.scandir(root)

    for m in tree:
        try:
            module = importlib.import_module("{}.tools.{}".format(__package__, os.path.splitext(m.name)[0]))
            for name_, module_class in inspect.getmembers(module, lambda m: inspect.isclass(m) and not inspect.isabstract(m)):
                if issubclass(module_class, AbsTool):
                    located_tools[module_class.name] = module_class
        except ImportError as e:
            raise ImportError("Unable to load {}. Reason: {}".format(m, e))

    return located_tools
