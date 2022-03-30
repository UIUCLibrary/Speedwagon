import abc
import os
import typing
from typing import List, Any, Dict, Optional, Set, Iterator, Union, Callable

from PySide6 import QtWidgets, QtCore
from PySide6.QtGui import Qt

import speedwagon
from speedwagon import workflow, tasks


def validate_missing_values(user_args: Dict[str, Union[str, bool]]) -> None:
    path = user_args.get("Path")
    if path is None:
        raise ValueError("Missing Value")


def validate_path_valid(user_args: Dict[str, Union[str, bool]]) -> None:
    path = user_args["Path"]
    if not os.path.exists(path):
        raise ValueError(f"Unable to locate {path}")


class MedusaPreingestCuration(speedwagon.Workflow):
    name = "Medusa Preingest Curation"
    description = \
        """
-  Locates and deletes file that start with ._ (dot underscore)
-  Locates and deletes .DS_Store files
-  Locates and deletes Capture One files
-  Verifies that contents are structured in standard package format
    """.strip()

    validation_checks: List[Callable[[Dict[str, Union[str, bool]]], None]] = [
        validate_missing_values,
        validate_path_valid
    ]

    def initial_task(self, task_builder: tasks.TaskBuilder,
                     **user_args) -> None:
        task_builder.add_subtask(FindOffendingFiles(**user_args))
        super().initial_task(task_builder, **user_args)

    @staticmethod
    def validate_user_options(**user_args) -> bool:
        for check in MedusaPreingestCuration.validation_checks:
            check(user_args)
        return True

    def discover_task_metadata(
            self,
            initial_results: List[Any],
            additional_data: Dict[str, Any],
            **user_args
    ) -> List[dict]:
        new_tasks: List[Dict[str, str]] = []

        for file_path in additional_data["files"]:
            new_tasks.append({
                "type": "file",
                "path": file_path
            })

        for directory_path in additional_data['directories']:
            new_tasks.append({
                "type": "directory",
                "path": directory_path
            })

        return new_tasks

    def get_additional_info(self, parent: typing.Optional[QtWidgets.QWidget],
                            options: dict, pretask_results: list) -> dict:

        dialog = ConfirmDeleteDialog(
            items=list(pretask_results[0].data),
            parent=parent
        )
        results = dialog.exec()
        if results == QtWidgets.QDialog.Rejected:
            raise speedwagon.JobCancelled()

        resulting_data: List[str] = dialog.data()
        return self.sort_item_data(resulting_data)

    @staticmethod
    def sort_item_data(data: List[str]) -> Dict[str, List[str]]:
        dirs: List[str] = []
        files: List[str] = []

        for item in data:
            if os.path.isdir(item):
                dirs.append(item)
            elif os.path.isfile(item):
                files.append(item)
            else:
                raise ValueError(
                    f"Unable to determine if file or directory: {item}."
                )
        return {
            "files": files,
            "directories": dirs,
        }

    def get_user_options(self) -> List[workflow.AbsOutputOptionDataType]:
        root_directory = speedwagon.workflow.DirectorySelect("Path")

        include_subdirectories = \
            speedwagon.workflow.BooleanSelect("Include Subdirectories")
        include_subdirectories.value = True

        delete_dot_underscore = \
            speedwagon.workflow.BooleanSelect(
                "Locate and delete dot underscore files"
            )
        delete_dot_underscore.value = True

        delete_ds_store = \
            speedwagon.workflow.BooleanSelect(
                "Locate and delete .DS_Store files"
            )
        delete_ds_store.value = True

        delete_capture_one = \
            speedwagon.workflow.BooleanSelect(
                "Locate and delete Capture One files"
            )
        delete_capture_one.value = True

        return [
            root_directory,
            include_subdirectories,
            delete_dot_underscore,
            delete_ds_store,
            delete_capture_one
        ]

    @classmethod
    def generate_report(
            cls,
            results: List[tasks.Result],
            **user_args
    ) -> Optional[str]:
        items_deleted = [
            result.data for result in results if result.source in [
                DeleteFile,
                DeleteDirectory
            ]
        ]

        report_lines = [
            "*" * 80,
            "Deleted the following files and/or folders",
            "------------------------------------------",
            "\n",
            "\n".join([f"* {item}" for item in items_deleted]),
            "*" * 80,
        ]
        return "\n".join(report_lines)

    def create_new_task(self, task_builder: tasks.TaskBuilder,
                        **job_args) -> None:
        if job_args['type'] == "file":
            task_builder.add_subtask(DeleteFile(job_args["path"]))
        elif job_args['type'] == "directory":
            task_builder.add_subtask(DeleteDirectory(job_args["path"]))


class FindOffendingFiles(tasks.Subtask):

    def __init__(self, **user_args) -> None:
        super().__init__()

        self.root: str = user_args['Path']
        self._include_subdirectory = user_args['Include Subdirectories']

        self._locate_dot_underscore: bool = \
            user_args['Locate and delete dot underscore files']

        self._locate_ds_store: bool = \
            user_args['Locate and delete .DS_Store files']

        self._locate_capture_one: bool = \
            user_args['Locate and delete Capture One files']

    def task_description(self) -> Optional[str]:
        return f"Searching {self.root}"

    @staticmethod
    def locate_folders(
            starting_dir: str,
            recursive: bool = True
    ) -> typing.Iterable[str]:
        if not recursive:
            item: 'os.DirEntry[str]'
            for item in filter(lambda x: x.is_dir(), os.scandir(starting_dir)):
                yield item.path
        else:
            for root, dirs, _ in os.walk(starting_dir):
                for dir_name in dirs:
                    yield os.path.join(root, dir_name)

    def work(self) -> bool:
        offending_item: Set[str] = set()
        for dir_name in self.locate_folders(self.root):
            relative_dir_to_root = \
                os.path.relpath(
                    dir_name,
                    start=self.root
                )
            self.log(f"Searching {relative_dir_to_root}")

            for item in self.locate_offending_files_and_folders(dir_name):
                offending_item.add(item)

        self.set_results(offending_item)
        return True

    def locate_offending_files_and_folders(
            self,
            directory: str
    ) -> Iterator[str]:
        if self._locate_capture_one is True:
            yield from self.find_capture_one_data(directory)

        for item in filter(lambda i: i.is_file(), os.scandir(directory)):
            if all([
                self._locate_dot_underscore,
                item.name.startswith("._")
            ]):
                yield item.path
                continue

            if all([
                self._locate_ds_store,
                item.name == ".DS_Store"
            ]):
                yield item.path

    @staticmethod
    def find_capture_one_data(directory: str) -> Iterator[str]:
        potential_capture_one_dir_name = \
            os.path.join(directory, "CaptureOne")

        if os.path.exists(potential_capture_one_dir_name):
            for root, dirs, files in os.walk(potential_capture_one_dir_name):
                for file_name in files:
                    yield os.path.join(root, file_name)
                for dir_name in dirs:
                    yield os.path.join(root, dir_name)
            yield potential_capture_one_dir_name


class DeleteFileSystemItem(tasks.Subtask, abc.ABC):

    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path


class DeleteFile(DeleteFileSystemItem):

    def task_description(self) -> Optional[str]:
        return "Deleting file"

    def work(self) -> bool:
        self.log(f"Deleting {self.path}")
        self.set_results(self.path)
        return True


class DeleteDirectory(DeleteFileSystemItem):

    def work(self) -> bool:
        self.log(f"Removing {self.path} directory")
        self.set_results(self.path)
        return True

    def task_description(self) -> Optional[str]:
        return "Removing directory"


class ConfirmDeleteDialog(QtWidgets.QDialog):
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
        self.setFixedWidth(500)
        self._make_connections()
        self.package_view = QtWidgets.QListView(self)

        layout.addWidget(self.package_view)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self.model = ConfirmListModel(items=items, parent=self)
        self.package_view.setModel(self.model)

    def _make_connections(self):
        # pylint: disable=E1101
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def data(self) -> List[str]:
        return self.model.selected()


class ConfirmListModel(QtCore.QAbstractListModel):

    def __init__(
            self,
            items: List[str],
            parent: Optional[QtCore.QObject] = None
    ) -> None:

        super().__init__(parent)

        self.items = [{
                "name": i,
                "checked": Qt.Checked
            } for i in items
        ]

    def selected(self) -> List[str]:
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
        return len(self.items)

    def data(
            self,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ],
            role: int = Qt.DisplayRole
    ) -> Any:
        if role == Qt.CheckStateRole:
            return self.items[index.row()].get("checked", Qt.Unchecked)
        if role == Qt.DisplayRole:
            return self.items[index.row()]['name']
        return None

    def setData(  # pylint: disable=invalid-name
            self,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ],
            value: Any,
            role: int = Qt.DisplayRole
    ) -> bool:
        if role == Qt.CheckStateRole:
            self.items[index.row()]['checked'] = value
            return True

        return super().setData(index, value, role)

    def flags(
            self,
            index: Union[
                QtCore.QModelIndex,
                QtCore.QPersistentModelIndex
            ]) -> QtCore.Qt.ItemFlags:
        if index.isValid():
            return super().flags(index) | Qt.ItemIsUserCheckable
        return super().flags(index)
