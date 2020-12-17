import abc
import os

from PyQt5 import QtWidgets, QtCore
from typing import Type


class AbsCustomData2(metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def is_valid(cls, value) -> bool:
        pass

    @classmethod
    @abc.abstractmethod
    def edit_widget(cls) -> QtWidgets.QWidget:
        pass


class WidgetMeta(abc.ABCMeta, type(QtCore.QObject)):  # type: ignore
    pass


class CustomItemWidget(QtWidgets.QWidget):
    editingFinished = QtCore.pyqtSignal()

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._data = ""
        self.inner_layout = QtWidgets.QHBoxLayout(parent)
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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self.text_line = QtWidgets.QLineEdit(self)
        self.action = \
            self.text_line.addAction(
                self.get_browse_icon(),
                QtWidgets.QLineEdit.TrailingPosition
            )

        self.action.triggered.connect(self.browse_clicked)

        self.text_line.textEdited.connect(self._change_data)
        self.inner_layout.addWidget(self.text_line)

    @abc.abstractmethod
    def get_browse_icon(self):
        """Get the icon for the right type of browsing."""

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


class ChecksumFile(AbsBrowseableWidget):

    def get_browse_icon(self):
        return QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.SP_FileIcon)

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

    def get_browse_icon(self):
        return QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.SP_DirOpenIcon)

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

    def edit_widget(self) -> QtWidgets.QWidget:
        return self.data_type.edit_widget()


class UserOption2(metaclass=abc.ABCMeta):
    def __init__(self, label_text):
        self.label_text = label_text
        self.data = None

    @abc.abstractmethod
    def is_valid(self) -> bool:
        pass

    def edit_widget(self) -> QtWidgets.QWidget:
        pass


class UserOptionPythonDataType2(UserOption2):
    def __init__(self, label_text, data_type=str) -> None:
        super().__init__(label_text)
        self.data_type = data_type
        self.data = None

    def is_valid(self) -> bool:
        return isinstance(self.data, self.data_type)


class ListSelectionWidget(CustomItemWidget, metaclass=WidgetMeta):

    def __init__(self, selections, *args, **kwargs):
        super().__init__()
        self._combobox = QtWidgets.QComboBox()
        self._selections = selections

        self._model = QtCore.QStringListModel()
        self._model.setStringList(self._selections)
        self._combobox.setModel(self._model)
        self._combobox.currentIndexChanged.connect(self._update)
        self.inner_layout.addWidget(self._combobox,
                                    alignment=QtCore.Qt.AlignBaseline)

    def _update(self):
        self.data = self._combobox.currentText()


class ListSelection(UserOption2):

    def __init__(self, label_text):
        super().__init__(label_text)
        self._selections = []

    def is_valid(self) -> bool:
        return True

    def edit_widget(self) -> QtWidgets.QWidget:
        return ListSelectionWidget(self._selections)

    def add_selection(self, text):
        self._selections.append(text)
        self.data = self._selections[0]
        return self
