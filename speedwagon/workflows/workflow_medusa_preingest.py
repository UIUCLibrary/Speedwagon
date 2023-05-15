"""Workflow for Medusa Preingest.

Added on 3/30/2022

.. versionadded:: 0.3.0 added option for removing Thumbs.db files.
"""

import abc
import os
import typing
from typing import List, Any, Dict, Optional, Set, Iterator, Union, Callable
from pathlib import Path
import speedwagon
from speedwagon import workflow, tasks
from speedwagon.frontend import interaction
from speedwagon.tasks import filesystem as filesystem_tasks

__all__ = ['MedusaPreingestCuration']


def validate_missing_values(user_args: Dict[str, Union[str, bool]]) -> None:
    path = user_args.get("Path")
    if path is None:
        raise ValueError("Missing Value")


def validate_path_valid(user_args: Dict[str, Union[str, bool]]) -> None:
    path = user_args["Path"]
    if not os.path.exists(path):
        raise ValueError(f"Unable to locate {path}")


class MedusaPreingestCuration(speedwagon.Workflow):
    """Medusa Preingest curation Workflow."""

    name = "Medusa Preingest Curation"
    description = \
        """
-  Locates and deletes file that start with ._ (dot underscore)
-  Locates and deletes .DS_Store files
-  Locates and deletes Thumbs.db files
-  Locates and deletes Capture One files
    """.strip()

    validation_checks: List[Callable[[Dict[str, Union[str, bool]]], None]] = [
        validate_missing_values,
        validate_path_valid
    ]

    def initial_task(self, task_builder: tasks.TaskBuilder,
                     **user_args) -> None:
        """Add task to search for files to be removed."""
        task_builder.add_subtask(FindOffendingFiles(**user_args))
        super().initial_task(task_builder, **user_args)

    @staticmethod
    def validate_user_options(**user_args) -> bool:
        """Validate user args."""
        for check in MedusaPreingestCuration.validation_checks:
            check(user_args)
        return True

    def discover_task_metadata(
            self,
            initial_results: List[Any],
            additional_data: Dict[str, Any],
            **user_args
    ) -> List[dict]:
        """Organize the order the files & directories should be removed."""
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

    def get_additional_info(
            self,
            user_request_factory: interaction.UserRequestFactory,
            options: dict,
            pretask_results: list
    ) -> dict:
        """Confirm which files should be deleted or removed."""
        confirm = \
            user_request_factory.confirm_removal()

        return self.sort_item_data(
            confirm.get_user_response(options, pretask_results)['items']
        )

    @staticmethod
    def sort_item_data(data: List[str]) -> Dict[str, List[str]]:
        """Sort list of file contents into a dictionary based on type."""
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

    def job_options(self) -> List[workflow.AbsOutputOptionDataType]:
        """Get which types of files to search for."""
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

        delete_thumbs_db = \
            speedwagon.workflow.BooleanSelect(
                "Locate and delete Thumbs.db files"
            )
        delete_thumbs_db.value = True

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
            delete_thumbs_db,
            delete_capture_one
        ]

    @classmethod
    def generate_report(
            cls,
            results: List[tasks.Result],
            **user_args
    ) -> Optional[str]:
        """Generate a report about what files and directories were removed.

        Args:
            results:
            **user_args:
        """
        items_deleted = [
            result.data for result in results if result.source in [
                filesystem_tasks.DeleteFile,
                filesystem_tasks.DeleteDirectory
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
        """Add a delete file or delete directory task to the task list.

        Args:
            task_builder:
            **job_args:
        """
        if job_args['type'] == "file":
            task_builder.add_subtask(
                filesystem_tasks.DeleteFile(job_args["path"])
            )
        elif job_args['type'] == "directory":
            task_builder.add_subtask(
                filesystem_tasks.DeleteDirectory(job_args["path"])
            )


class AbsChecker(abc.ABC):  # pylint: disable=R0903

    @abc.abstractmethod
    def is_valid(self, path: Path) -> bool:
        """Is path valid."""


class AbsPathItemDecision(abc.ABC):  # pylint: disable=R0903
    @abc.abstractmethod
    def is_offending(self, path: Path) -> bool:
        """Get if file is offending or not."""


class DsStoreChecker(AbsChecker):  # pylint: disable=R0903
    def is_valid(self, path: Path) -> bool:
        return path.name != ".DS_Store"


class ThumbsDbChecker(AbsChecker):  # pylint: disable=R0903
    def is_valid(self, path: Path) -> bool:
        return path.name != "Thumbs.db"


class DotUnderScoreChecker(AbsChecker):  # pylint: disable=R0903
    def is_valid(self, path: Path) -> bool:
        return not path.name.startswith("._")


class OffendingPathDecider(AbsPathItemDecision):

    def __init__(self) -> None:
        self._checkers: List[AbsChecker] = []

    def add_checker(self, value: AbsChecker) -> None:
        self._checkers.append(value)

    def is_offending(self, path: Path) -> bool:
        return any(not checker.is_valid(path) for checker in self._checkers)


class FindOffendingFiles(tasks.Subtask):

    def __init__(self, **user_args) -> None:
        super().__init__()

        self.root: str = user_args['Path']
        self._include_subdirectory = user_args['Include Subdirectories']

        self._locate_capture_one: bool = \
            user_args['Locate and delete Capture One files']
        self.file_deciding_strategy = OffendingPathDecider()

        if user_args['Locate and delete dot underscore files']:
            self.file_deciding_strategy.add_checker(DotUnderScoreChecker())

        if user_args['Locate and delete .DS_Store files']:
            self.file_deciding_strategy.add_checker(DsStoreChecker())

        if user_args['Locate and delete Thumbs.db files']:
            self.file_deciding_strategy.add_checker(ThumbsDbChecker())

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
        self.set_results(self.locate_results())
        return True

    def locate_results(self) -> Set[str]:
        offending_item: Set[str] = set()
        if not os.path.exists(self.root):
            raise FileNotFoundError(f"Could not find {self.root}")

        for dir_name in self.locate_folders(self.root):
            relative_dir_to_root = \
                os.path.relpath(
                    dir_name,
                    start=self.root
                )
            self.log(f"Searching {relative_dir_to_root}")

            for item in self.locate_offending_files_and_folders(dir_name):
                offending_item.add(item)
        return offending_item

    def locate_offending_subdirectories(self, root_dir: str) -> Iterator[str]:
        if self._locate_capture_one is True:
            yield from find_capture_one_data(root_dir)

    def locate_offending_files(self, root_dir: str) -> Iterator[str]:
        for item in filter(lambda i: i.is_file(), os.scandir(root_dir)):
            if self.file_deciding_strategy.is_offending(Path(item.path)):
                yield item.path

    def locate_offending_files_and_folders(
            self,
            directory: str
    ) -> Iterator[str]:
        yield from self.locate_offending_subdirectories(directory)
        yield from self.locate_offending_files(directory)


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
