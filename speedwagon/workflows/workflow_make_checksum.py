import collections
import typing

import os
import enum

import itertools
from typing import List, Any, DefaultDict, Optional

import speedwagon
from speedwagon.job import AbsWorkflow
from speedwagon.tools import options
from speedwagon import tasks
from pyhathiprep import checksum
from speedwagon.reports import add_report_borders


class ResultsValues(enum.Enum):
    SOURCE_FILE = "source_filename"
    SOURCE_HASH = "checksum_hash"
    CHECKSUM_FILE = "checksum_file"


class MakeChecksumBatchSingleWorkflow(AbsWorkflow):
    name = "0 EXPERIMENTAL " \
           "Make Checksum Batch [Single]"
    description = "Creates a single checksum.md5 for every file inside " \
                  "a given folder" \
                  "\nInput: Path to a root folder"

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
        new_task = MakeChecksumTask(source_path, filename, report_name)
        task_builder.add_subtask(new_task)

    def completion_task(self, task_builder: tasks.TaskBuilder, results,
                        **user_args) -> None:

        sorted_results = self.sort_results([i.data for i in results])

        for checksum_report, checksums in sorted_results.items():
            process = MakeCheckSumReportTask(checksum_report, checksums)
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
    name = "0 EXPERIMENTAL " \
           "Make Checksum Batch [Multiple]"
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
        new_task = MakeChecksumTask(source_path, filename, report_name)
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
            process = MakeCheckSumReportTask(checksum_report, checksums)
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


class MakeChecksumTask(tasks.Subtask):

    def __init__(self, source_path, filename, checksum_report) -> None:
        super().__init__()
        self._source_path = source_path
        self._filename = filename
        self._checksum_report = checksum_report

    def work(self) -> bool:
        item_path = self._source_path
        item_file_name = self._filename = self._filename
        report_path_to_save_to = self._checksum_report
        self.log(f"Calculated the checksum for {item_file_name}")

        file_to_calculate = os.path.join(item_path, item_file_name)
        result = {
            ResultsValues.SOURCE_FILE: item_file_name,
            ResultsValues.SOURCE_HASH: checksum.calculate_md5_hash(
                file_to_calculate),
            ResultsValues.CHECKSUM_FILE: report_path_to_save_to

        }
        self.set_results(result)

        return True


class MakeCheckSumReportTask(speedwagon.tasks.Subtask):

    def __init__(self, output_filename, checksum_calculations) -> None:
        super().__init__()
        self._output_filename = output_filename
        self._checksum_calculations = checksum_calculations

    def work(self) -> bool:

        report_builder = checksum.HathiChecksumReport()
        for item in self._checksum_calculations:
            filename = item[ResultsValues.SOURCE_FILE]
            hash_value = item[ResultsValues.SOURCE_HASH]
            report_builder.add_entry(filename, hash_value)
        report = report_builder.build()

        with open(self._output_filename, "w", encoding="utf-8") as wf:
                wf.write(report)
        self.log("Wrote {}".format(self._output_filename))

        return True
