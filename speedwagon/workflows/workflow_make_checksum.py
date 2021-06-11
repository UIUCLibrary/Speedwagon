import collections
import typing

import os

import itertools
from typing import List, Any, DefaultDict, Optional

from speedwagon.job import AbsWorkflow
from speedwagon import tasks
from speedwagon.reports import add_report_borders
from .checksum_shared import ResultsValues
from . import checksum_tasks, shared_custom_widgets
from . import shared_custom_widgets as options


__all__ = [
    'MakeChecksumBatchSingleWorkflow',
    'MakeChecksumBatchMultipleWorkflow'
]


class AbcMakeChecksumWorkflow(AbsWorkflow):
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


class MakeChecksumBatchSingleWorkflow(AbcMakeChecksumWorkflow):
    name = "Make Checksum Batch [Single]"
    description = "The checksum is a signature of a file.  If any data is " \
                  "changed, the checksum will provide a different " \
                  "signature.  The checksum.md5 contains a record of each " \
                  "file in a single item along with respective checksum " \
                  "values " \
                  "\n" \
                  "Creates a single checksum.md5 for every file inside a " \
                  "given folder" \
                  "\n" \
                  "Input: Path to a root folder"

    def discover_task_metadata(self,
                               initial_results: List[tasks.Result],
                               additional_data,
                               **user_args: str) -> List[dict]:
        jobs = []
        package_root = user_args["Input"]
        report_to_save_to = os.path.normpath(os.path.join(package_root,
                                                          "checksum.md5"))

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

    def create_new_task(self,
                        task_builder: tasks.TaskBuilder,
                        **job_args: str) -> None:

        source_path = job_args['source_path']
        filename = job_args['filename']
        report_name = job_args['save_to_filename']

        new_task = checksum_tasks.MakeChecksumTask(
            source_path, filename, report_name)

        task_builder.add_subtask(new_task)

    def completion_task(self,
                        task_builder: tasks.TaskBuilder,
                        results: List[tasks.Result],
                        **user_args: str) -> None:

        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():

            process = checksum_tasks.MakeCheckSumReportTask(
                checksum_report, checksums)

            task_builder.add_subtask(process)

    @classmethod
    @add_report_borders
    def generate_report(cls,
                        results: List[tasks.Result],
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


class MakeChecksumBatchMultipleWorkflow(AbcMakeChecksumWorkflow):
    name = "Make Checksum Batch [Multiple]"
    description = "The checksum is a signature of a file.  If any data " \
                  "is changed, the checksum will provide a different " \
                  "signature.  The checksum.md5 contains a record of the " \
                  "files for a given package." \
                  "\n" \
                  "The tool creates a checksum.md5 for every subdirectory " \
                  "found inside a given path." \
                  "\n" \
                  "Input: Path to a root directory that contains " \
                  "subdirectories to generate checksum.md5 files"

    def discover_task_metadata(
            self,
            initial_results: List[Any],
            additional_data,
            **user_args: str
    ) -> List[typing.Dict[str, str]]:

        jobs = []

        root_for_all_packages = user_args["Input"]
        for sub_dir in filter(lambda it: it.is_dir(),
                              os.scandir(root_for_all_packages)):

            package_root = sub_dir.path
            report_to_save_to = os.path.normpath(
                os.path.join(package_root, "checksum.md5"))

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
            task_builder: tasks.TaskBuilder,
            **job_args: str
    ) -> None:

        source_path = job_args['source_path']
        filename = job_args['filename']
        report_name = job_args['save_to_filename']

        new_task = checksum_tasks.MakeChecksumTask(
            source_path, filename, report_name)

        task_builder.add_subtask(new_task)

    def completion_task(self,
                        task_builder: tasks.TaskBuilder,
                        results: List[tasks.Result],
                        **user_args: str) -> None:

        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():

            process = checksum_tasks.MakeCheckSumReportTask(
                checksum_report, checksums)

            task_builder.add_subtask(process)

    @classmethod
    @add_report_borders
    def generate_report(cls,
                        results: List[tasks.Result],
                        **user_args: str) -> Optional[str]:

        report_lines = [
            f"Checksum values for {len(items_written)} "
            f"files written to {checksum_report}"
            for checksum_report, items_written in cls.sort_results(
                [i.data for i in results]
            ).items()
        ]

        return "\n".join(report_lines)


class RegenerateChecksumBatchSingleWorkflow(AbsWorkflow):
    name = "Regenerate Checksum Batch [Single]"
    description = "Regenerates hash values for every file inside for a " \
                  "given checksum.md5 file" \
                  "\n" \
                  "Input: Path to a root folder"

    def discover_task_metadata(self,
                               initial_results: List[tasks.Result],
                               additional_data,
                               **user_args: str) -> List[dict]:
        jobs = []

        report_to_save_to = user_args["Input"]
        package_root = os.path.dirname(report_to_save_to)

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

    def create_new_task(self,
                        task_builder: tasks.TaskBuilder,
                        **job_args: str) -> None:

        source_path = job_args['source_path']
        filename = job_args['filename']
        report_name = job_args['save_to_filename']

        new_task = checksum_tasks.MakeChecksumTask(
            source_path, filename, report_name)

        task_builder.add_subtask(new_task)

    def completion_task(self,
                        task_builder: tasks.TaskBuilder,
                        results: List[tasks.Result],
                        **user_args: str) -> None:

        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():

            process = checksum_tasks.MakeCheckSumReportTask(
                checksum_report, checksums)

            task_builder.add_subtask(process)

    @classmethod
    @add_report_borders
    def generate_report(cls, results: List[tasks.Result],
                        **user_args: str) -> Optional[str]:

        report_lines = [
            f"Checksum values for {len(items_written)} "
            f"files written to {checksum_report}"
            for checksum_report, items_written in cls.sort_results(
                [i.data for i in results]
            ).items()
        ]

        return "\n".join(report_lines)

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

    def user_options(self) -> List[options.UserOption3]:
        return [
            options.UserOptionCustomDataType(
                "Input", shared_custom_widgets.ChecksumData),
        ]


class RegenerateChecksumBatchMultipleWorkflow(AbsWorkflow):
    name = "Regenerate Checksum Batch [Multiple]"
    description = "Regenerates the hash values for every checksum.md5 " \
                  "located inside a given path\n" \
                  "\n" \
                  "Input: Path to a root directory that contains " \
                  "subdirectories to generate checksum.md5 files"

    def discover_task_metadata(self,
                               initial_results: List[Any],
                               additional_data,
                               **user_args: str) -> List[dict]:

        jobs = []

        root_for_all_packages = user_args["Input"]
        for sub_dir in filter(lambda it: it.is_dir(),
                              os.scandir(root_for_all_packages)):

            package_root = sub_dir.path
            report_to_save_to = os.path.normpath(
                os.path.join(package_root, "checksum.md5"))

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

    def create_new_task(self,
                        task_builder: tasks.TaskBuilder,
                        **job_args: str) -> None:

        source_path = job_args['source_path']
        filename = job_args['filename']
        report_name = job_args['save_to_filename']

        new_task = \
            checksum_tasks.MakeChecksumTask(source_path, filename, report_name)

        task_builder.add_subtask(new_task)

    @classmethod
    def sort_results(cls,
                     results: typing.List[typing.Mapping[ResultsValues, str]]
                     ) -> typing.Dict[str,
                                      typing.List[typing.Dict[ResultsValues,
                                                              str]]]:

        new_results: DefaultDict[str, list] = collections.defaultdict(list)

        sorted_results = sorted(results,
                                key=lambda it: it[ResultsValues.CHECKSUM_FILE])

        for k, v in itertools.groupby(
                sorted_results,
                key=lambda it: it[ResultsValues.CHECKSUM_FILE]):

            for result_data in v:
                new_results[k].append(result_data)
        return dict(new_results)

    def completion_task(self,
                        task_builder: tasks.TaskBuilder,
                        results: List[tasks.Result],
                        **user_args: str) -> None:

        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():

            process = checksum_tasks.MakeCheckSumReportTask(
                checksum_report, checksums)

            task_builder.add_subtask(process)

    @classmethod
    @add_report_borders
    def generate_report(cls,
                        results: List[tasks.Result],
                        **user_args: str) -> Optional[str]:

        report_lines = [
            f"Checksum values for {len(items_written)} "
            f"files written to {checksum_report}"
            for checksum_report, items_written in cls.sort_results(
                [i.data for i in results]
            ).items()
        ]

        return "\n".join(report_lines)
