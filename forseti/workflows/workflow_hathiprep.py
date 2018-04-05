import os
import typing

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt

import forseti.tasks
from forseti.job import Workflow
from forseti.tools import options

from uiucprescon.packager import PackageFactory
import uiucprescon.packager.packages
from uiucprescon.packager.packages import collection
from collections import namedtuple

ModelField = namedtuple("ModelField", ("column_header", "data_entry", "editable"))


class FileSelectionDelegate2(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent):

        # self.model = parent.model
        super().__init__(parent)
        self.choices = []
        self.acceptable_extensions = [".jp2", ".tif"]

    def createEditor(self, parent, QStyleOptionViewItem, QModelIndex):
        selection = QtWidgets.QComboBox(parent)
        object_ = QModelIndex.data(role=Qt.UserRole)
        files = []
        for i in object_:
            instance = i.instantiations[collection.InstantiationTypes.ACCESS]
            files += instance.files

        for file in files:
            selection.addItem(file)
        return selection

    def setEditorData(self, editor: QtWidgets.QComboBox, index):
        print("SEt")
        column = index.column()
        row = index.row()
        # package_object = self.model._packages[row]
        # item_names = []
        # for item in package_object:
        #     for file_name in item.instantiations["access"].files:
        #         basename = os.path.basename(file_name)
        #         base, ext = os.path.splitext(basename)
        #         if ext.lower() in self.acceptable_extensions:
        #             item_names.append(basename)
        #     # item_names.append(item.metadata["item_name"])
        # self.choices = item_names
        # editor.addItems([str(item) for item in self.choices])
        super().setEditorData(editor, index)

    @staticmethod
    def get_files(path):
        for files in filter(lambda x: x.is_file(), os.scandir(path)):
            yield files.name



class PackagesModel(QtCore.QAbstractTableModel):
    fields = [

        ModelField(column_header="Object",
                   data_entry=collection.Metadata.ID,
                   editable=False),


        ModelField(column_header="Location",
                   data_entry=collection.Metadata.PATH,
                   editable=False),

        ModelField(column_header="Title Page",
                   data_entry=collection.Metadata.TITLE_PAGE,
                   editable=True),

    ]

    def __init__(self, packages: list, parent=None):
        super().__init__(parent)
        self._packages = packages

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self.fields)

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self._packages)

    def headerData(self, index, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            try:
                return self.fields[index].column_header
            except IndexError:
                return ""
        else:
            return super().headerData(index, orientation, role)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        row = index.row()
        column = index.column()

        if role == QtCore.Qt.DisplayRole:
            field = self.fields[column]
            try:
                return self._packages[row].metadata[field.data_entry]
            except KeyError:
                return ""

        if role == QtCore.Qt.UserRole:
            return self._packages[row]

        return QtCore.QVariant()

    def flags(self, index):
        column = index.column()
        if self.fields[column].editable:
            return Qt.ItemIsEditable | Qt.ItemIsEnabled
        return super().flags(index)


class PackageBrowser(QtWidgets.QDialog):
    def __init__(self, packages, parent,
                 flags: typing.Union[
                     Qt.WindowFlags, Qt.WindowType] = Qt.WindowFlags(),
                 *args, **kwargs):
        super().__init__(parent, flags, *args, **kwargs)
        self._parent = parent
        self._packages = packages
        self._model = PackagesModel(packages)
        self._layout = QtWidgets.QGridLayout(self)

        self.package_view = QtWidgets.QTreeView(self)
        self.package_view.setEditTriggers(QtWidgets.QTreeView.AllEditTriggers)
        self.package_view.setContentsMargins(0, 0, 0, 0)
        self.package_view.setModel(self._model)
        self.package_view.setItemDelegate(FileSelectionDelegate2(self))
        # self.package_view.setItemDelegateForColumn(1, QtWidgets.QPushButton("asdfasdf", self))
        # self.package_view.setItemDelegateForColumn(0, FileSelectionDelegate2(self))

        self._buttons = QtWidgets.QButtonGroup(parent=self)
        self.ok_button = QtWidgets.QPushButton("Ok")
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self._layout.addWidget(self.package_view, 0, 0, 1, 4)
        self._buttons.addButton(self.ok_button)
        self._buttons.addButton(self.cancel_button)
        self._layout.addWidget(self.ok_button, 1, 1)
        self._layout.addWidget(self.cancel_button, 1, 2)
        self._layout.setContentsMargins(0, 0, 0, 10)

        # TODO: set accept and cancel


class HathiPrepWorkflow(Workflow):
    name = "Hathi Prep"
    description = "Something goes here later"

    def user_options(self):
        return options.UserOptionCustomDataType("input",
                                                options.FolderData),

    def initial_task(
            self,
            task_builder: forseti.tasks.TaskBuilder,
            **user_args
    ) -> None:
        root = user_args['input']
        task_builder.add_subtask(FindPackagesTask(root))

    def discover_task_metadata(self, initial_results: typing.List[typing.Any],
                               **user_args) -> typing.List[dict]:
        # TODO: For each package, add information about the title page

        return []

    def get_additional_info(self, parent: QtWidgets.QWidget, options: dict,
                            initial_results: list) -> dict:
        # TODO: Generate a title page selection and return the user options

        root_dir = options['input']

        package_factory = PackageFactory(
            uiucprescon.packager.packages.HathiTiff())

        packages = [package for package in
                    package_factory.locate_packages(root_dir)]
        browser = PackageBrowser(packages, parent)
        browser.exec()

        return super().get_additional_info(parent, options, initial_results)


class FindPackagesTask(forseti.tasks.Subtask):

    def __init__(self, root) -> None:
        super().__init__()
        self._root = root

    def work(self) -> bool:
        self.log("Locating packages in {}".format(self._root))

        def find_dirs(item: os.DirEntry):

            if not item.is_dir():
                return False
            return True

        directories = []

        for directory in filter(find_dirs, os.scandir(self._root)):
            directories.append(directory.path)
            self.log(f"Located {directory.name}")
        self.set_results(directories)

        return True
