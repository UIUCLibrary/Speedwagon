"""Specialize widgets."""
import abc
import json
import os.path
import typing
from typing import \
    Union, \
    Optional, \
    Dict, \
    Any, \
    TypedDict, \
    List

try:
    from typing import TypeAlias
except ImportError:
    from typing_extensions import TypeAlias

try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired


from PySide6 import QtWidgets, QtCore, QtGui
from speedwagon.frontend.qtwidgets import models, ui_loader, ui
from speedwagon.workflow import AbsOutputOptionDataType
try:  # pragma: no cover
    from importlib.resources import as_file
    from importlib import resources
except ImportError:  # pragma: no cover
    import importlib_resources as resources  # type: ignore
    from importlib_resources import as_file


__all__ = [
    'get_workspace'
]


UseDataType: TypeAlias = Union[str, bool, None]


class WidgetMetadata(TypedDict):
    label: str
    widget_type: str
    filter: NotRequired[str]
    selections: NotRequired[List[str]]
    placeholder_text: NotRequired[str]
    value: NotRequired[UseDataType]


class EditDelegateWidget(QtWidgets.QWidget):
    """EditDelegateWidget base class.

    Note:
        When https://bugreports.qt.io/browse/PYSIDE-1434 is resolved, this
        should be made into an abstract base class.
    """
    editingFinished = QtCore.Signal()
    dataChanged = QtCore.Signal()

    def __init__(
            self,
            widget_metadata: WidgetMetadata,
            parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent=parent)
        self._data: Optional[Any] = None
        self.widget_metadata = widget_metadata or {}
        inner_layout = QtWidgets.QHBoxLayout()
        inner_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(inner_layout)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

    @property
    def data(self) -> UseDataType:
        return self._data

    @data.setter
    @abc.abstractmethod
    def data(self, value: UseDataType) -> None:
        """Set the value based on the widget used."""


class LineEditWidget(EditDelegateWidget):

    def __init__(
            self,
            widget_metadata: WidgetMetadata,
            parent: Optional[QtWidgets.QWidget] = None,
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

    @EditDelegateWidget.data.setter  # type: ignore[attr-defined]
    def data(self, value: str) -> None:
        self._data = value
        self.text_box.setText(value)


class CheckBoxWidget(EditDelegateWidget):

    def __init__(
            self,
            widget_metadata: WidgetMetadata,
            parent: Optional[QtWidgets.QWidget] = None,
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

    @EditDelegateWidget.data.setter  # type: ignore[attr-defined]
    def data(self, value: bool) -> None:
        self._data = value
        if value:
            self.check_box.setCheckState(QtCore.Qt.CheckState.Checked)
        else:
            self.check_box.setCheckState(QtCore.Qt.CheckState.Unchecked)


class ComboWidget(EditDelegateWidget):
    def __init__(
            self,
            widget_metadata: WidgetMetadata,
            parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(widget_metadata=widget_metadata, parent=parent)
        self.combo_box = QtWidgets.QComboBox(self)
        place_holder_text = widget_metadata.get("placeholder_text")

        if place_holder_text is not None:
            self.combo_box.setPlaceholderText(place_holder_text)

        model = QtCore.QStringListModel(widget_metadata.get('selections', []))
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

    @EditDelegateWidget.data.setter  # type: ignore[attr-defined]
    def data(self, value: Optional[str]) -> None:
        self._data = value

        self._update_combo_box_selected(value, self.combo_box)

    @staticmethod
    def _update_combo_box_selected(
            expected_value: Optional[str],
            combo_box: QtWidgets.QComboBox
    ) -> None:
        model = combo_box.model()
        for i in range(model.rowCount()):
            index = model.index(i, 0)
            if index.data() == expected_value:
                combo_box.setCurrentIndex(index.row())
                break

    def get_selections(self) -> List[str]:
        model = self.combo_box.model()
        selections = []
        for i in range(model.rowCount()):
            index = model.index(i)
            selections.append(model.data(index))
        return selections


class FileSystemItemSelectWidget(EditDelegateWidget):

    def __init__(
            self,
            widget_metadata: WidgetMetadata,
            parent: Optional[QtWidgets.QWidget] = None,
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

    @EditDelegateWidget.data.setter  # type: ignore[attr-defined]
    def data(self, value: str) -> None:
        self._data = value
        self.edit.setText(value)

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
        return urls[0].toLocalFile()

    @abc.abstractmethod
    def drop_acceptable_data(self, param) -> bool:
        """check if dropped item is accessible"""


class DirectorySelectWidget(FileSystemItemSelectWidget):
    def drop_acceptable_data(self, mime_data: QtCore.QMimeData) -> bool:
        if not mime_data.hasUrls():
            return False
        urls = mime_data.urls()
        if len(urls) != 1:
            return False
        path = urls[0].toLocalFile()
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

        selection: Optional[str] = \
            (get_file_callback or default_use_qt_dialog)()

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
        path = urls[0].toLocalFile()
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
            widget_metadata: WidgetMetadata,
            parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(widget_metadata=widget_metadata, parent=parent)
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


class InnerForm(QtWidgets.QWidget):
    modelChanged = QtCore.Signal()

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QtWidgets.QFormLayout(self)
        layout.setRowWrapPolicy(layout.RowWrapPolicy.WrapLongRows)
        layout.setFieldGrowthPolicy(
            layout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        self.setLayout(layout)
        self.model = models.ToolOptionsModel4()
        self.modelChanged.connect(self.update_widget)
        self.widgets: Dict[str, EditDelegateWidget] = {}

    def create_editor(
            self,
            widget_name: str,
            data: WidgetMetadata
    ) -> EditDelegateWidget:
        widget_types: typing.Dict[str, typing.Type[EditDelegateWidget]] = {
            "FileSelect": FileSelectWidget,
            "DirectorySelect": DirectorySelectWidget,
            "ChoiceSelection": ComboWidget,
            "BooleanSelect": CheckBoxWidget,
            "TextInput": LineEditWidget,
        }
        return widget_types[widget_name](
            widget_metadata=data,
            parent=self
        )

    def update_widget(self) -> None:
        self.widgets = {}
        layout = typing.cast(QtWidgets.QFormLayout, self.layout())
        layout.setContentsMargins(15, 0, 0, 0)
        layout.setVerticalSpacing(1)
        while layout.rowCount():
            layout.removeRow(0)
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
            widget = self.create_editor(
                widget_name=json_data['widget_type'],
                data=json_data
            )
            widget.data = json_data.get("value")
            self.widgets[json_data['label']] = widget

            # Checkboxes/BooleanSelect already have a label built into them
            label = QtWidgets.QLabel(
                "" if json_data['widget_type'] == 'BooleanSelect'
                else json_data['label']
            )
            label.setFixedWidth(150)
            label.setWordWrap(True)
            layout.addRow(label, widget)

        self.update()

    def update_model(self) -> None:
        for i in range(self.model.rowCount()):
            index = self.model.index(i)
            if not index.isValid():
                return
            model_data = typing.cast(
                AbsOutputOptionDataType,
                self.model.data(
                    index,
                    models.ToolOptionsModel4.DataRole
                )
            )

            self.model.setData(index, self.widgets[model_data.label].data)

    @staticmethod
    def iter_row_rect(layout: QtWidgets.QFormLayout, device):
        last_height = 0
        for row in range(layout.rowCount()):
            label = \
                layout.itemAt(row, QtWidgets.QFormLayout.ItemRole.LabelRole)
            widget = \
                layout.itemAt(row, QtWidgets.QFormLayout.ItemRole.FieldRole)

            y_axis = label.geometry().y()
            bottom_point = widget.geometry().y() + widget.geometry().height()
            total_height = bottom_point - y_axis
            rect = QtCore.QRect(0, y_axis, device.width(), total_height)
            yield rect
            last_height = rect.height() + rect.y()

        default_row_height = 25
        for y_pos in range(last_height, device.height(), default_row_height):
            yield QtCore.QRect(0, y_pos, device.width(), default_row_height)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        options = QtWidgets.QStyleOptionViewItem()
        painter = QtWidgets.QStylePainter(self)
        for i, rect in enumerate(
                self.iter_row_rect(
                    typing.cast(QtWidgets.QFormLayout, self.layout()),
                    painter.device()
                )
        ):
            if i % 2 == 0:
                options.features = options.ViewItemFeature.Alternate  # type: ignore  # noqa:E501
            else:
                options.features = options.ViewItemFeature.None_  # type: ignore  # noqa:E501
            if self.isEnabled():
                options.palette.setCurrentColorGroup(  # type: ignore  # noqa
                    QtGui.QPalette.ColorGroup.Normal
                )
            else:
                options.palette.setCurrentColorGroup(  # type: ignore  # noqa
                    QtGui.QPalette.ColorGroup.Disabled
                )
            options.rect = rect  # type: ignore
            painter.drawPrimitive(
                QtWidgets.QStyle.PrimitiveElement.PE_PanelItemViewRow,
                options
            )
        painter.end()


class DynamicForm(QtWidgets.QScrollArea):
    modelChanged = QtCore.Signal()

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )

        self.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setWidgetResizable(True)

        layout = QtWidgets.QFormLayout(self)
        layout.setRowWrapPolicy(layout.RowWrapPolicy.WrapLongRows)
        layout.setFieldGrowthPolicy(
            layout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        self.widgets: Dict[str, EditDelegateWidget] = {}
        self.setLayout(QtWidgets.QVBoxLayout())
        self._background = InnerForm(self)
        self.modelChanged.connect(self._background.modelChanged)
        self.setWidget(self._background)
        self.ensurePolished()

    def create_editor(
            self,
            widget_name: str,
            data: WidgetMetadata
    ) -> EditDelegateWidget:
        return self._background.create_editor(widget_name, data)

    # pylint: disable=invalid-name
    def set_model(self, model: models.ToolOptionsModel4) -> None:
        self._background.model = model
        self.modelChanged.emit()

    def update_model(self) -> None:
        self._background.update_model()

    def update_widget(self):
        self._background.update_widget()

    @property
    def model(self):
        return self._background.model


class Workspace(QtWidgets.QWidget):
    settingsWidget: QtWidgets.QWidget
    selectedWorkflowView: QtWidgets.QLineEdit
    descriptionView: QtWidgets.QTextBrowser
    settings_form: DynamicForm

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
        parent: Optional[QtWidgets.QWidget] = None
) -> Workspace:
    """Get Workspace widget."""
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
    widget.settings_form = DynamicForm(widget)
    widget.layout().replaceWidget(
        widget.settingsWidget,
        widget.settings_form
    )
    widget.settings_form.setMinimumHeight(100)
    return widget
