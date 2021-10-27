"""Workflows for generating checksums."""

import collections
import typing

import os

import itertools
import warnings
from abc import ABC
from typing import List, Any, DefaultDict, Optional

import speedwagon
from speedwagon.job import Workflow
from speedwagon.reports import add_report_borders
from speedwagon.tasks import validation
from .checksum_shared import ResultsValues
from . import shared_custom_widgets
from . import shared_custom_widgets as options


__all__ = [
    'MakeChecksumBatchSingleWorkflow',
    'MakeChecksumBatchMultipleWorkflow'
]

DEFAULT_CHECKSUM_FILE_NAME = "checksum.md5"


class CreateChecksumWorkflow(Workflow, ABC):
    @staticmethod
    def locate_files(package_root: str):
        for root, _, files in os.walk(package_root):
            for file_ in files:
                yield os.path.join(root, file_)

    @classmethod
    def sort_results(cls,
                     results: typing.List[typing.Mapping[ResultsValues, str]]
                     ) -> typing.Dict[str,
                                      typing.List[typing.Dict[ResultsValues,
                                                              str]]]:

        new_results: DefaultDict[str, list] = collections.defaultdict(list)

        sorted_results = sorted(results,
                                key=lambda it: it[ResultsValues.CHECKSUM_FILE])

        for key, value in itertools.groupby(
                sorted_results,
                key=lambda it: it[ResultsValues.CHECKSUM_FILE]):

            for result_data in value:
                new_results[key].append(result_data)
        return dict(new_results)

    def completion_task(self,
                        task_builder: "speedwagon.tasks.TaskBuilder",
                        results: List[speedwagon.tasks.Result],
                        **user_args: str) -> None:
        """Create checksum report at very end."""
        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():

            process = validation.MakeCheckSumReportTask(
                checksum_report, checksums)

            task_builder.add_subtask(process)

    def create_new_task(self,
                        task_builder: "speedwagon.tasks.TaskBuilder",
                        **job_args: str) -> None:

        filename = job_args['filename']
        source_path = job_args['source_path']
        report_name = job_args['save_to_filename']

        new_task = \
            validation.MakeChecksumTask(source_path, filename, report_name)

        task_builder.add_subtask(new_task)


class MakeChecksumBatchSingleWorkflow(CreateChecksumWorkflow):
    """Workflow for generating a checksum report for single batch of files."""

    name = "Make Checksum Batch [Single]"
    description = "The checksum is a signature of a file.  If any data is " \
                  "changed, the checksum will provide a different " \
                  f"signature.  The {DEFAULT_CHECKSUM_FILE_NAME} contains a " \
                  f"record of each file in a single item along with " \
                  f"respective checksum values " \
                  "\n" \
                  f"Creates a single {DEFAULT_CHECKSUM_FILE_NAME} for every " \
                  f"file inside a given folder" \
                  "\n" \
                  "Input: Path to a root folder"

    def discover_task_metadata(self,
                               initial_results: List[
                                   speedwagon.tasks.Result],
                               additional_data,
                               **user_args: str) -> List[dict]:
        jobs = []
        package_root = user_args["Input"]
        report_to_save_to = os.path.normpath(
            os.path.join(package_root, DEFAULT_CHECKSUM_FILE_NAME)
        )
        for file_path in self.locate_files(package_root):
            relpath = os.path.relpath(file_path, package_root)
            job = {
                "source_path": package_root,
                "filename": relpath,
                "save_to_filename": report_to_save_to
            }
            jobs.append(job)
        return jobs

    @classmethod
    @add_report_borders
    def generate_report(cls,
                        results: List[speedwagon.tasks.Result],
                        **user_args: str) -> Optional[str]:

        report_lines = [
            f"Checksum values for {len(items_written)} "
            f"files written to {checksum_report}"
            for checksum_report, items_written in cls.sort_results(
                [i.data for i in results]
            ).items()
        ]

        return "\n".join(report_lines)

    def user_options(self) -> List[options.UserOption3]:
        return [
            options.UserOptionCustomDataType("Input",
                                             options.FolderData),
        ]


class MakeChecksumBatchMultipleWorkflow(CreateChecksumWorkflow):
    name = "Make Checksum Batch [Multiple]"
    description = "The checksum is a signature of a file.  If any data " \
                  "is changed, the checksum will provide a different " \
                  f"signature.  The {DEFAULT_CHECKSUM_FILE_NAME} contains a " \
                  f"record of the files for a given package." \
                  "\n" \
                  f"The tool creates a {DEFAULT_CHECKSUM_FILE_NAME} for " \
                  f"every subdirectory found inside a given path." \
                  "\n" \
                  "Input: Path to a root directory that contains " \
                  f"subdirectories to generate {DEFAULT_CHECKSUM_FILE_NAME} " \
                  f"files"

    def discover_task_metadata(
            self,
            initial_results: List[Any],
            additional_data,
            **user_args: str
    ) -> List[typing.Dict[str, str]]:

        jobs = []

        for sub_dir in filter(lambda it: it.is_dir(),
                              os.scandir(user_args["Input"])):

            package_root = sub_dir.path
            report_to_save_to = os.path.normpath(
                os.path.join(package_root, DEFAULT_CHECKSUM_FILE_NAME)
            )

            for root, _, files in os.walk(package_root):
                for file_ in files:
                    full_path = os.path.join(root, file_)
                    relpath = os.path.relpath(full_path, package_root)
                    job = {
                        "source_path": package_root,
                        "filename": relpath,
                        "save_to_filename": report_to_save_to
                    }
                    jobs.append(job)
        return jobs

    def user_options(self) -> List[options.UserOption3]:
        return [
            options.UserOptionCustomDataType("Input",
                                             options.FolderData),
        ]

    def create_new_task(
            self,
            task_builder: "speedwagon.tasks.TaskBuilder",
            **job_args: str
    ) -> None:

        filename = job_args['filename']
        report_name = job_args['save_to_filename']
        source_path = job_args['source_path']

        task_builder.add_subtask(
            validation.MakeChecksumTask(
                source_path,
                filename,
                report_name
            )
        )

    @classmethod
    @add_report_borders
    def generate_report(cls,
                        results: List[speedwagon.tasks.Result],
                        **user_args: str) -> Optional[str]:

        report_lines = [
            f"Checksum values for {len(items_written)} "
            f"files written to {checksum_report}"
            for checksum_report, items_written in cls.sort_results(
                [i.data for i in results]
            ).items()
        ]

        return "\n".join(report_lines)


class RegenerateChecksumBatchSingleWorkflow(CreateChecksumWorkflow):
    name = "Regenerate Checksum Batch [Single]"
    description = "Regenerates hash values for every file inside for a " \
                  f"given {DEFAULT_CHECKSUM_FILE_NAME} file" \
                  "\n" \
                  "Input: Path to a root folder"
    active = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        warnings.warn(
            "Pending removal of Regenerate Checksum Batch [Single]",
            DeprecationWarning
        )

    def discover_task_metadata(self,
                               initial_results: List[
                                   speedwagon.tasks.Result],
                               additional_data,
                               **user_args: str) -> List[dict]:
        jobs = []

        report_to_save_to = user_args["Input"]
        package_root = os.path.dirname(report_to_save_to)

        for file_path in self.locate_files(package_root):
            relpath = os.path.relpath(file_path, package_root)
            jobs.append(
                {
                    "source_path": package_root,
                    "filename": relpath,
                    "save_to_filename": report_to_save_to
                }
            )
        return jobs

    def create_new_task(self,
                        task_builder: "speedwagon.tasks.TaskBuilder",
                        **job_args: str) -> None:

        source_path = job_args['source_path']
        filename = job_args['filename']
        report_name = job_args['save_to_filename']

        new_task = validation.MakeChecksumTask(
            source_path, filename, report_name)

        task_builder.add_subtask(new_task)

    def completion_task(self,
                        task_builder: "speedwagon.tasks.TaskBuilder",
                        results: List[speedwagon.tasks.Result],
                        **user_args: str) -> None:

        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():

            process = validation.MakeCheckSumReportTask(
                checksum_report, checksums)

            task_builder.add_subtask(process)

    @classmethod
    @add_report_borders
    def generate_report(cls, results: List[speedwagon.tasks.Result],
                        **user_args: str) -> Optional[str]:

        report_lines = [
            f"Checksum values for {len(items_written)} "
            f"files written to {checksum_report}"
            for checksum_report, items_written in cls.sort_results(
                [i.data for i in results]
            ).items()
        ]

        return "\n".join(report_lines)

    def user_options(self) -> List[options.UserOption3]:
        return [
            options.UserOptionCustomDataType(
                "Input", shared_custom_widgets.ChecksumData),
        ]


class RegenerateChecksumBatchMultipleWorkflow(CreateChecksumWorkflow):
    name = "Regenerate Checksum Batch [Multiple]"
    description = f"Regenerates the hash values for every " \
                  f"{DEFAULT_CHECKSUM_FILE_NAME} located inside a " \
                  f"given path\n" \
                  "\n" \
                  "Input: Path to a root directory that contains " \
                  f"subdirectories to generate {DEFAULT_CHECKSUM_FILE_NAME} " \
                  f"files"
    active = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        warnings.warn(
            "Pending removal of Regenerate Checksum Batch [Multiple]",
            DeprecationWarning
        )

    def discover_task_metadata(self,
                               initial_results: List[Any],
                               additional_data,
                               **user_args: str) -> List[dict]:

        jobs = []

        for sub_dir in filter(lambda it: it.is_dir(),
                              os.scandir(user_args["Input"])):

            package_root = sub_dir.path

            report_to_save_to = os.path.normpath(
                os.path.join(package_root, DEFAULT_CHECKSUM_FILE_NAME)
            )

            for root, _, files in os.walk(package_root):
                for file_ in files:
                    full_path = os.path.join(root, file_)
                    if os.path.samefile(report_to_save_to, full_path):
                        continue
                    relpath = os.path.relpath(full_path, package_root)
                    job = {
                        "source_path": package_root,
                        "filename": relpath,
                        "save_to_filename": report_to_save_to
                    }
                    jobs.append(job)
        return jobs

    def user_options(self) -> List[options.UserOption3]:
        return [
            options.UserOptionCustomDataType("Input",
                                             options.FolderData),
        ]

    def completion_task(self,
                        task_builder: "speedwagon.tasks.TaskBuilder",
                        results: List[speedwagon.tasks.Result],
                        **user_args: str) -> None:

        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():
            task_builder.add_subtask(
                validation.MakeCheckSumReportTask(
                    checksum_report,
                    checksums
                )
            )

    @classmethod
    @add_report_borders
    def generate_report(cls,
                        results: List[speedwagon.tasks.Result],
                        **user_args: str) -> Optional[str]:
        report_lines = [
            f"Checksum values for {len(items_written)} "
            f"files written to {checksum_report}"
            for checksum_report, items_written in cls.sort_results(
                [i.data for i in results]
            ).items()
        ]

        return "\n".join(report_lines)
