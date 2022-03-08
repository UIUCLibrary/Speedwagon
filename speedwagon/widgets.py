import abc
import json
import typing
import warnings
from typing import Union, Optional

from PySide6 import QtWidgets, QtCore, QtGui
import speedwagon.models


class AbsOutputOptionDataType(abc.ABC):
    label: str
    widget_name: str

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "widget_name"):
            raise TypeError(f"Can't instantiate abstract class {cls.__name__} "
                            f"without abstract property widget_name")
        return super().__init_subclass__()

    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label
        self.value = None

    def build_json_data(self) -> str:
        return json.dumps(
            {
                "widget_type": self.widget_name
            }
        )


class DropDownSelection(AbsOutputOptionDataType):
    widget_name: str = "DropDownSelect"

    def __init__(self, label: str) -> None:
        super().__init__(label)
        self._selections: typing.List[str] = []

    def add_selection(self, label: str) -> None:
        self._selections.append(label)

    def build_json_data(self) -> str:
        return json.dumps(
            {
                "widget_type": self.widget_name,
                "selections": self._selections
            }
        )


class TextLineEditWidget(AbsOutputOptionDataType):
    widget_name = "line_edit"


class EditDelegateWidget(QtWidgets.QWidget):
    editingFinished = QtCore.Signal()
    dataChanged = QtCore.Signal()

    def __init__(self, widget_metadata, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._data = None
        self.widget_metadata = widget_metadata
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


class DropDownWidget(EditDelegateWidget):
    def __init__(self, widget_metadata, *args, **kwargs) -> None:
        super().__init__(widget_metadata, *args, **kwargs)
        self.combo_box = QtWidgets.QComboBox(self)
        model = QtCore.QStringListModel(widget_metadata['selections'])
        self.combo_box.setModel(model)
        # model: QtGui.QStandardItemModel = self.combo_box.model()
        # model: QtGui.Q = self.combo_box.model()

        self.setFocusProxy(self.combo_box)
        self.layout().addWidget(self.combo_box)
        self.combo_box.currentTextChanged.connect(self.update_data)
        # for selection in widget_metadata['selections']:
        #     model.appendRow(selection)
        #     # print(model.insertRow(0, selection))
        #     # self.combo_box.addItem(selection)

    def update_data(self, value):
        self.data = value


class FileSystemItemSelectWidget(EditDelegateWidget):

    def __init__(self, widget_metadata, *args, **kwargs):
        super().__init__(widget_metadata, *args, **kwargs)
        self.edit = QtWidgets.QLineEdit(parent=self)
        self.edit.textChanged.connect(self._update_data_from_line_edit)
        self.edit.editingFinished.connect(self.editingFinished)
        self.edit.addAction(
            self.get_browse_action(),
            QtWidgets.QLineEdit.TrailingPosition
        )
        self.setFocusProxy(self.edit)
        self.layout().addWidget(self.edit)

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
        browse_dir_action.triggered.connect(self.browse_dir)
        return browse_dir_action

    def browse_dir(self):
        selection = QtWidgets.QFileDialog.getExistingDirectory(
            parent=self,
        )

        if selection:
            data = selection
            self.data = data
            self.dataChanged.emit()

    def __init__(self, widget_metadata, *args, **kwargs) -> None:
        super().__init__(widget_metadata, *args, **kwargs)


class FileSelectWidget(FileSystemItemSelectWidget):
    def get_browse_action(self):
        icon = QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.SP_DialogOpenButton)
        browse_file_action = QtGui.QAction(
            icon, "Browse", parent=self
        )
        browse_file_action.triggered.connect(self.browse_file)
        return browse_file_action

    def __init__(self, widget_metadata, *args, **kwargs):
        super().__init__(widget_metadata, *args, **kwargs)
        self.filter = widget_metadata.get('filter')

    def browse_file(self):
        selection = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            filter=self.filter
        )

        if selection[0]:
            data = selection[0]
            self.data = data
            self.dataChanged.emit()


class FileSelectData(AbsOutputOptionDataType):
    widget_name: str = "FileSelect"

    def __init__(self, label: str) -> None:
        super().__init__(label)
        self.filter: Optional[str] = None

    def build_json_data(self) -> str:
        data = json.loads(super().build_json_data())
        data['filter'] = self.filter
        return json.dumps(data)


class DirectorySelect(AbsOutputOptionDataType):
    widget_name = "DirectorySelect"


class OptionWidgetBuilder(abc.ABC):
    @abc.abstractmethod
    def build(self, widget: AbsOutputOptionDataType) -> None:
        """Build the widget in the correct format."""


class DelegateSelection(QtWidgets.QStyledItemDelegate):
    widget_types: typing.Dict[str, typing.Type[EditDelegateWidget]] = {
        "FileSelect": FileSelectWidget,
        "DirectorySelect": DirectorySelectWidget,
        "DropDownSelect": DropDownWidget
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
        json_data = json.loads(
            index.data(role=speedwagon.models.ToolOptionsModel4.JsonDataRole)
        )

        editor_type: Optional[typing.Type[EditDelegateWidget]] = \
            self.widget_types.get(json_data['widget_type'])

        if editor_type is None:
            return super().createEditor(parent, option, index)

        editor_widget: EditDelegateWidget = editor_type(json_data)
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
        data = index.data(typing.cast(int, QtCore.Qt.EditRole))
        if data is not None:
            editor.data = data
        super().setEditorData(editor, index)

    def setModelData(
            self,
            editor: QtWidgets.QWidget,
            model: QtCore.QAbstractItemModel,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]) -> None:
        if hasattr(editor, "data") and editor.data is not None:
            model.setData(
                index,
                editor.data,
                role=typing.cast(int, QtCore.Qt.EditRole)
            )
        else:
            warnings.warn(
                "Editor has to data. Make sure to use a widget that "
                "subclaseses EditDelegateWidget"
            )
            super().setModelData(editor, model, index)
