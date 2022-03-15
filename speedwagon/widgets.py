"""Specialize widgets."""

import json
import typing
import warnings
from typing import Union, Optional, Dict, Any

from PySide6 import QtWidgets, QtCore, QtGui
import speedwagon.models

__all__ = [
    "QtWidgetDelegateSelection"
]


class EditDelegateWidget(QtWidgets.QWidget):
    editingFinished = QtCore.Signal()
    dataChanged = QtCore.Signal()

    def __init__(self, *args, widget_metadata=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._data = None
        self.widget_metadata = widget_metadata or {}
        inner_layout = QtWidgets.QHBoxLayout(parent=self)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(inner_layout)
        self.setAutoFillBackground(True)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value


class CheckBoxWidget(EditDelegateWidget):

    def __init__(self, *args, widget_metadata=None, **kwargs) -> None:
        super().__init__(*args, widget_metadata=widget_metadata, **kwargs)
        self.check_box = QtWidgets.QCheckBox(self)
        self.setFocusProxy(self.check_box)
        self._make_connections()
        self.layout().addWidget(self.check_box)
        self.set_defaults()

    def set_defaults(self) -> None:
        self.data = False

    def _make_connections(self) -> None:
        # pylint: disable=no-member
        self.check_box.stateChanged.connect(self.update_data)

    def update_data(self, state):

        if state == QtCore.Qt.Unchecked:
            self.data = False

        if state == QtCore.Qt.Checked:
            self.data = True
        self.dataChanged.emit()

    @EditDelegateWidget.data.setter
    def data(self, value):
        self._data = value
        if value is True:
            self.check_box.setCheckState(QtCore.Qt.Checked)
        elif value is False:
            self.check_box.setCheckState(QtCore.Qt.Unchecked)


class ComboWidget(EditDelegateWidget):
    def __init__(
            self,
            *args,
            widget_metadata: Optional[Dict[str, Any]] = None,
            **kwargs
    ) -> None:
        super().__init__(widget_metadata=widget_metadata, *args, **kwargs)
        widget_metadata = widget_metadata or {
            'selections': []
        }

        self.combo_box = QtWidgets.QComboBox(self)
        place_holder_text = widget_metadata.get("placeholder_text")

        if place_holder_text is not None:
            self.combo_box.setPlaceholderText(place_holder_text)

        model = QtCore.QStringListModel(widget_metadata['selections'])
        self.combo_box.setModel(model)
        self.combo_box.setCurrentIndex(-1)

        self.setFocusProxy(self.combo_box)
        self._make_connections()
        self.layout().addWidget(self.combo_box)

    def _make_connections(self):
        # pylint: disable=no-member
        self.combo_box.currentTextChanged.connect(self.update_data)

    def update_data(self, value):
        self.data = value

    @EditDelegateWidget.data.setter
    def data(self, value):
        self._data = value

        self._update_combo_box_selected(value, self.combo_box)

    @staticmethod
    def _update_combo_box_selected(
            expected_value: str,
            combo_box: QtWidgets.QComboBox
    ) -> None:
        model: QtCore.QStringListModel = combo_box.model()
        for i in range(model.rowCount()):
            index = model.index(i, 0)
            if index.data() == expected_value:
                combo_box.setCurrentIndex(index.row())
                break


class FileSystemItemSelectWidget(EditDelegateWidget):

    def __init__(self, *args, widget_metadata=None, **kwargs):
        super().__init__(*args, widget_metadata=widget_metadata, **kwargs)
        self.edit = QtWidgets.QLineEdit(parent=self)

        self._make_connections()

        self.edit.addAction(
            self.get_browse_action(),
            QtWidgets.QLineEdit.TrailingPosition
        )
        self.setFocusProxy(self.edit)
        self.layout().addWidget(self.edit)

    def _make_connections(self) -> None:
        # pylint: disable=no-member
        self.edit.textChanged.connect(self._update_data_from_line_edit)
        self.edit.editingFinished.connect(self.editingFinished)

    def _update_data_from_line_edit(self):
        self._data = self.edit.text()
        self.dataChanged.emit()

    def get_browse_action(self):
        return QtGui.QAction("Browse", parent=self)

    @EditDelegateWidget.data.setter
    def data(self, value):
        self._data = value
        self.edit.setText(value)


class DirectorySelectWidget(FileSystemItemSelectWidget):
    def get_browse_action(self):
        icon = QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.SP_DialogOpenButton)
        browse_dir_action = QtGui.QAction(
            icon, "Browse", parent=self
        )
        # pylint: disable=no-member
        browse_dir_action.triggered.connect(self.browse_dir)
        return browse_dir_action

    def browse_dir(
            self,
            get_file_callback: Optional[
                typing.Callable[[], Optional[str]]
            ] = None
    ) -> None:
        def default_use_qt_dialog() -> Optional[str]:
            return QtWidgets.QFileDialog.getExistingDirectory(parent=self)

        selection = (get_file_callback or default_use_qt_dialog)()
        if selection:
            data = selection
            self.data = data
            self.dataChanged.emit()


class FileSelectWidget(FileSystemItemSelectWidget):
    def get_browse_action(self):
        icon = QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.SP_DialogOpenButton)
        browse_file_action = QtGui.QAction(
            icon, "Browse", parent=self
        )
        # pylint: disable=no-member
        browse_file_action.triggered.connect(self.browse_file)
        return browse_file_action

    def __init__(self, *args, widget_metadata=None, **kwargs):
        super().__init__(*args, widget_metadata=widget_metadata, **kwargs)
        widget_metadata = widget_metadata or {}
        self.filter = widget_metadata.get('filter')

    def browse_file(
            self,
            get_file_callback: Optional[
                typing.Callable[[], Optional[str]]
            ] = None
    ) -> None:
        def use_qt_file_dialog():
            result = QtWidgets.QFileDialog.getOpenFileName(parent=self,
                                                           filter=self.filter)
            if result:
                return result[0]
            return None

        selection = (get_file_callback or use_qt_file_dialog)()
        if selection:
            data = selection
            self.data = data
            self.dataChanged.emit()


class QtWidgetDelegateSelection(QtWidgets.QStyledItemDelegate):
    """Special delegate selector.

    Uses data in widget_type field to dynamically select the correct editor
    widget.
    """

    widget_types: typing.Dict[str, typing.Type[EditDelegateWidget]] = {
        "FileSelect": FileSelectWidget,
        "DirectorySelect": DirectorySelectWidget,
        "ChoiceSelection": ComboWidget,
        "BooleanSelect": CheckBoxWidget
    }

    def createEditor(
            self,
            parent: QtWidgets.QWidget,
            option: QtWidgets.QStyleOptionViewItem,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]
    ) -> QtWidgets.QWidget:
        """Create the correct editor widget for editing the data."""
        json_data = json.loads(
            index.data(role=speedwagon.models.ToolOptionsModel4.JsonDataRole)
        )

        editor_type: Optional[typing.Type[EditDelegateWidget]] = \
            self.widget_types.get(json_data['widget_type'])

        if editor_type is None:
            return super().createEditor(parent, option, index)

        editor_widget: EditDelegateWidget = \
            editor_type(widget_metadata=json_data)

        editor_widget.setParent(parent)
        return editor_widget

    def setEditorData(
            self,
            editor: QtWidgets.QWidget,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]
    ) -> None:
        """Update the editor delegate widget with the model's data."""
        editor.data = index.data(typing.cast(int, QtCore.Qt.EditRole))
        super().setEditorData(editor, index)

    def setModelData(
            self,
            editor: QtWidgets.QWidget,
            model: QtCore.QAbstractItemModel,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]) -> None:
        """Set data from editor widget to the model."""
        if hasattr(editor, "data"):
            model.setData(
                index,
                editor.data,
                role=typing.cast(int, QtCore.Qt.EditRole)
            )
        else:
            warnings.warn(
                f"Editor [{editor.__class__.__name__}] has to have the "
                "attribute data to display properly. "
                "Make sure to use a widget that is a subclass of "
                "EditDelegateWidget",
                Warning
            )
            super().setModelData(editor, model, index)
