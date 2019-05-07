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


class MakeChecksumBatchSingleWorkflow(AbsWorkflow):
    name = "Make Checksum Batch [Single]"
    description = "The checksum is a signature of a file.  If any data is " \
                  "changed, the checksum will provide a different " \
                  "signature. The checksum.md5 contains a record of the " \
                  "files for a given package.\n" \
                  "\n" \
                  "The tool creates a checksum.md5 for every subdirectory " \
                  "found inside a given path.\n" \
                  "\n" \
                  "Input: Path to a root directory that contains " \
                  "subdirectories to generate checksum.md5 files"

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        jobs = []
        package_root = user_args["Input"]
        report_to_save_to = os.path.normpath(os.path.join(package_root,
                                                          "checksum.md5"))

        for root, dirs, files in os.walk(package_root):
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

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        source_path = job_args['source_path']
        filename = job_args['filename']
        report_name = job_args['save_to_filename']

        new_task = checksum_tasks.MakeChecksumTask(
            source_path, filename, report_name)

        task_builder.add_subtask(new_task)

    def completion_task(self, task_builder: tasks.TaskBuilder, results,
                        **user_args) -> None:

        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():

            process = checksum_tasks.MakeCheckSumReportTask(
                checksum_report, checksums)

            task_builder.add_subtask(process)

    @classmethod
    @add_report_borders
    def generate_report(cls, results: List[tasks.Result],
                        **user_args) -> Optional[str]:

        report_lines = []

        for checksum_report, items_written in \
                cls.sort_results([i.data for i in results]).items():

            report_lines.append(f"Checksum values for {len(items_written)} "
                                f"files written to {checksum_report}")

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

        for k, v in itertools.groupby(
                sorted_results,
                key=lambda it: it[ResultsValues.CHECKSUM_FILE]):

            for result_data in v:
                new_results[k].append(result_data)
        return dict(new_results)

    def user_options(self):
        return [
            options.UserOptionCustomDataType("Input",
                                             options.FolderData),
        ]


class MakeChecksumBatchMultipleWorkflow(AbsWorkflow):
    name = "Make Checksum Batch [Multiple]"
    description = "Creates a checksum.md5 for every subdirectory found " \
                  "inside a given path" \
                  "\nInput: Path to a root directory that contains " \
                  "subdirectories to generate checksum.md5 files"

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:

        jobs = []

        root_for_all_packages = user_args["Input"]
        for sub_dir in filter(lambda it: it.is_dir(),
                              os.scandir(root_for_all_packages)):

            package_root = sub_dir.path
            report_to_save_to = os.path.normpath(
                os.path.join(package_root, "checksum.md5"))

            for root, dirs, files in os.walk(package_root):
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

    def user_options(self):
        return [
            options.UserOptionCustomDataType("Input",
                                             options.FolderData),
        ]

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        source_path = job_args['source_path']
        filename = job_args['filename']
        report_name = job_args['save_to_filename']

        new_task = checksum_tasks.MakeChecksumTask(
            source_path, filename, report_name)

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

    def completion_task(self, task_builder: tasks.TaskBuilder, results,
                        **user_args) -> None:

        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():

            process = checksum_tasks.MakeCheckSumReportTask(
                checksum_report, checksums)

            task_builder.add_subtask(process)

    @add_report_borders
    def generate_report(cls, results: List[tasks.Result],
                        **user_args) -> Optional[str]:

        report_lines = []

        for checksum_report, items_written in \
                cls.sort_results([i.data for i in results]).items():

            report_lines.append(f"Checksum values for {len(items_written)} "
                                f"files written to {checksum_report}")

        return "\n".join(report_lines)


class RegenerateChecksumBatchSingleWorkflow(AbsWorkflow):
    name = "Regenerate Checksum Batch [Single]"
    description = "Regenerates the hash values for every checksum.md5 " \
                  "located inside a given path.\n" \
                  "\n" \
                  "Input: Path to a root directory that contains " \
                  "subdirectories to generate checksum.md5 files"

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        jobs = []

        report_to_save_to = user_args["Input"]
        package_root = os.path.dirname(report_to_save_to)

        for root, dirs, files in os.walk(package_root):
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

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        source_path = job_args['source_path']
        filename = job_args['filename']
        report_name = job_args['save_to_filename']

        new_task = checksum_tasks.MakeChecksumTask(
            source_path, filename, report_name)

        task_builder.add_subtask(new_task)

    def completion_task(self, task_builder: tasks.TaskBuilder, results,
                        **user_args) -> None:

        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():

            process = checksum_tasks.MakeCheckSumReportTask(
                checksum_report, checksums)

            task_builder.add_subtask(process)

    @classmethod
    @add_report_borders
    def generate_report(cls, results: List[tasks.Result],
                        **user_args) -> Optional[str]:

        report_lines = []

        for checksum_report, items_written in \
                cls.sort_results([i.data for i in results]).items():

            report_lines.append(f"Checksum values for {len(items_written)} "
                                f"files written to {checksum_report}")

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

        for k, v in itertools.groupby(
                sorted_results,
                key=lambda it: it[ResultsValues.CHECKSUM_FILE]):

            for result_data in v:
                new_results[k].append(result_data)
        return dict(new_results)

    def user_options(self):
        return [
            options.UserOptionCustomDataType(
                "Input", shared_custom_widgets.ChecksumData),
        ]


class RegenerateChecksumBatchMultipleWorkflow(AbsWorkflow):
    name = "Regenerate Checksum Batch [Multiple]"
    description = "Regenerates the hash values for ever checksum.md5 " \
                  "located inside a given path\n" \
                  "\n" \
                  "Input: Path to a root directory that contains " \
                  "subdirectories to generate checksum.md5 files"

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:

        jobs = []

        root_for_all_packages = user_args["Input"]
        for sub_dir in filter(lambda it: it.is_dir(),
                              os.scandir(root_for_all_packages)):

            package_root = sub_dir.path
            report_to_save_to = os.path.normpath(
                os.path.join(package_root, "checksum.md5"))

            for root, dirs, files in os.walk(package_root):
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

    def user_options(self):
        return [
            options.UserOptionCustomDataType("Input",
                                             options.FolderData),
        ]

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
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

    def completion_task(self, task_builder: tasks.TaskBuilder, results,
                        **user_args) -> None:

        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():

            process = checksum_tasks.MakeCheckSumReportTask(
                checksum_report, checksums)

            task_builder.add_subtask(process)

    @add_report_borders
    def generate_report(cls, results: List[tasks.Result],
                        **user_args) -> Optional[str]:

        report_lines = []

        for checksum_report, items_written in \
                cls.sort_results([i.data for i in results]).items():

            report_lines.append(f"Checksum values for {len(items_written)} "
                                f"files written to {checksum_report}")

        return "\n".join(report_lines)
