import abc
import os
import typing
from PyQt5 import QtWidgets


class ToolOption:

    def __init__(self, name) -> None:
        self.name = name
        self._data = ""


class ToolOptionDataType(ToolOption):
    def __init__(self, name, data_type=str) -> None:
        super().__init__(name)
        self.data_type = data_type
        self._data = ""

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if not isinstance(value, self.data_type):
            raise TypeError("Invalid type")
        self._data = value


class UserOption(metaclass=abc.ABCMeta):
    def __init__(self, label_text):
        self.label_text = label_text
        self.data = None

    @abc.abstractmethod
    def is_valid(self) -> bool:
        pass

    def browse(self):
        pass


class UserOptionPythonDataType(UserOption):
    def __init__(self, label_text, data_type=str) -> None:
        super().__init__(label_text)
        self.data_type = data_type
        self.data = None

    def is_valid(self) -> bool:
        return isinstance(self.data, self.data_type)




class AbsCustomData(metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def is_valid(cls, value)->bool:
        pass

    @classmethod
    def browse(cls):
        pass


class UserOptionCustomDataType(UserOption):
    def __init__(self, label_text, data_type: typing.Type[AbsCustomData]) -> None:
        super().__init__(label_text)
        self.data_type = data_type
        self.data = None

    def is_valid(self) -> bool:
        return self.data_type.is_valid(self.data)

    def browse(self):
        return self.data_type.browse()


class FileData(AbsCustomData, metaclass=abc.ABCMeta):

    @classmethod
    def is_valid(cls, value) -> bool:
        if not os.path.isfile(value):
            return False
        if os.path.basename(value) != cls.filename():
            return False
        return True


    @classmethod
    def browse(cls)->QtWidgets.QWidget:
        browser = QtWidgets.QFileDialog()
        browser.setModal(True)
        browser.setFileMode(QtWidgets.QFileDialog.AnyFile)
        browser.setNameFilter(cls.filter())
        return browser


    @staticmethod
    @abc.abstractmethod
    def filename()->str:
        pass


    @staticmethod
    @abc.abstractmethod
    def filter()->str:
        pass

