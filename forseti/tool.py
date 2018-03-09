import abc
import warnings

import forseti.finder
from forseti.tools.abstool import AbsTool
import os
from PyQt5 import QtWidgets


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


class PathSelector2:
    def __init__(self, parent=None):
        warnings.warn("Don't use", DeprecationWarning)
        self.parent = parent


class PathSelector(QtWidgets.QWidget):

    def __init__(self, parent=None, *args, **kwargs):
        warnings.warn("Removing", DeprecationWarning)
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



class ToolFinder(forseti.finder.AbsDynamicFinder):

    @staticmethod
    def py_module_filter(item: os.DirEntry):
        if not str(item.name).startswith("tool_"):
            return False
        return True

    @property
    def package_name(self) -> str:
        return "{}.tools".format(__package__)

    @property
    def base_class(self):
        return AbsTool


def available_tools() -> dict:
    """
    Locate all tools that can be loaded

    Returns: Dictionary of all tools

    """
    root = os.path.join(os.path.dirname(__file__), "tools")
    finder = ToolFinder(root)
    return finder.locate()
