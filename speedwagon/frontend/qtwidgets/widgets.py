"""Specialize widgets."""
import json
import os.path
import typing
from typing import Union, Optional, Dict, Any

from PySide6 import QtWidgets, QtCore, QtGui
from speedwagon.frontend.qtwidgets import models, ui_loader, ui
try:  # pragma: no cover
    from importlib.resources import as_file
    from importlib import resources
except ImportError:  # pragma: no cover
    import importlib_resources as resources  # type: ignore
    from importlib_resources import as_file


if typing.TYPE_CHECKING:
    from speedwagon.workflow import AbsOutputOptionDataType
__all__ = [
]

WidgetMetadata = Dict[str, Union[str, None]]


class EditDelegateWidget(QtWidgets.QWidget):
    editingFinished = QtCore.Signal()
    dataChanged = QtCore.Signal()

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
            widget_metadata: Optional[WidgetMetadata] = None,
    ) -> None:
        super().__init__(parent)
        self._data: Optional[Any] = None
        self.widget_metadata = widget_metadata or {}
        inner_layout = QtWidgets.QHBoxLayout()
        inner_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(inner_layout)
        self.setAutoFillBackground(True)

    @property
    def data(self) -> Optional[Any]:
        return self._data

    @data.setter
    def data(self, value: Any) -> None:
        self._data = value


class LineEditWidget(EditDelegateWidget):

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
            widget_metadata: Optional[WidgetMetadata] = None,
    ) -> None:
        super().__init__(widget_metadata=widget_metadata, parent=parent)
        self.text_box = QtWidgets.QLineEdit(self)
        self._make_connections()
        self.setFocusProxy(self.text_box)
        self.text_box.installEventFilter(self)
        self.text_box.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        layout = self.layout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text_box)
        self.setLayout(layout)

    def _make_connections(self) -> None:
        # pylint: disable=no-member
        self.text_box.textChanged.connect(  # type: ignore
            self._update_data_from_line_edit
        )

    def _update_data_from_line_edit(self) -> None:
        self._data = self.text_box.text()
        self.dataChanged.emit()

    @EditDelegateWidget.data.setter
    def data(self, value: str) -> None:
        self._data = value
        self.text_box.setText(value)


class CheckBoxWidget(EditDelegateWidget):

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
            widget_metadata: Optional[WidgetMetadata] = None,
    ) -> None:
        super().__init__(widget_metadata=widget_metadata, parent=parent)
        self.check_box = QtWidgets.QCheckBox(self)
        self.setFocusProxy(self.check_box)
        if widget_metadata:
            self.check_box.setText(widget_metadata['label'])
        self._make_connections()
        layout = self.layout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.check_box)
        self.setLayout(layout)
        self.set_defaults()

    def set_defaults(self) -> None:
        self.data = False

    def _make_connections(self) -> None:
        # pylint: disable=no-member
        self.check_box.stateChanged.connect(self.update_data)  # type: ignore

    def update_data(self, state: QtCore.Qt.CheckState) -> None:
        self.data = self.check_box.isChecked()
        self.dataChanged.emit()

    @EditDelegateWidget.data.setter
    def data(self, value: bool) -> None:
        self._data = value
        if value:
            self.check_box.setCheckState(QtCore.Qt.CheckState.Checked)
        else:
            self.check_box.setCheckState(QtCore.Qt.CheckState.Unchecked)


class ComboWidget(EditDelegateWidget):
    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
            widget_metadata: Optional[WidgetMetadata] = None,
    ) -> None:
        super().__init__(widget_metadata=widget_metadata, parent=parent)
        widget_metadata = widget_metadata or {
            'selections': []
        }

        self.combo_box = QtWidgets.QComboBox(self.parent())
        place_holder_text = widget_metadata.get("placeholder_text")

        if place_holder_text is not None:
            self.combo_box.setPlaceholderText(place_holder_text)

        model = QtCore.QStringListModel(widget_metadata['selections'])
        self.combo_box.setModel(model)
        self.combo_box.setCurrentIndex(-1)

        self.setFocusProxy(self.combo_box)
        self._make_connections()
        layout = self.layout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.combo_box)
        self.setLayout(layout)

    def _make_connections(self) -> None:
        # pylint: disable=no-member
        self.combo_box.currentTextChanged.connect(  # type: ignore
            self.update_data
        )

    def update_data(self, value: str) -> None:
        self.data = value
        self.dataChanged.emit()
        self.editingFinished.emit()

    @EditDelegateWidget.data.setter
    def data(self, value) -> None:
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

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
            widget_metadata: Optional[WidgetMetadata] = None,
    ) -> None:
        super().__init__(widget_metadata=widget_metadata, parent=parent)
        self.edit = QtWidgets.QLineEdit(self)
        self._make_connections()

        self.edit.addAction(
            self.get_browse_action(),
            QtWidgets.QLineEdit.ActionPosition.TrailingPosition
        )
        self.setFocusProxy(self.edit)
        self.edit.installEventFilter(self)
        self.edit.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        layout = self.layout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit)
        self.setLayout(layout)
        self.setAcceptDrops(True)

    def _make_connections(self) -> None:
        # pylint: disable=no-member
        self.edit.textChanged.connect(  # type: ignore
            self._update_data_from_line_edit
        )

    def _update_data_from_line_edit(self) -> None:
        self._data = self.edit.text()
        self.dataChanged.emit()

    def get_browse_action(self) -> QtGui.QAction:
        return QtGui.QAction("Browse", parent=self)

    @EditDelegateWidget.data.setter
    def data(self, value: str) -> None:
        self._data = value
        self.edit.setText(value)

    def drop_acceptable_data(self, mime_data: QtCore.QMimeData) -> bool:
        """Return if the item dragged over is the right type."""
        return True

    def eventFilter(
            self,
            watched: QtCore.QObject,
            event: QtCore.QEvent
    ) -> bool:
        if event.type() == event.Type.DragEnter:
            event = typing.cast(QtGui.QDragEnterEvent, event)
            if self.drop_acceptable_data(event.mimeData()):
                event.accept()
            else:
                event.ignore()
            return True
        if event.type() == event.Type.Drop:
            event = typing.cast(QtGui.QDropEvent, event)
            self.edit.setText(self.extract_path_from_event(event))
            event.accept()
            return True
        return super().eventFilter(watched, event)

    @staticmethod
    def extract_path_from_event(
        event: Union[QtGui.QDropEvent, QtGui.QDragMoveEvent]
    ) -> str:
        mime_data = event.mimeData()
        urls = mime_data.urls()
        return urls[0].path()


class DirectorySelectWidget(FileSystemItemSelectWidget):
    def drop_acceptable_data(self, mime_data: QtCore.QMimeData) -> bool:
        if not mime_data.hasUrls():
            return False
        urls = mime_data.urls()
        if len(urls) != 1:
            return False
        path = urls[0].path()
        return os.path.exists(path) and os.path.isdir(path)

    def get_browse_action(self) -> QtGui.QAction:
        icon = QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton)
        browse_dir_action = QtGui.QAction(
            icon, "Browse", parent=self
        )
        # pylint: disable=no-member
        browse_dir_action.triggered.connect(self.browse_dir)  # type: ignore
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
    def drop_acceptable_data(self, mime_data: QtCore.QMimeData) -> bool:
        if not mime_data.hasUrls():
            return False
        urls = mime_data.urls()
        if len(urls) != 1:
            return False
        path = urls[0].path()
        return os.path.exists(path) and not os.path.isdir(path)

    def get_browse_action(self) -> QtGui.QAction:
        icon = QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton)
        browse_file_action = QtGui.QAction(
            icon, "Browse", parent=self
        )
        # pylint: disable=no-member
        browse_file_action.triggered.connect(self.browse_file)  # type: ignore
        return browse_file_action

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
            widget_metadata: Optional[WidgetMetadata] = None,
    ) -> None:
        super().__init__(widget_metadata=widget_metadata, parent=parent)
        widget_metadata = widget_metadata or {}
        self.filter = widget_metadata.get('filter')

    def browse_file(
            self,
            get_file_callback: Optional[
                typing.Callable[[], Optional[str]]
            ] = None
    ) -> None:
        def use_qt_file_dialog() -> Optional[str]:
            if self.filter is None:
                result = QtWidgets.QFileDialog.getOpenFileName(parent=self)
            else:
                result = QtWidgets.QFileDialog.getOpenFileName(
                    parent=self,
                    filter=self.filter
                )
            if result:
                return result[0]
            return None

        selection = (get_file_callback or use_qt_file_dialog)()
        if selection:
            data = selection
            self.data = data
            self.dataChanged.emit()


class DynamicForm(QtWidgets.QWidget):
    modelChanged = QtCore.Signal()

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._scroll = QtWidgets.QScrollArea(self)
        self._scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self._scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._scroll.setWidgetResizable(True)

        layout = QtWidgets.QFormLayout(self._scroll)
        layout.setRowWrapPolicy(layout.RowWrapPolicy.WrapLongRows)
        layout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.setFieldGrowthPolicy(
            layout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        self.widgets: Dict[str, EditDelegateWidget] = {}
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.model = models.ToolOptionsModel4()
        self._background = QtWidgets.QFrame(self)
        self._background.setLayout(layout)
        self.layout().addWidget(self._scroll)
        self.modelChanged.connect(self.update_widget)
        self._scroll.setWidget(self._background)
        self.setMinimumHeight(100)

    def create_editor(self, widget_name, data):
        widget_types: typing.Dict[str, typing.Type[EditDelegateWidget]] = {
            "FileSelect": FileSelectWidget,
            "DirectorySelect": DirectorySelectWidget,
            "ChoiceSelection": ComboWidget,
            "BooleanSelect": CheckBoxWidget,
            "TextInput": LineEditWidget,
        }
        return widget_types.get(widget_name)(self._background, data)

    def update_widget(self):
        self.widgets: Dict[str, EditDelegateWidget] = {}
        layout = self._background.layout()
        layout.setSpacing(2)
        while layout.rowCount():
            layout.removeRow(0)
        self.model: Optional[models.ToolOptionsModel4]
        for i in range(self.model.rowCount()):
            index = self.model.index(i)
            if not index.isValid():
                return
            serialized_json_data: str = \
                typing.cast(
                    str,
                    index.data(role=models.ToolOptionsModel4.JsonDataRole)
                )
            json_data = \
                typing.cast(WidgetMetadata, json.loads(serialized_json_data))
            widget = self.create_editor(json_data['widget_type'], json_data)
            widget.setAutoFillBackground(True)
            widget.data = json_data.get("value")
            self.widgets[json_data['label']] = widget

            # Checkboxes/BooleanSelect already have a label built into them
            layout.addRow(
                "" if json_data['widget_type'] == 'BooleanSelect'
                else json_data['label'],
                widget
            )

    # pylint: disable=invalid-name
    def setModel(self, model: models.ToolOptionsModel4):
        self.model = model
        self.modelChanged.emit()

    def update_model(self):
        for i in range(self.model.rowCount()):
            index = self.model.index(i)
            if not index.isValid():
                return
            model_data: AbsOutputOptionDataType = self.model.data(
                index,
                models.ToolOptionsModel4.DataRole
            )

            self.model.setData(index, self.widgets[model_data.label].data)

    def sizeHint(self) -> QtCore.QSize:
        return self._scroll.sizeHint()


class Workspace(QtWidgets.QWidget):
    settingsWidget: QtWidgets.QWidget
    selectedWorkflowView: QtWidgets.QLineEdit
    descriptionView: QtWidgets.QTextBrowser

    def __init__(
            self,
            model: models.WorkflowListModel,
            parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.tool_mapper = QtWidgets.QDataWidgetMapper(self)
        self.model = model
        self.tool_mapper.setModel(self.model)


def get_workspace(
        workflow_model: models.WorkflowListModel,
        parent: QtWidgets.QWidget = None
) -> Workspace:
    with as_file(
            resources.files(ui).joinpath("workspace.ui")
    ) as ui_file:
        widget = \
            typing.cast(
                Workspace,
                ui_loader.load_ui(
                    str(ui_file),
                    Workspace(workflow_model, parent)
                ),
            )

    widget.tool_mapper.addMapping(widget.selectedWorkflowView, 0)
    widget.tool_mapper.addMapping(widget.descriptionView, 1, b"plainText")
    return widget
