"""Specialize widgets."""
from __future__ import annotations
import abc
import json
import os.path
import typing
from collections import defaultdict
from typing import (
    Union,
    Optional,
    Dict,
    Any,
    TypedDict,
    List,
    Iterable,
    TYPE_CHECKING,
)

import sys
# pylint: disable=wrong-import-position
from importlib import resources
from importlib.resources import as_file

from PySide6 import QtWidgets, QtCore, QtGui
from speedwagon.frontend.qtwidgets import ui_loader, ui
from speedwagon.workflow import AbsOutputOptionDataType, UserDataType
from speedwagon import Workflow, exceptions, config

from speedwagon.frontend.qtwidgets.models.workflows import AbsWorkflowList
from speedwagon.frontend.qtwidgets import models, logging_helpers


if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import NotRequired
    else:
        from typing_extensions import NotRequired
    import logging


__all__ = ["Workspace", "DynamicForm", "SelectWorkflow"]


class WidgetMetadata(TypedDict):
    label: str
    widget_type: str
    filter: NotRequired[str]
    selections: NotRequired[List[str]]
    placeholder_text: NotRequired[str]
    value: NotRequired[UserDataType]


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
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent=parent)
        self._data: Optional[Any] = None
        self.widget_metadata = widget_metadata or {}
        inner_layout = QtWidgets.QHBoxLayout()
        inner_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(inner_layout)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)

    @property
    def data(self) -> UserDataType:
        return self._data

    @data.setter
    @abc.abstractmethod
    def data(self, value: UserDataType) -> None:
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
            self.check_box.setText(widget_metadata["label"])
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

        model = QtCore.QStringListModel(widget_metadata.get("selections", []))
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
        expected_value: Optional[str], combo_box: QtWidgets.QComboBox
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
            index = model.index(i, column=0)
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
            QtWidgets.QLineEdit.ActionPosition.TrailingPosition,
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
        self, watched: QtCore.QObject, event: QtCore.QEvent
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
        """Check if dropped item is accessible."""


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
            QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton
        )
        browse_dir_action = QtGui.QAction(icon, "Browse", parent=self)
        # pylint: disable=no-member
        browse_dir_action.triggered.connect(self.browse_dir)  # type: ignore
        return browse_dir_action

    def browse_dir(
        self,
        get_file_callback: Optional[typing.Callable[[], Optional[str]]] = None,
    ) -> None:
        def default_use_qt_dialog() -> Optional[str]:
            return QtWidgets.QFileDialog.getExistingDirectory(parent=self)

        selection: Optional[str] = (
            get_file_callback or default_use_qt_dialog
        )()

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
            QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton
        )
        browse_file_action = QtGui.QAction(icon, "Browse", parent=self)
        # pylint: disable=no-member
        browse_file_action.triggered.connect(self.browse_file)  # type: ignore
        return browse_file_action

    def __init__(
        self,
        widget_metadata: WidgetMetadata,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(widget_metadata=widget_metadata, parent=parent)
        self.filter = widget_metadata.get("filter")

    def browse_file(
        self,
        get_file_callback: Optional[typing.Callable[[], Optional[str]]] = None,
    ) -> None:
        def use_qt_file_dialog() -> Optional[str]:
            if self.filter is None:
                result = QtWidgets.QFileDialog.getOpenFileName(parent=self)
            else:
                result = QtWidgets.QFileDialog.getOpenFileName(
                    parent=self, filter=self.filter
                )
            return result[0] if result else None

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
        self, widget_name: str, data: WidgetMetadata
    ) -> EditDelegateWidget:
        widget_types: typing.Dict[str, typing.Type[EditDelegateWidget]] = {
            "FileSelect": FileSelectWidget,
            "DirectorySelect": DirectorySelectWidget,
            "ChoiceSelection": ComboWidget,
            "BooleanSelect": CheckBoxWidget,
            "TextInput": LineEditWidget,
        }
        return widget_types[widget_name](widget_metadata=data, parent=self)

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
            serialized_json_data: str = typing.cast(
                str, index.data(role=models.ToolOptionsModel4.JsonDataRole)
            )
            json_data = typing.cast(
                WidgetMetadata, json.loads(serialized_json_data)
            )
            widget = self.create_editor(
                widget_name=json_data["widget_type"], data=json_data
            )
            widget.data = json_data.get("value")
            self.widgets[json_data["label"]] = widget

            # Checkboxes/BooleanSelect already have a label built into them
            label = QtWidgets.QLabel(
                ""
                if json_data["widget_type"] == "BooleanSelect"
                else json_data["label"]
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
                self.model.data(index, models.ToolOptionsModel4.DataRole),
            )

            self.model.setData(index, self.widgets[model_data.label].data)

    @staticmethod
    def iter_row_rect(
        layout: QtWidgets.QFormLayout, device: InnerForm
    ) -> Iterable[QtCore.QRect]:
        last_height = 0
        for row in range(layout.rowCount()):
            label = layout.itemAt(
                row, QtWidgets.QFormLayout.ItemRole.LabelRole
            )
            widget = layout.itemAt(
                row, QtWidgets.QFormLayout.ItemRole.FieldRole
            )

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
                typing.cast(InnerForm, painter.device()),
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
                QtWidgets.QStyle.PrimitiveElement.PE_PanelItemViewRow, options
            )
        painter.end()


class DynamicForm(QtWidgets.QScrollArea):
    """Dynamic form for entering job configuration."""

    modelChanged = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        """Create a new DynamicForm object."""
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
        self.issues: List[str] = []

    def update_issues(self) -> None:
        """Update issues."""
        self.issues.clear()
        self.update_model()
        rows = self._background.model.rowCount()
        for row in range(rows):
            index = self._background.model.index(row)
            data = typing.cast(
                AbsOutputOptionDataType,
                self._background.model.data(
                    index, self._background.model.DataRole
                ),
            )
            if data.required and (data.value is None or data.value == ""):
                self.issues.append(f" Required value {data.label} is missing.")

    def is_valid(self) -> bool:
        """Get validity of form."""
        self.update_issues()
        return len(self.issues) == 0

    def create_editor(
        self, widget_name: str, data: WidgetMetadata
    ) -> EditDelegateWidget:
        """Create editor."""
        return self._background.create_editor(widget_name, data)

    # pylint: disable=invalid-name
    def set_model(self, model: models.ToolOptionsModel4) -> None:
        """Set model used by the widget."""
        self._background.model = model
        self.modelChanged.emit()

    def update_model(self) -> None:
        """Update model."""
        self._background.update_model()

    def update_widget(self) -> None:
        """Update widget."""
        self._background.update_widget()

    @property
    def model(self) -> models.ToolOptionsModel4:
        """Get the model used by the widget."""
        return self._background.model

    def get_configuration(self) -> Dict[str, AbsOutputOptionDataType]:
        """Get the configuration as a dictionary."""
        self.update_model()

        def with_instance(
                model_data: List[AbsOutputOptionDataType]
        ) -> Dict[str, AbsOutputOptionDataType]:
            return {
                option.setting_name if option.setting_name else option.label:
                    option
                for option in model_data
            }
        return self._background.model.get_as(with_instance)


class Workspace(QtWidgets.QWidget):
    """Workspace widget.

    This widget contains the controls for a user to set up a new job.
    """

    settingsWidget: QtWidgets.QWidget
    workflow_name_value: QtWidgets.QLineEdit
    descriptionView: QtWidgets.QTextBrowser
    selectedWorkflowNameLabel: QtWidgets.QLabel
    workflow_description_value: QtWidgets.QTextBrowser
    settings_form: DynamicForm

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        """Create Workspace widget."""
        super().__init__(parent)
        with as_file(resources.files(ui).joinpath("workspace.ui")) as ui_file:
            ui_loader.load_ui(str(ui_file), self)
        self.app_settings_lookup_strategy = config.StandardConfig()

    def set_workflow(self, workflow_klass: typing.Type[Workflow]) -> None:
        """Set current workflow."""
        if workflow_klass.name:
            self.workflow_name_value.setText(workflow_klass.name)
        try:
            settings = self.app_settings_lookup_strategy.settings()
            new_workflow = workflow_klass(
                global_settings=settings.get("GLOBAL", {})
            )
            config_backend = config.get_config_backend()
            config_backend.workflow = new_workflow
            new_workflow.set_options_backend(config_backend)
            if new_workflow.description:
                self.workflow_description_value.setText(
                    new_workflow.description
                )
            self.settings_form.set_model(
                models.ToolOptionsModel4(new_workflow.job_options())
            )
        except exceptions.MissingConfiguration as exc:
            self.workflow_description_value.setHtml(
                f"<b>Workflow unavailable.</b><p><b>Reason: </b>{exc}</p>"
            )
            self.settings_form.set_model(models.ToolOptionsModel4())

    def is_valid(self) -> bool:
        """Check if the workflow configured is valid."""
        return self.settings_form.is_valid()

    def _get_configuration(self) -> Dict[str, AbsOutputOptionDataType]:
        return self.settings_form.get_configuration()

    @property
    def workflow_name(self) -> str:
        """Get workflow name."""
        return self._get_workflow_name()

    def _get_workflow_name(self) -> str:
        return self.workflow_name_value.text()

    @property
    def workflow_description(self) -> str:
        """Get workflow description."""
        return self._get_workflow_description()

    def _get_workflow_description(self) -> str:
        return self.workflow_description_value.toPlainText()

    name = QtCore.Property(str, _get_workflow_name)
    description = QtCore.Property(str, _get_workflow_description)
    configuration = QtCore.Property(object, _get_configuration)


class SelectWorkflow(QtWidgets.QWidget):
    """Workflow selection widget.

    This is based on a QListView.
    """

    workflowSelectionView: QtWidgets.QListView
    workflow_selected = QtCore.Signal(object)
    selected_index_changed = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        """Create a new SelectWorkflow object."""
        super().__init__(parent)
        with as_file(
            resources.files("speedwagon.frontend.qtwidgets.ui").joinpath(
                "select_workflow_widget.ui"
            )
        ) as ui_file:
            ui_loader.load_ui(str(ui_file), self)
        self.workflowSelectionView.setModel(models.WorkflowList())

    @property
    def model(self) -> QtCore.QAbstractItemModel:
        """Get the model used by the widget."""
        return self.workflowSelectionView.model()

    @model.setter
    def model(self, value: AbsWorkflowList) -> None:
        # pass
        self.workflowSelectionView.setModel(value)
        selection_model = self.workflowSelectionView.selectionModel()
        selection_model.currentChanged.connect(  # type: ignore
            self._update_tool_selected
        )

    def _update_tool_selected(
        self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex
    ) -> None:
        item = typing.cast(
            typing.Type[Workflow],
            self.model.data(
                current, role=typing.cast(int, models.WorkflowClassRole)
            ),
        )
        self.selected_index_changed.emit(current)
        self.workflow_selected.emit(item)

    def add_workflow(self, workflow_klass: typing.Type[Workflow]) -> None:
        """Add workflow to list."""
        new_row = self.model.rowCount()
        self.model.insertRow(new_row)
        self.model.setData(self.model.index(new_row, 0), workflow_klass)

    def set_current_by_name(self, workflow_name: str) -> None:
        """Set current workflow by workflow name."""
        rows = self.model.rowCount()
        for row_id in range(rows):
            workflow_index = self.model.index(row_id, 0)
            name = workflow_index.data()
            if name == workflow_name:
                self.workflowSelectionView.setCurrentIndex(workflow_index)
                self.workflow_selected.emit(
                    self.model.data(workflow_index, models.WorkflowClassRole)
                )
                break
        else:
            raise ValueError(f"{workflow_name} not loaded in model")

    def get_current_workflow_type(self) -> Optional[typing.Type[Workflow]]:
        """Get current workflow type."""
        return typing.cast(
            typing.Type[Workflow],
            self.model.data(
                self.workflowSelectionView.currentIndex(),
                role=typing.cast(int, models.WorkflowClassRole),
            ),
        )

    @property
    def workflows(self) -> Dict[str, typing.Type[Workflow]]:
        """Get loaded workflows."""
        loaded_workflows = {}
        for row_id in range(self.model.rowCount()):
            index = self.model.index(row_id, 0)
            workflow_name = typing.cast(
                str, self.model.data(index, QtCore.Qt.ItemDataRole.DisplayRole)
            )

            loaded_workflows[workflow_name] = typing.cast(
                typing.Type[Workflow],
                self.model.data(index, QtCore.Qt.ItemDataRole.UserRole),
            )

        return loaded_workflows


class PluginConfig(QtWidgets.QWidget):
    changes_made = QtCore.Signal()
    plugin_list_view: QtWidgets.QListView

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        with as_file(
            resources.files(ui).joinpath("plugin_settings.ui")
        ) as ui_file:
            ui_loader.load_ui(str(ui_file), self)

        self.model = models.PluginActivationModel()
        self.model.dataChanged.connect(self.changes_made)
        self.plugin_list_view.setModel(self.model)

    @property
    def modified(self) -> bool:
        return self.model.data_modified

    def enabled_plugins(self) -> Dict[str, List[str]]:
        active_plugins: Dict[str, List[str]] = defaultdict(list)
        for i in range(self.model.rowCount()):
            checked = typing.cast(
                QtCore.Qt.ItemDataRole,
                self.model.data(
                    self.model.index(i), QtCore.Qt.ItemDataRole.CheckStateRole
                ),
            )

            if checked == QtCore.Qt.CheckState.Checked:
                source = typing.cast(
                    str,
                    self.model.data(
                        self.model.index(i), self.model.ModuleRole
                    ),
                )
                plugin_name = typing.cast(
                    str,
                    self.model.data(
                        self.model.index(i), QtCore.Qt.ItemDataRole.DisplayRole
                    ),
                )
                active_plugins[source].append(plugin_name)
        return dict(active_plugins)


class WorkflowSettingsEditorUI(QtWidgets.QWidget):
    workflow_settings_view: QtWidgets.QTreeView

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        with as_file(
            resources.files(ui).joinpath("tab_workflow_options.ui")
        ) as ui_file:
            ui_loader.load_ui(str(ui_file), self)


class WorkflowSettingsEditor(WorkflowSettingsEditorUI):
    _model: QtCore.QAbstractItemModel
    data_changed = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.model = models.WorkflowSettingsModel()

    @property
    def model(self) -> QtCore.QAbstractItemModel:
        return self._model

    @model.setter
    def model(self, value: QtCore.QAbstractItemModel) -> None:
        self._model = value
        self.workflow_settings_view.setModel(self._model)
        self.model.dataChanged.connect(self.data_changed)


class ToolConsole(QtWidgets.QWidget):
    """Logging console."""

    _console: QtWidgets.QTextBrowser

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        """Create a new tool console object.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)

        self.log_handler = logging_helpers.QtSignalLogHandler(self)
        if self.log_handler.signals is None:
            raise RuntimeError("attach_logger failed to connect signals")
        self.log_handler.signals.messageSent.connect(self.add_message)

        self.log_formatter = logging_helpers.ConsoleFormatter()
        self.log_handler.setFormatter(self.log_formatter)

        with as_file(
                resources.files(ui).joinpath("console.ui")
        ) as ui_file:
            ui_loader.load_ui(str(ui_file), self)
        #
        # #  Use a monospaced font based on what's on system running
        monospaced_font = QtGui.QFontDatabase.systemFont(
            QtGui.QFontDatabase.SystemFont.FixedFont
        )

        self._log = QtGui.QTextDocument()
        self._log.setDefaultFont(monospaced_font)
        # pylint: disable=no-member
        self._log.contentsChanged.connect(self._follow_text)
        self._console.setDocument(self._log)
        self._console.setFont(monospaced_font)

        self._attached_logger: typing.Optional[logging.Logger] = None
        self.cursor: QtGui.QTextCursor = QtGui.QTextCursor(self._log)

    def _follow_text(self) -> None:
        cursor = QtGui.QTextCursor(self._log)
        cursor.movePosition(cursor.MoveOperation.End)
        self._console.setTextCursor(cursor)

    @QtCore.Slot(str)
    def add_message(
            self,
            message: str,
    ) -> None:
        """Add message to console.

        Args:
            message: message text.

        """
        self.cursor.beginEditBlock()
        self.cursor.insertHtml(message)
        self.cursor.endEditBlock()

    @property
    def text(self) -> str:
        """Get the complete text in the console."""
        return self._log.toPlainText()

    def attach_logger(self, logger: logging.Logger) -> None:
        """Attach Python logger."""
        logger.addHandler(self.log_handler)
        self._attached_logger = logger

    def detach_logger(self) -> None:
        """Detach Python logger."""
        if self._attached_logger is not None:
            self.log_handler.flush()
            self._attached_logger.removeHandler(self.log_handler)
            self._attached_logger = None
