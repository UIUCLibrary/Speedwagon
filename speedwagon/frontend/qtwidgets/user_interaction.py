"""User interaction when using a QtWidget backend."""
from __future__ import annotations

import enum
import os.path
import threading
import typing
from typing import Dict, Any, Optional, List, Union, Type

from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import Qt
from uiucprescon.packager import Metadata

import speedwagon.exceptions
from speedwagon.frontend import interaction
from speedwagon.frontend.qtwidgets.dialog.title_page_selection import \
    PackageBrowser


if typing.TYPE_CHECKING:
    from uiucprescon.packager.packages import collection
    from speedwagon.job import Workflow


class QtWidgetFactory(interaction.UserRequestFactory):
    """Factory for generating Qt Widget."""

    def __init__(self, parent: Optional[QtWidgets.QWidget]) -> None:
        """Create a new QtWidgetFactory factory."""
        super().__init__()
        self.parent = parent

    def package_browser(self) -> interaction.AbstractPackageBrowser:
        """Generate widget for browsing packages."""
        return QtWidgetPackageBrowserWidget(self.parent)

    def confirm_removal(
            self
    ) -> interaction.AbstractConfirmFilesystemItemRemoval:
        """Generate widget for selecting which files or folders to remove."""
        return QtWidgetConfirmFileSystemRemoval(parent=self.parent)

    def package_title_page_selection(
            self
    ) -> interaction.AbstractPackageTitlePageSelection:
        """Generate widget for selecting title pages from a package."""

        return QtWidgetTitlePageSelection(parent=self.parent)


class ConfirmListModel(QtCore.QAbstractListModel):
    """Confirm list model to be used to select items."""

    itemsChanged = QtCore.Signal()

    def __init__(
            self,
            items: List[str] = None,
            parent: Optional[QtCore.QObject] = None
    ) -> None:
        """Create a new confirmation list model."""
        super().__init__(parent)
        self.items = items or []

    @property
    def items(self):
        """Get the items."""
        return self._items

    @items.setter
    def items(self, value):
        self._items = [{
                "name": i,
                "checked": Qt.Unchecked
            } for i in value
        ]
        self.itemsChanged.emit()

    def selected(self) -> List[str]:
        """Get items in the model that have been checked."""
        selected: List[str] = []
        for i in range(self.rowCount()):
            index = self.index(i)
            checked: QtCore.Qt.ItemDataRole = \
                self.data(index, Qt.CheckStateRole)

            if checked == Qt.Checked:
                selected.append(self.data(index, Qt.DisplayRole))
        return selected

    def rowCount(  # pylint: disable=invalid-name
            self,
            parent: Union[  # pylint: disable=unused-argument
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = None
    ) -> int:
        """Get the number of items."""
        return len(self._items)

    def data(
            self,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ],
            role: int = typing.cast(int, Qt.DisplayRole)
    ) -> Any:
        """Get data from the model."""
        if role == Qt.CheckStateRole:
            return int(
                self._items[index.row()].get("checked", QtCore.Qt.Unchecked)
            )
        if role == Qt.DisplayRole:
            return self._items[index.row()]['name']
        return None

    def setData(  # pylint: disable=invalid-name
            self,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ],
            value: Any,
            role: int = typing.cast(int, Qt.DisplayRole)
    ) -> bool:
        """Set model data."""
        if role == Qt.CheckStateRole:
            self._items[index.row()]['checked'] = value
            return True

        return super().setData(index, value, role)

    def flags(
            self,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]) -> QtCore.Qt.ItemFlags:
        """Set the flags needed."""
        if index.isValid():
            return super().flags(index) | Qt.ItemIsUserCheckable
        return super().flags(index)


class DetailsSorterProxyModel(QtCore.QSortFilterProxyModel):

    def lessThan(
            self,
            source_left: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ],
            source_right: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]) -> bool:
        # The first column uses a checkbox to state if selected or not
        if source_right.column() == 0:
            return source_left.data(
                typing.cast(int, QtCore.Qt.CheckStateRole)
            ) < source_right.data(
                typing.cast(int, QtCore.Qt.CheckStateRole)
            )
        return super().lessThan(source_left, source_right)


class ConfirmTableDetailsModel(QtCore.QTransposeProxyModel):
    class DetailsColumns(enum.IntEnum):
        SELECTED = 0
        NAME = 1
        LOCATION = 2

    def columnCount(
            self,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex] = ...
    ) -> int:
        return len(self.DetailsColumns)

    def index(
            self,
            row: int,
            column: int,
            parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> QtCore.QModelIndex:
        return self.createIndex(row, column)

    def mapToSource(
            self,
            proxy_index: QtCore.QModelIndex
    ) -> QtCore.QModelIndex:
        return self.sourceModel().index(
            proxy_index.row(),
            0
        ) if proxy_index.isValid() else QtCore.QModelIndex()

    def mapFromSource(
            self,
            source_index: QtCore.QModelIndex
    ) -> QtCore.QModelIndex:
        if source_index.isValid() and \
                0 <= source_index.row() < self.rowCount():
            return self.createIndex(
                self.sourceModel().index(source_index.row(), 0).row(),
                source_index.column(),
                source_index.internalPointer()
            )
        return QtCore.QModelIndex()

    def headerData(
            self,
            section: int,
            orientation: QtCore.Qt.Orientation,
            role: int
    ) -> str:
        if orientation == QtCore.Qt.Horizontal and \
                role == QtCore.Qt.DisplayRole:
            if section == self.DetailsColumns.NAME:
                return "Name"
            if section == self.DetailsColumns.LOCATION:
                return "Location"
            return ''
        return super().headerData(section, orientation, role)

    def rowCount(
            self,
            parent: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ] = ...) -> int:
        source_model = self.sourceModel()
        if not source_model:
            return 0
        return source_model.rowCount()

    def data(
            self,
            proxy_index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ],
            role: Optional[int] = None) -> Any:
        # Only the first column should be checkable
        if role == QtCore.Qt.CheckStateRole and proxy_index.column() != 0:
            return None
        if role == QtCore.Qt.DisplayRole:
            source_model = self.sourceModel()
            if source_model is not None:
                source_value: str = source_model.data(proxy_index, role)
                path = os.path.split(source_value)
                if proxy_index.column() == \
                        self.DetailsColumns.NAME.value:
                    return path[-1]
                if proxy_index.column() == \
                        self.DetailsColumns.LOCATION.value:
                    return path[0]
                if proxy_index.column() == 0:
                    return None

        return super().data(proxy_index, role)


class ConfirmDeleteDialog(QtWidgets.QDialog):
    """Confirm deletion dialog box."""

    def __init__(
            self,
            items: typing.List[str],
            parent: typing.Optional[QtWidgets.QWidget] = None,
            flags: typing.Union[
                Qt.WindowFlags, Qt.WindowType] = Qt.WindowFlags(),
    ) -> None:
        """Create a package browser dialog window."""
        super().__init__(parent, flags)
        layout = QtWidgets.QGridLayout(self)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.setWindowTitle("Delete the Following Items?")
        self.setMinimumWidth(500)
        self._make_connections()
        self.package_view = QtWidgets.QTableView(self)
        self.package_view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.package_view.setSelectionMode(
            QtWidgets.QTableView.SingleSelection
        )
        self.package_view.verticalHeader().setVisible(False)
        self.package_view.horizontalHeader().setStretchLastSection(True)

        self.select_all_button = QtWidgets.QPushButton(parent=self)
        self._connect_signals()
        self.select_all_button.setText("Select All")
        layout.addWidget(self.package_view)
        layout.addWidget(self.select_all_button)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self.nothing_found_label = QtWidgets.QLabel()

        self.nothing_found_label.setText(
            QtWidgetConfirmFileSystemRemoval.NO_FILES_LOCATED_MESSAGE
        )

        self.nothing_found_label.setVisible(False)

        package_layout = QtWidgets.QVBoxLayout()
        package_layout.setAlignment(Qt.AlignHCenter)
        package_layout.addWidget(self.nothing_found_label)

        self.package_view.setLayout(package_layout)

        self.model = ConfirmListModel(parent=self)
        self.model.itemsChanged.connect(self.update_buttons)
        self.model.itemsChanged.connect(self.update_view_label)
        self.model.items = sorted(items)
        self.model_table = ConfirmTableDetailsModel()
        self.model_table.setSourceModel(self.model)

        self._proxy_model = DetailsSorterProxyModel()
        self._proxy_model.setSourceModel(self.model_table)
        self.package_view.setSortingEnabled(True)
        self.package_view.sortByColumn(
            ConfirmTableDetailsModel.DetailsColumns.LOCATION,
            Qt.AscendingOrder
        )
        self.package_view.setModel(self._proxy_model)
        self.package_view.setColumnWidth(0, 50)
        header = self.package_view.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)

    def _connect_signals(self):
        """Connect any Qt signals.

        The only reason for this method is to localize the pylint false
        positive warnings.
        """
        # pylint: disable=no-member
        self.select_all_button.clicked.connect(self._select_all)

    def _select_all(self):
        self.model.beginResetModel()
        for i in range(self.model.rowCount()):
            index = self.model.index(i)
            self.model.setData(
                index,
                value=QtCore.Qt.Checked,
                role=QtCore.Qt.CheckStateRole
            )
        self.model.endResetModel()

    def update_view_label(self) -> None:
        """Update the label on top of the list view widget."""
        self.nothing_found_label.setVisible(len(self.model.items) <= 0)

    def update_buttons(self) -> None:
        """Update the dialog box button states."""
        ok_button = self.button_box.button(QtWidgets.QDialogButtonBox.Ok)
        if len(self.model.items) > 0:
            ok_button.setEnabled(True)
        else:
            ok_button.setEnabled(False)

    def _make_connections(self):
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
            self,
            options: dict,
            pretask_results: list
    ) -> Dict[str, Any]:
        """Request confirmation about which files should be removed."""
        return {
            "items": self.use_dialog_box(
                items=list(pretask_results[0].data),
                parent=self.parent
            )
        }

    @staticmethod
    def use_dialog_box(
            items: List[str],
            dialog_box: Optional[Type[ConfirmDeleteDialog]] = None,
            parent: Optional[QtWidgets.QWidget] = None
    ) -> List[str]:
        """Open dialog box and return with user response."""
        widget = dialog_box or QtWidgetConfirmFileSystemRemoval.dialog_box_type
        dialog = widget(
            items=items,
            parent=parent
        )
        results = dialog.exec()
        if results == QtWidgets.QDialog.Rejected:
            raise speedwagon.exceptions.JobCancelled()
        return dialog.data()


class QtWidgetPackageBrowserWidget(interaction.AbstractPackageBrowser):
    """QtWidget-based widget for selecting packages title pages."""

    def __init__(self, parent: Optional[QtWidgets.QWidget]) -> None:
        """Create a new package browser."""
        super().__init__()
        self.parent = parent

    def get_user_response(
            self,
            options: dict,
            pretask_results: list
    ) -> Dict[str, Any]:
        """Generate the dialog for selecting title pages."""
        return {
            "packages":
                self.get_data_with_dialog_box(
                    options['input'],
                    self.image_str_to_enum(options["Image File Type"])
                )

        }

    def get_data_with_dialog_box(
            self,
            root_dir: str,
            image_type: interaction.SupportedImagePackageFormats,
            dialog_box: typing.Type[PackageBrowser] = PackageBrowser
    ) -> List[collection.Package]:
        """Open a Qt dialog box for selecting package title pages."""
        browser = dialog_box(
            self.get_packages(root_dir, image_type),
            self.parent
        )
        browser.exec()
        return browser.data()


class QtWidgetTitlePageSelection(
    interaction.AbstractPackageTitlePageSelection
):
    """Qt widget for selection of a title page."""

    def __init__(self, parent: Optional[QtWidgets.QWidget]) -> None:
        """Create a title page selection widget."""
        super().__init__()
        self.parent = parent
        self.browser_widget = PackageBrowser

    def get_user_response(
            self, options: dict,
            pretask_results: list
    ) -> Dict[str, Any]:
        """Show the user the packages and ask for a title page."""
        results = pretask_results[0]
        packages = results.data

        title_pages: Dict[str, str] = {}
        extra_data: Dict[str, Dict[str, str]] = {}
        browser = self.browser_widget(packages, self.parent)
        browser.exec()

        if browser.result() != QtWidgets.QDialog.Accepted:
            raise speedwagon.exceptions.JobCancelled()
        data = browser.data()
        for package in data:
            bib_id = typing.cast(str, package.metadata[Metadata.ID])

            title_page = \
                typing.cast(str, package.metadata[Metadata.TITLE_PAGE])

            title_pages[bib_id] = title_page
        extra_data["title_pages"] = title_pages
        return extra_data


class QtRequestMoreInfo(QtCore.QObject):
    """Requesting info from user with a Qt widget."""

    request = QtCore.Signal(object, object, object, object)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget]) -> None:
        """Create a new qt object."""
        super().__init__(parent)
        self.results: Optional[Dict[str, typing.Any]] = None
        self._parent = parent
        self.exc: Optional[BaseException] = None
        self.request.connect(self.request_more_info)

    def request_more_info(
            self,
            user_is_interacting: threading.Condition,
            workflow: Workflow,
            options: Dict[str, typing.Any],
            pre_results: List[typing.Any]
    ) -> None:
        """Open new request widget."""
        with user_is_interacting:
            try:
                factory = QtWidgetFactory(self._parent)

                self.results = workflow.get_additional_info(
                    factory,
                    options=options,
                    pretask_results=pre_results
                )
            except speedwagon.exceptions.JobCancelled as exc:
                self.exc = exc
            except BaseException as exc:
                self.exc = exc
                raise
            finally:
                user_is_interacting.notify()
