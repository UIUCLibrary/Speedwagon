"""User interaction when using a QtWidget backend."""
from __future__ import annotations

import dataclasses
import threading
import typing
from typing import (
    Dict,
    Any,
    Optional,
    List,
    Union,
    Type,
    Generic,
    TypeVar,
    Callable,
    Sequence,
    Mapping
)

try:  # pragma: no cover
    from typing import TypedDict
except ImportError:  # pragma: no cover
    from typing_extensions import TypedDict

from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import Qt

import speedwagon.exceptions
from speedwagon.frontend import interaction
from speedwagon.frontend.qtwidgets.models.common import ItemTableModel
from speedwagon.frontend.qtwidgets.dialog.dialogs import TableEditDialog

if typing.TYPE_CHECKING:
    from speedwagon.job import Workflow

DEFAULT_WINDOW_FLAGS = Qt.WindowType(0)


class ConfirmItem(TypedDict):
    """Confirm plugin by name."""

    name: str
    checked: Qt.CheckState


T = TypeVar("T")
TableReportFormat = TypeVar("TableReportFormat")


class QtWidgetFactory(interaction.UserRequestFactory):
    """Factory for generating Qt Widget."""

    def __init__(self, parent: Optional[QtWidgets.QWidget]) -> None:
        """Create a new QtWidgetFactory factory."""
        super().__init__()
        self.parent = parent

    def confirm_removal(
        self,
    ) -> interaction.AbstractConfirmFilesystemItemRemoval:
        """Generate widget for selecting which files or folders to remove."""
        return QtWidgetConfirmFileSystemRemoval(parent=self.parent)

    def table_data_editor(
        self,
        enter_data: typing.Callable[
            [Mapping[str, object], list],
            List[Sequence[interaction.DataItem]]
        ],
        process_data: Callable[
            [List[Sequence[interaction.DataItem]]],
            TableReportFormat
        ]
    ) -> interaction.AbstractTableEditData:
        """Get table data editor."""
        def update_data(
            value: str,
            existing_row: Sequence[interaction.DataItem],
            index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ) -> Sequence[interaction.DataItem]:
            existing_row[index.column()].value = value
            return existing_row

        model_mapping_roles = QtModelMappingRoles[interaction.DataItem](
            is_editable_rule=lambda selection, index: selection[
                index.column()
            ].editable,
            display_role=lambda selection, index: selection[
                index.column()
            ].value,
            options_role=lambda selection, index: selection[
                index.column()
            ].possible_values,
            update_data=update_data
        )

        return QtWidgetTableEditWidget[
            interaction.DataItem,
            TableReportFormat
        ](
            enter_data=enter_data,
            process_data=process_data,
            model_mapping_roles=model_mapping_roles,
            parent=self.parent
        )


class ConfirmListModel(QtCore.QAbstractListModel):
    """Confirm list model to be used to select items."""

    itemsChanged = QtCore.Signal()

    def __init__(
        self,
        items: Optional[List[str]] = None,
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        """Create a new model."""
        super().__init__(parent)
        self._items: List[ConfirmItem] = []
        if items:
            self._set_items(items)

    def _set_items(self, item_names: List[str]) -> None:
        self._items = [
            {"name": i, "checked": Qt.CheckState.Checked} for i in item_names
        ]
        self.itemsChanged.emit()

    @property
    def items(self) -> List[str]:
        """Get the items."""
        keys = []
        for item in self._items:
            keys.append(item["name"])
        return keys

    @items.setter
    def items(self, value: List[str]) -> None:
        self._set_items(value)

    def selected(self) -> List[str]:
        """Get items in the model that have been checked."""
        selected: List[str] = []
        for i in range(self.rowCount()):
            index = self.index(i)
            checked: QtCore.Qt.ItemDataRole = self.data(
                index, Qt.ItemDataRole.CheckStateRole
            )

            if checked == Qt.CheckState.Checked:
                selected.append(
                    typing.cast(
                        str, self.data(index, Qt.ItemDataRole.DisplayRole)
                    )
                )
        return selected

    def rowCount(  # pylint: disable=invalid-name
        self,
        parent: Optional[  # pylint: disable=unused-argument
            Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ] = None,
    ) -> int:
        """Get the number of items."""
        return len(self._items)

    def data(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Get data from the model."""
        if role == Qt.ItemDataRole.CheckStateRole:
            return self._items[index.row()].get(
                "checked", Qt.CheckState.Unchecked
            )
        if role == Qt.ItemDataRole.DisplayRole:
            return self._items[index.row()]["name"]
        return None

    def setData(  # pylint: disable=invalid-name
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        value: Any,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> bool:
        """Set model data."""
        if role == Qt.ItemDataRole.CheckStateRole:
            self._items[index.row()]["checked"] = value
            return True

        return super().setData(index, value, role)

    def flags(
        self, index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.Qt.ItemFlag:
        """Set the flags needed."""
        if index.isValid():
            return super().flags(index) | Qt.ItemFlag.ItemIsUserCheckable
        return super().flags(index)


class ConfirmDeleteDialog(QtWidgets.QDialog):
    """Confirm deletion dialog box."""

    def __init__(
        self,
        items: typing.List[str],
        parent: typing.Optional[QtWidgets.QWidget] = None,
        flags: Qt.WindowType = DEFAULT_WINDOW_FLAGS,
    ) -> None:
        """Create a package browser dialog window."""
        super().__init__(parent, flags)
        layout = QtWidgets.QGridLayout(self)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.setWindowTitle("Delete the Following Items?")
        self.setFixedWidth(500)
        self._make_connections()
        self.package_view = QtWidgets.QListView(self)

        layout.addWidget(self.package_view)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self.nothing_found_label = QtWidgets.QLabel()

        self.nothing_found_label.setText(
            QtWidgetConfirmFileSystemRemoval.NO_FILES_LOCATED_MESSAGE
        )

        self.nothing_found_label.setVisible(False)

        package_layout = QtWidgets.QVBoxLayout()
        package_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        package_layout.addWidget(self.nothing_found_label)

        self.package_view.setLayout(package_layout)

        self.model = ConfirmListModel(parent=self)
        self.model.itemsChanged.connect(self.update_buttons)
        self.model.itemsChanged.connect(self.update_view_label)
        self.model.items = items
        self.package_view.setModel(self.model)

    def update_view_label(self) -> None:
        """Update the label on top of the list view widget."""
        self.nothing_found_label.setVisible(len(self.model.items) <= 0)

    def update_buttons(self) -> None:
        """Update the dialog box button states."""
        ok_button = self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )

        if len(self.model.items) > 0:
            ok_button.setEnabled(True)
        else:
            ok_button.setEnabled(False)

    def _make_connections(self) -> None:
        # pylint: disable=E1101
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def data(self) -> List[str]:
        """Get the files and folders selected by the user in the dialog box."""
        return self.model.selected()


class QtWidgetConfirmFileSystemRemoval(
    interaction.AbstractConfirmFilesystemItemRemoval
):
    """Qt Based widget for confirming items from the file system."""

    dialog_box_type = ConfirmDeleteDialog

    def __init__(self, parent: Optional[QtWidgets.QWidget]) -> None:
        """Create a new file system removal.

        Args:
            parent: Qt widget to use a parent.
        """
        super().__init__()
        self.parent = parent

    def get_user_response(
        self, options: Mapping[str, object], pretask_results: list
    ) -> Dict[str, Any]:
        """Request confirmation about which files should be removed."""
        return {
            "items": self.use_dialog_box(
                items=list(pretask_results[0].data), parent=self.parent
            )
        }

    @staticmethod
    def use_dialog_box(
        items: List[str],
        dialog_box: Optional[Type[ConfirmDeleteDialog]] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> List[str]:
        """Open dialog box and return with user response."""
        widget = dialog_box or QtWidgetConfirmFileSystemRemoval.dialog_box_type
        dialog = widget(items=items, parent=parent)
        results = dialog.exec()
        if results == QtWidgets.QDialog.DialogCode.Rejected:
            raise speedwagon.exceptions.JobCancelled()
        return dialog.data()


class TableSelectDialog(Generic[T, TableReportFormat]):
    """TableSelectDialog for displaying and editing tabular data."""

    def __init__(
            self,
            model_mapping_roles: QtModelMappingRoles,
            process_data: Callable[[List[Sequence[T]]], TableReportFormat],
            parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        """Create a new TableSelectDialog object."""
        super().__init__()
        self.parent = parent
        self.display_role = model_mapping_roles.display_role
        self.options_role = model_mapping_roles.options_role
        self.is_editable_rule = model_mapping_roles.is_editable_rule
        self.update_data = model_mapping_roles.update_data
        self.process_data = process_data

    def create_model(
            self,
            column_names: Sequence[str],
            selections: List[Sequence[T]]
    ) -> ItemTableModel:
        """Create a new Qt table model."""
        model = ItemTableModel[T, TableReportFormat](keys=column_names)
        model.display_role = self.display_role
        model.options_role = self.options_role
        model.is_editable_rule = self.is_editable_rule
        model.update_data = self.update_data

        model.process_results = self.process_data

        for row in selections:
            model.add_item(row)
        return model

    def get_dialog(
            self,
            column_names: Sequence[str],
            selections: List[Sequence[T]],
            title: str = ""
    ) -> TableEditDialog:
        """Get dialog box for working with editable tabular data."""
        model = self.create_model(column_names, selections=selections)
        dialog = TableEditDialog(parent=self.parent, model=model)
        dialog.setWindowTitle(title)
        return dialog


_RetVal = typing.TypeVar("_RetVal")


@dataclasses.dataclass
class QtModelMappingRoles(Generic[T]):
    """Map Qt Model roles to table view."""

    is_editable_rule: Callable[
        [
            Sequence[T],
            Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ],
        bool
    ]
    display_role: Callable[
        [
            Sequence[T],
            Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ],
        Optional[str]
    ]
    options_role: Callable[
        [
            Sequence[T],
            Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ],
        Sequence[str]
    ]
    update_data: Callable[
        [
            str,
            Sequence[T],
            Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ],
        Sequence[T]
    ]


class QtWidgetTableEditWidget(
    interaction.AbstractTableEditData,
    typing.Generic[T, _RetVal]
):
    """QtWidget-based widget for selecting packages title pages."""

    def __init__(
        self,
        enter_data: typing.Callable[
            [Mapping[str, object], list], List[Sequence[T]]
        ],
        process_data: typing.Callable[[List[Sequence[T]]], _RetVal],
        model_mapping_roles: QtModelMappingRoles,
        parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        """Create a new package browser."""
        super().__init__(enter_data, process_data)
        self.parent = parent
        self.item_browser = TableSelectDialog[T, _RetVal](
            process_data=process_data,
            model_mapping_roles=model_mapping_roles,
            parent=parent
        )

    def get_user_response(
        self, options: Mapping[str, Any], pretask_results: list
    ) -> Dict[str, Any]:
        """Generate the dialog for selecting title pages."""
        return self.get_data_with_dialog_box(
            self.gather_data(options, pretask_results)
        )

    def get_dialog_box(self, selections: List[Sequence[T]]) -> TableEditDialog:
        """Get dialog box object."""
        return self.item_browser.get_dialog(
            self.column_names,
            selections,
            title=self.title
        )

    def get_data_with_dialog_box(
            self,
            selections: List[Sequence[T]]
    ) -> Dict[str, Any]:
        """Open dialog box."""
        dialog = self.get_dialog_box(selections)
        dialog.exec()
        return dialog.data() or {}


class QtRequestMoreInfo(QtCore.QObject):
    """Requesting info from user with a Qt widget."""

    request = QtCore.Signal(object, object, object, object)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget]) -> None:
        """Create a new qt object."""
        super().__init__(parent)
        self.results: Optional[Mapping[str, typing.Any]] = None
        self._parent = parent
        self.exc: Optional[BaseException] = None
        self.request.connect(self.request_more_info)

    def request_more_info(
        self,
        user_is_interacting: threading.Condition,
        workflow: Workflow[Any],
        options: Mapping[str, object],
        pre_results: List[typing.Any],
    ) -> None:
        """Open new request widget."""
        with user_is_interacting:
            try:
                factory = QtWidgetFactory(self._parent)

                self.results = workflow.get_additional_info(
                    factory, options=options, pretask_results=pre_results
                )
            except speedwagon.exceptions.JobCancelled as exc:
                self.exc = exc
            except BaseException as exc:
                self.exc = exc
                raise
            finally:
                user_is_interacting.notify()
