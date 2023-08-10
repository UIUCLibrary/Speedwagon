"""Selection of title page widget."""

import os
import typing
from typing import NamedTuple, Any, Union

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt
from uiucprescon.packager.packages import collection

DEFAULT_WINDOW_FLAGS = Qt.WindowType(0)


class ModelField(NamedTuple):
    """Model field."""

    column_header: str
    data_entry: Any
    editable: bool


class FileSelectDelegate(QtWidgets.QStyledItemDelegate):
    """File selection delegate widget."""

    def createEditor(  # pylint: disable=C0103,W0613
        self,
        parent: QtWidgets.QWidget,
        item: QtWidgets.QStyleOptionViewItem,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
    ) -> QtWidgets.QWidget:
        """Create editor widget."""
        return QtWidgets.QComboBox(parent)

    def setEditorData(  # pylint: disable=C0103,W0613
        self,
        editor: QtCore.QObject,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
    ) -> None:
        """Set editor data."""
        object_record: collection.PackageObject = index.data(
            role=typing.cast(int, Qt.ItemDataRole.UserRole)
        )

        try:
            title_page = object_record.component_metadata[
                collection.Metadata.TITLE_PAGE
            ]
        except KeyError:
            title_page = ""

        files: typing.List[str] = []

        for i in object_record:
            for instance in i.instantiations.values():
                files += [os.path.basename(f) for f in instance.files]
        editor = typing.cast(QtWidgets.QComboBox, editor)
        for i, file in enumerate(files):
            editor.addItem(file)
            if title_page == file:
                editor.setCurrentIndex(i)

    def setModelData(  # pylint: disable=C0103
        self,
        widget: QtWidgets.QWidget,
        model: QtCore.QAbstractItemModel,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
    ) -> None:
        """Set model data."""
        record: collection.PackageObject = model.data(
            index, role=typing.cast(int, Qt.ItemDataRole.UserRole)
        )
        widget = typing.cast(QtWidgets.QComboBox, widget)
        record.component_metadata[
            collection.Metadata.TITLE_PAGE
        ] = widget.currentText()

        model.setData(
            index, record, role=typing.cast(int, Qt.ItemDataRole.UserRole)
        )


class PackagesModel(QtCore.QAbstractTableModel):
    """Model for holding title page information."""

    fields = [
        ModelField(
            column_header="Object",
            data_entry=collection.Metadata.ID,
            editable=False,
        ),
        ModelField(
            column_header="Title Page",
            data_entry=collection.Metadata.TITLE_PAGE,
            editable=True,
        ),
        ModelField(
            column_header="Location",
            data_entry=collection.Metadata.PATH,
            editable=False,
        ),
    ]

    def __init__(
        self,
        packages: typing.List[collection.Package],
        parent: typing.Optional[QtWidgets.QWidget] = None,
    ) -> None:
        """Create a new package model."""
        super().__init__(parent)
        self._packages = packages

    def columnCount(  # pylint: disable=C0103,W0613
        self,
        *args,
        parent: typing.Optional[
            Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ] = None,
        **kwargs,
    ) -> int:
        """Get the number of fields in model."""
        return len(self.fields)

    def rowCount(  # pylint: disable=C0103,W0613
        self,
        *args,
        parent: typing.Optional[
            Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ] = None,
        **kwargs,
    ) -> int:
        """Get the number of packages in model."""
        return len(self._packages)

    def headerData(  # pylint: disable=C0103
        self,
        index: int,
        orientation: Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Union[str, QtCore.QObject]:
        """Get model header information."""
        if (
            role == QtCore.Qt.ItemDataRole.DisplayRole
            and orientation == QtCore.Qt.Orientation.Horizontal
        ):
            try:
                return self.fields[index].column_header
            except IndexError:
                return ""
        else:
            return super().headerData(index, orientation, role)

    def data(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        role=QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Get data at index."""
        row = index.row()
        column = index.column()

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            field = self.fields[column]
            try:
                return self._packages[row].metadata[field.data_entry]
            except KeyError:
                return ""

        if role == QtCore.Qt.ItemDataRole.UserRole:
            return self._packages[row]

        return None

    def results(self) -> typing.List[collection.Package]:
        """Get results."""
        return self._packages

    def flags(
        self, index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> Qt.ItemFlag:
        """Set flags for index."""
        column = index.column()
        if self.fields[column].editable:
            return typing.cast(
                Qt.ItemFlag,
                Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled,
            )
        return super().flags(index)


class PackageBrowser(QtWidgets.QDialog):
    """Browser dialog for selecting title page."""

    def __init__(
        self,
        packages: typing.List[collection.Package],
        parent: typing.Optional[QtWidgets.QWidget],
        flags: Qt.WindowType = DEFAULT_WINDOW_FLAGS,
    ) -> None:
        """Create a package browser dialog window."""
        super().__init__(parent, flags)
        self._parent = parent
        self._packages = packages
        self._model = PackagesModel(packages)

        self._layout = QtWidgets.QGridLayout(self)

        self.package_view = QtWidgets.QTreeView(self)
        self.package_view.setEditTriggers(
            QtWidgets.QTreeView.EditTrigger.AllEditTriggers
        )

        self.package_view.setContentsMargins(0, 0, 0, 0)
        self.package_view.setModel(self._model)

        # Index 1 in the view is the title page
        self.package_view.setItemDelegateForColumn(1, FileSelectDelegate(self))

        self._buttons = QtWidgets.QButtonGroup(parent=self)
        self.ok_button = QtWidgets.QPushButton("Done")

        # pylint: disable=no-member
        self.ok_button.clicked.connect(self.accept)  # type: ignore
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)  # type: ignore

        self._layout.addWidget(self.package_view, 0, 0, 1, 4)

        self._buttons.addButton(self.ok_button)
        self._buttons.addButton(self.cancel_button)
        self._layout.addWidget(self.ok_button, 1, 2)
        self._layout.addWidget(self.cancel_button, 1, 3)
        self._layout.setColumnStretch(2, 0)
        self._layout.setColumnStretch(3, 0)
        self._layout.setColumnStretch(1, 1)

        # Configure the window settings
        self.setWindowTitle("Title Page Selection")
        self.setMinimumWidth(640)
        self.setMinimumHeight(240)

    def data(self) -> typing.List[collection.Package]:
        """Get the results."""
        return self._model.results()
