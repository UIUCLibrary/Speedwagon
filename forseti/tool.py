import abc
import warnings

import forseti.finder
# from forseti.tools.abstool import AbsTool
from forseti.job import AbsTool
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
