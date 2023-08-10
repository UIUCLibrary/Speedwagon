"""Shared custom widgets."""

import abc
import os
import warnings
from typing import Type, Union, List, Optional
from PySide6 import QtWidgets, QtCore, QtGui

__all__ = ["CustomItemWidget"]


class AbsCustomData2(metaclass=abc.ABCMeta):
    """Base class for custom data types."""

    @classmethod
    @abc.abstractmethod
    def is_valid(cls, value: str) -> bool:
        """Check user selection is valid."""

    @classmethod
    @abc.abstractmethod
    def edit_widget(cls) -> QtWidgets.QWidget:
        """Get widget for editing data type."""


class WidgetMeta(abc.ABCMeta, type(QtCore.QObject)):  # type: ignore
    """Widget meta class."""


class CustomItemWidget(QtWidgets.QWidget):
    """Custom item Widget."""

    editingFinished = QtCore.Signal()

    def __init__(
        self, *args, parent: Optional[QtWidgets.QWidget] = None, **kwargs
    ) -> None:
        """Create a custom item widget."""
        warnings.warn(
            "Use workflow.AbsOutputOptionDataType instead",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(parent, *args, **kwargs)
        self._data = ""
        self.inner_layout = (
            QtWidgets.QHBoxLayout(parent)
            if parent is not None
            else QtWidgets.QHBoxLayout()
        )
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.inner_layout)
        self.setAutoFillBackground(True)

    @property
    def data(self) -> str:
        """Access the data from the widget."""
        return self._data

    @data.setter
    def data(self, value: str) -> None:
        self._data = value
        self.editingFinished.emit()


class AbsBrowseableWidget(CustomItemWidget):
    """Abstract browsable widget."""

    def __init__(self, *args, **kwargs) -> None:
        """Create the base structure for a browseable widget."""
        warnings.warn(
            "Use workflow.AbsOutputOptionDataType instead",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__()
        self.text_line = QtWidgets.QLineEdit(self)
        self.action = self.text_line.addAction(
            self.get_browse_icon(),
            QtWidgets.QLineEdit.ActionPosition.TrailingPosition,
        )

        self.action.triggered.connect(self.browse_clicked)  # type: ignore

        # pylint: disable=no-member
        self.text_line.textEdited.connect(self._change_data)  # type: ignore

        self.inner_layout.addWidget(self.text_line)

    def get_browse_icon(self) -> QtGui.QIcon:
        """Get the icon for the right type of browsing."""
        return QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon
        )

    @abc.abstractmethod
    def browse_clicked(self) -> None:
        """Execute action when browse selected."""

    @property
    def data(self):
        """Access the data from the widget."""
        return super().data

    @data.setter
    def data(self, value: str) -> None:
        self._data = value
        self.text_line.setText(value)

    def _change_data(self, value):
        self.data = value


class AbsCustomData3(metaclass=abc.ABCMeta):
    """Abstract data type creating custom data."""

    @classmethod
    @abc.abstractmethod
    def is_valid(cls, value) -> bool:
        """Check user selection is valid."""

    @classmethod
    @abc.abstractmethod
    def edit_widget(cls) -> QtWidgets.QWidget:
        """Get widget for editing the data."""


class ChecksumFile(AbsBrowseableWidget):
    """Widget for checksum md5 files."""

    def get_browse_icon(self) -> QtGui.QIcon:
        """Get the os-specific browse icon for files."""
        return QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_FileIcon
        )

    def browse_clicked(self) -> None:
        """Launch file browser to locate an .md5 file."""
        selection = QtWidgets.QFileDialog.getOpenFileName(
            self, filter="Checksum files (*.md5)"
        )

        if selection[0]:
            self.data = selection[0]
            self.editingFinished.emit()


class ChecksumData(AbsCustomData3):
    """Checksum data format."""

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check user selection is valid."""
        if not os.path.exists(value):
            return False
        if os.path.basename(value) == "checksum":
            print("No a checksum file")
            return False
        return True

    @classmethod
    def edit_widget(cls) -> QtWidgets.QWidget:
        """Get a file select dialog box."""
        return ChecksumFile()


class FolderBrowseWidget(AbsBrowseableWidget):
    """Widget for browsing for folders on the hard drive."""

    def get_browse_icon(self) -> QtGui.QIcon:
        """Get the os-specific browse icon for folders."""
        return QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon
        )

    def browse_clicked(self) -> None:
        """Browse hard drive to select an existing directory."""
        selection = QtWidgets.QFileDialog.getExistingDirectory()
        if selection:
            self.data = selection
            self.editingFinished.emit()


class FolderData(AbsCustomData3, metaclass=abc.ABCMeta):
    """Select a folder as a data type."""

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check user selection is valid."""
        if not os.path.isdir(value):
            return False
        return True

    @classmethod
    def edit_widget(cls) -> QtWidgets.QWidget:
        """Get Folder browser widget."""
        return FolderBrowseWidget()


class UserOption3(metaclass=abc.ABCMeta):
    """User option."""

    def __init__(self, label_text: str):
        """Create user option data."""
        self.label_text = label_text
        self.data = None

    @abc.abstractmethod
    def is_valid(self) -> bool:
        """Check user selection is valid."""

    def edit_widget(self) -> Optional[QtWidgets.QWidget]:
        """Get widget for editing."""
        return None


class UserOptionPythonDataType2(UserOption3):
    """User option Python data type."""

    def __init__(
        self, label_text: str, data_type: Type[Union[str, int, bool]] = str
    ) -> None:
        """Create a user options data type."""
        super().__init__(label_text)
        self.data_type = data_type
        self.data = None

    def is_valid(self) -> bool:
        """Check user selection is valid."""
        return isinstance(self.data, self.data_type)


class ListSelectionWidget(CustomItemWidget):
    """List selection widget."""

    def __init__(self, selections: List[str], *args, **kwargs) -> None:
        """Create a list selection widget."""
        super().__init__()
        self._combobox = QtWidgets.QComboBox()
        self._selections = selections

        self._model = QtCore.QStringListModel()
        self._model.setStringList(self._selections)
        self._combobox.setModel(self._model)

        # pylint: disable=no-member
        self._combobox.currentIndexChanged.connect(  # type: ignore
            self._update
        )
        self.inner_layout.addWidget(
            self._combobox, alignment=QtCore.Qt.AlignmentFlag.AlignBaseline
        )

    def _update(self) -> None:
        self.data = self._combobox.currentText()
