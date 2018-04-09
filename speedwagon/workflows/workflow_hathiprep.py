import itertools
import os
import shutil
import typing

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt

import speedwagon.tasks
from speedwagon.job import Workflow, JobCancelled
from speedwagon.tools import options as tool_options

from uiucprescon.packager import PackageFactory
import uiucprescon.packager.packages
from uiucprescon.packager.packages import collection
from collections import namedtuple
from pyhathiprep import package_creater

ModelField = namedtuple("ModelField",
                        ("column_header", "data_entry", "editable"))


class FileSelectDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent):

        super().__init__(parent)

    def createEditor(self, parent, QStyleOptionViewItem,
                     index: QtCore.QModelIndex):
        selection = QtWidgets.QComboBox(parent)

        return selection

    def setEditorData(self, editor: QtWidgets.QComboBox,
                      index: QtCore.QModelIndex):

        object_record = index.data(role=Qt.UserRole)

        try:
            title_page = object_record.component_metadata[
                collection.Metadata.TITLE_PAGE]
        except KeyError as e:
            title_page = ""

        files: typing.List[str] = []

        for i in object_record:
            instance = i.instantiations[collection.InstantiationTypes.ACCESS]
            files += [os.path.basename(f) for f in instance.files]

        for i, file in enumerate(files):
            editor.addItem(file)
            if title_page == file:
                editor.setCurrentIndex(i)

    def setModelData(self, widget: QtWidgets.QComboBox,
                     model: QtCore.QAbstractItemModel,
                     index: QtCore.QModelIndex):
        record: collection.PackageObject = model.data(index, role=Qt.UserRole)
        record.component_metadata[
            collection.Metadata.TITLE_PAGE] = widget.currentText()

        model.setData(index, record, role=Qt.UserRole)


class PackagesModel(QtCore.QAbstractTableModel):
    fields = [

        ModelField(column_header="Object",
                   data_entry=collection.Metadata.ID,
                   editable=False),

        ModelField(column_header="Title Page",
                   data_entry=collection.Metadata.TITLE_PAGE,
                   editable=True),
        ModelField(column_header="Location",
                   data_entry=collection.Metadata.PATH,
                   editable=False),

    ]

    def __init__(self, packages: list, parent=None) -> None:
        super().__init__(parent)
        self._packages = packages

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self.fields)

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self._packages)

    def headerData(self, index, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole \
                and orientation == QtCore.Qt.Horizontal:
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

    def results(self) -> typing.List[collection.Package]:
        return self._packages

    def flags(self, index):
        column = index.column()
        if self.fields[column].editable:
            return Qt.ItemIsEditable | Qt.ItemIsEnabled
        return super().flags(index)


class PackageBrowser(QtWidgets.QDialog):
    def __init__(self, packages, parent,
                 flags: typing.Union[
                     Qt.WindowFlags, Qt.WindowType] = Qt.WindowFlags(),
                 *args, **kwargs) -> None:
        super().__init__(parent, flags, *args, **kwargs)
        self._parent = parent
        self._packages = packages
        self._model = PackagesModel(packages)

        self._layout = QtWidgets.QGridLayout(self)

        self.package_view = QtWidgets.QTreeView(self)
        self.package_view.setEditTriggers(QtWidgets.QTreeView.AllEditTriggers)
        self.package_view.setContentsMargins(0, 0, 0, 0)
        self.package_view.setModel(self._model)

        # Index 1 in the view is the title page
        self.package_view.setItemDelegateForColumn(1, FileSelectDelegate(self))

        self._buttons = QtWidgets.QButtonGroup(parent=self)
        self.ok_button = QtWidgets.QPushButton("Done")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

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
        return self._model.results()


class HathiPrepWorkflow(Workflow):
    name = "Hathi Prep"
    description = "Something goes here later"

    def user_options(self):
        return tool_options.UserOptionCustomDataType("input",
                                                     tool_options.FolderData),

    def initial_task(self, task_builder: speedwagon.tasks.TaskBuilder,
                     **user_args) -> None:
        root = user_args['input']
        task_builder.add_subtask(FindPackagesTask(root))

    def discover_task_metadata(self, initial_results: typing.List[typing.Any],
                               additional_data,
                               **user_args) -> typing.List[dict]:
        jobs = []
        for package in additional_data["packages"]:
            job = {
                "package_id": package.metadata[collection.Metadata.ID],
                "title_page": package.metadata[collection.Metadata.TITLE_PAGE],
                "source_path": package.metadata[collection.Metadata.PATH]
            }
            jobs.append(job)

        return jobs

    def create_new_task(self, task_builder: "speedwagon.tasks.TaskBuilder",
                        **job_args):
        title_page = job_args['title_page']
        source = job_args['source_path']
        package_id = job_args['package_id']

        task_builder.add_subtask(
            subtask=MakeYamlTask(package_id, source, title_page))

        task_builder.add_subtask(
            subtask=GenerateChecksumTask(package_id, source))

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
        result = browser.result()
        if result != browser.Accepted:
            raise JobCancelled()

        extra = {
            'packages': browser.data()
        }

        return extra

    @classmethod
    def generate_report(cls, results: typing.List[speedwagon.tasks.Result],
                        **user_args) -> typing.Optional[str]:
        results_sorted = sorted(results, key=lambda x: x.source.__name__)
        _result_grouped = itertools.groupby(results_sorted, lambda x: x.source)
        results_grouped = dict()

        for k, v in _result_grouped:
            results_grouped[k] = [i.data for i in v]

        objects = set()

        num_checksum_files = len(results_grouped[GenerateChecksumTask])
        num_yaml_files = len(results_grouped[MakeYamlTask])
        print("HGEr")

        for result in results_grouped[GenerateChecksumTask]:
            objects.add(result['package_id'])

        for result in results_grouped[MakeYamlTask]:
            objects.add(result['package_id'])

        objects_prepped_list = "\n  ".join(objects)

        process_report = f"HathiPrep Report:" \
                         f"\n" \
                         f"\nPrepped the following objects:" \
                         f"\n  {objects_prepped_list}" \
                         f"\n" \
                         f"\nTotal files generated: " \
                         f"\n  {num_checksum_files} checksum.md5 files" \
                         f"\n  {num_yaml_files} meta.yml files" \

        return process_report


class FindPackagesTask(speedwagon.tasks.Subtask):

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


class MakeYamlTask(speedwagon.tasks.Subtask):
    def __init__(self, package_id, source, title_page) -> None:
        super().__init__()

        self._source = source
        self._title_page = title_page
        self._package_id = package_id
        # self._working_dir = subtask_working_dir

    def work(self):
        meta_filename = "meta.yml"
        self.log("Generating meta.yml for {}".format(self._package_id))
        package_builder = package_creater.InplacePackage(self._source)
        package_builder.make_yaml(build_path=self.subtask_working_dir,
                                  title_page=self._title_page)

        meta_yml = os.path.join(self.subtask_working_dir, meta_filename)
        dest = os.path.join(self._source, meta_filename)
        successful = os.path.exists(meta_yml)
        assert successful

        shutil.move(meta_yml, dest)
        assert os.path.exists(dest)
        self.log("Added meta.yml to {}".format(self._source))

        self.set_results(
            {
                "source": self._source,
                "meta.yml": dest,
                "package_id": self._package_id
            }
        )

        return successful


class GenerateChecksumTask(speedwagon.tasks.Subtask):

    def __init__(self, package_id, source) -> None:
        super().__init__()
        self._source = source
        self._package_id = package_id

    def work(self) -> bool:
        checksum_filename = "checksum.md5"
        self.log("Generating checksums for {}".format(self._package_id))
        package_builder = package_creater.InplacePackage(self._source)
        package_builder.create_checksum_report(self.subtask_working_dir)

        generated_checksum_file = os.path.join(
            self.subtask_working_dir, checksum_filename)

        dest = os.path.join(self._source, checksum_filename)

        success = os.path.exists(generated_checksum_file)
        assert success

        shutil.move(generated_checksum_file, dest)
        assert os.path.exists(dest)
        self.log("Added checksum.md5 to {}".format(self._source))

        self.set_results(
            {
                "source": self._source,
                "checksum": dest,
                "package_id": self._package_id
            }
        )
        return success


class PrepTask(speedwagon.tasks.Subtask):

    def __init__(self, source, title_page) -> None:
        super().__init__()

        self._source = source
        self._title_page = title_page

    def work(self) -> bool:
        self.log("Prepping on {}".format(self._source))
        package_builder = package_creater.InplacePackage(self._source)
        package_builder.generate_package(destination=self._source,
                                         title_page=self._title_page)
        return True
