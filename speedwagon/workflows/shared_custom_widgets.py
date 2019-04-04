import abc
import os

from PyQt5 import QtWidgets, QtCore
from typing import Type
from speedwagon.tools import options


class WidgetMeta(abc.ABCMeta, type(QtCore.QObject)):  # type: ignore
    pass


class CustomItemWidget(QtWidgets.QWidget):
    editingFinished = QtCore.pyqtSignal()

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._data = ""
        self.inner_layout = QtWidgets.QHBoxLayout(parent)
        self.inner_layout.setSpacing(3)
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.inner_layout)
        self.setAutoFillBackground(True)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        self.editingFinished.emit()


class AbsBrowseableWidget(CustomItemWidget, metaclass=WidgetMeta):
    # class AbsBrowseableWidget(metaclass=WidgetMeta):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self.text_line = QtWidgets.QLineEdit(self)
        size_p = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                       QtWidgets.QSizePolicy.MinimumExpanding)
        self.text_line.setSizePolicy(size_p)
        self.browse_button = QtWidgets.QPushButton("Browse", parent=self)
        # self.browse_button.setSizePolicy(size_p)
        self.inner_layout.addWidget(self.text_line)
        self.inner_layout.addWidget(self.browse_button)
        self.text_line.textEdited.connect(self._change_data)
        self.text_line.editingFinished.connect(self.editingFinished)
        # self.text_line.focus
        # self.text_line.
        self.browse_button.clicked.connect(self.browse_clicked)
        # self.browse_button.clicked.connect(self.editingFinished)

        # self.setFocusPolicy(QtCore.Qt.StrongFocus)
        # self.text_line.setFocusPolicy(QtCore.Qt.StrongFocus)

    @abc.abstractmethod
    def browse_clicked(self):
        pass

    @property
    def data(self):
        return super().data

    @data.setter
    def data(self, value):
        self._data = value
        self.text_line.setText(value)

    def _change_data(self, value):
        self.data = value


class AbsCustomData3(metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def is_valid(cls, value) -> bool:
        pass

    @classmethod
    @abc.abstractmethod
    def edit_widget(cls) -> QtWidgets.QWidget:
        pass


class ChecksumFile(options.AbsBrowseableWidget):
    def browse_clicked(self):
        selection = QtWidgets.QFileDialog.getOpenFileName(
            filter="Checksum files (*.md5)")

        if selection[0]:
            self.data = selection[0]
            self.editingFinished.emit()


class ChecksumData(AbsCustomData3):

    @classmethod
    def is_valid(cls, value) -> bool:
        if not os.path.exists(value):
            return False
        if os.path.basename(value) == "checksum":
            print("No a checksum file")
            return False
        return True

    @classmethod
    def edit_widget(cls) -> QtWidgets.QWidget:
        return ChecksumFile()


class FolderBrowseWidget(AbsBrowseableWidget):

    def browse_clicked(self):
        selection = QtWidgets.QFileDialog.getExistingDirectory()
        if selection:
            self.data = selection
            self.editingFinished.emit()


class FolderData(AbsCustomData3, metaclass=abc.ABCMeta):

    @classmethod
    def is_valid(cls, value) -> bool:
        if not os.path.isdir(value):
            return False
        return True

    @classmethod
    def edit_widget(cls) -> QtWidgets.QWidget:
        return FolderBrowseWidget()

    # @classmethod
    # def browse(cls):
    #     return QtWidgets.QLineEdit()


class UserOption3(metaclass=abc.ABCMeta):
    def __init__(self, label_text):
        self.label_text = label_text
        self.data = None

    @abc.abstractmethod
    def is_valid(self) -> bool:
        pass

    def edit_widget(self) -> QtWidgets.QWidget:
        pass


class UserOptionCustomDataType(UserOption3):
    def __init__(
            self,
            label_text,
            data_type: Type[AbsCustomData3]
    ) -> None:

        super().__init__(label_text)
        self.data_type = data_type
        self.data = None

    def is_valid(self) -> bool:
        return self.data_type.is_valid(self.data)
        # return self.data_type.is_valid(self.data)

    def edit_widget(self) -> QtWidgets.QWidget:
        return self.data_type.edit_widget()
