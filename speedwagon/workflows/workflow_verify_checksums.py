"""Workflow for verifying checksums."""


import abc
import collections
import itertools
import os
import enum
from typing import DefaultDict, Iterable, Optional, Dict, List, Any, Union
import typing

import hathi_validate.process

import speedwagon
from speedwagon.job import Workflow
from speedwagon.reports import add_report_borders

__all__ = ['ChecksumWorkflow', 'VerifyChecksumBatchSingleWorkflow']

from speedwagon import workflow

TaskResult = Union[str, bool]


class UserArgs(enum.Enum):
    INPUT = "Input"


class JobValues(enum.Enum):
    SOURCE_REPORT = "source_report"
    EXPECTED_HASH = "expected_hash"
    ITEM_FILENAME = "filename"
    ROOT_PATH = "path"


class ResultValues(enum.Enum):
    VALID = "valid"
    FILENAME = "filename"
    PATH = "path"
    CHECKSUM_REPORT_FILE = "checksum_report_file"


class ChecksumWorkflow(Workflow):
    """Checksum validation workflow for Speedwagon."""

    name = "Verify Checksum Batch [Multiple]"
    description = "Verify checksum values in checksum batch file, report " \
                  "errors. Verifies every entry in the checksum.md5 files " \
                  "matches expected hash value for the actual file.  Tool " \
                  "reports discrepancies in console of Speedwagon." \
                  "\n" \
                  "Input is path that contains subdirectory which a text " \
                  "file containing a list of multiple files and their md5 " \
                  "values. The listed files are expected to be siblings to " \
                  "the checksum file."

    @staticmethod
    def locate_checksum_files(root: str) -> Iterable[str]:
        """Locate any checksum.md5 files located inside a directory.

        Notes:
            This searches a path recursively.
        """
        for search_root, _, files in os.walk(root):
            for file_ in files:
                if file_ != "checksum.md5":
                    continue
                yield os.path.join(search_root, file_)

    def discover_task_metadata(self,
                               initial_results: List[
                                   speedwagon.tasks.Result],
                               additional_data: Dict[str, None],
                               **user_args: str) -> List[Dict[str, str]]:
        """Read the values inside the checksum report."""
        jobs: List[Dict[str, str]] = []
        for result in initial_results:
            for file_to_check in result.data:
                new_job: Dict[str, str] = {
                    JobValues.EXPECTED_HASH.value:
                        file_to_check["expected_hash"],
                    JobValues.ITEM_FILENAME.value:
                        file_to_check["filename"],
                    JobValues.ROOT_PATH.value:
                        file_to_check["path"],
                    JobValues.SOURCE_REPORT.value:
                        file_to_check["source_report"],
                }
                jobs.append(new_job)
        return jobs

    def job_options(self) -> List[workflow.AbsOutputOptionDataType]:
        """Request user options.

        User Options include:
            * Input - path directory containing checksum files
        """
        input_folder = \
            speedwagon.workflow.DirectorySelect(UserArgs.INPUT.value)

        return [
            input_folder
        ]

    @staticmethod
    def validate_user_options(**user_args: str) -> bool:
        """Validate user options."""
        input_data = user_args[UserArgs.INPUT.value]
        if input_data is None:
            raise ValueError("Missing value in input")

        if not os.path.exists(input_data) or not os.path.isdir(input_data):
            raise ValueError("Invalid user arguments")
        return True

    def initial_task(self, task_builder: "speedwagon.tasks.TaskBuilder",
                     **user_args: str) -> None:
        """Add a task to read the checksum report files."""
        root = user_args['Input']
        for checksum_report_file in self.locate_checksum_files(root):
            task_builder.add_subtask(
                ReadChecksumReportTask(checksum_file=checksum_report_file))

    def create_new_task(
            self,
            task_builder: "speedwagon.tasks.TaskBuilder",
            **job_args: str
    ) -> None:
        """Create a checksum validation task."""
        filename = job_args['filename']
        file_path = job_args['path']
        expected_hash = job_args['expected_hash']
        source_report = job_args['source_report']
        task_builder.add_subtask(
            ValidateChecksumTask(file_name=filename,
                                 file_path=file_path,
                                 expected_hash=expected_hash,
                                 source_report=source_report))

    @classmethod
    def generate_report(cls,
                        results: List[speedwagon.tasks.Result],
                        **user_args: str) -> Optional[str]:
        """Generate a report for files failed checksum test."""
        def validation_result_filter(
                task_result: speedwagon.tasks.Result) -> bool:
            if task_result.source != ValidateChecksumTask:
                return False
            return True

        line_sep = "\n" + "-" * 60
        results_with_failures = cls.find_failed(
            cls._sort_results(
                map(lambda x: x.data,
                    filter(validation_result_filter, results))
            )
        )

        if len(results_with_failures) > 0:
            messages = []
            for checksum_file, failed_files in results_with_failures.items():
                status = f"{len(failed_files)} files " \
                         f"failed checksum validation."
                failed_files_bullets = [f"* {failure[ResultValues.FILENAME]}"
                                        for failure in failed_files]
                failure_list = "\n".join(failed_files_bullets)
                single_message = f"{checksum_file}" \
                                 f"\n\n{status}" \
                                 f"\n{failure_list}"
                messages.append(single_message)
            report = f"\n{line_sep}\n".join(messages)

        else:
            stats_message = f"All {len(results)} passed checksum validation."
            failure_list = ""
            report = f"Success" \
                     f"\n{stats_message}" \
                     f"\n{failure_list}"
        return report

    @classmethod
    def find_failed(
            cls,
            new_results: Dict[str, List[Dict[ResultValues, TaskResult]]]
    ) -> dict:
        """Locate failed results."""
        failed: DefaultDict[str, list] = collections.defaultdict(list)
        for checksum_file, results in new_results.items():

            for failed_item in filter(lambda it: not it[ResultValues.VALID],
                                      results):
                failed[checksum_file].append(failed_item)
        return dict(failed)

    @classmethod
    def _sort_results(
            cls,
            results: Iterable[Dict[ResultValues, Any]]
    ) -> Dict[str, List[Dict[ResultValues, TaskResult]]]:
        """Sort the data & put it into a dict with the source for the key.

        Args:
            results:

        Returns: Dictionary of organized data where the source is the key and
                 the value contains all the files updated

        """
        new_results: \
            DefaultDict[str, List[Dict[ResultValues, TaskResult]]] = \
            collections.defaultdict(list)

        sorted_results = sorted(results,
                                key=lambda it:
                                it[ResultValues.CHECKSUM_REPORT_FILE])
        for key, value in itertools.groupby(
                sorted_results,
                key=lambda it: it[ResultValues.CHECKSUM_REPORT_FILE]):

            for result_data in value:
                new_results[key].append(result_data)
        return dict(new_results)


class ReadChecksumReportTask(speedwagon.tasks.Subtask):

    def __init__(self, checksum_file: str) -> None:
        super().__init__()
        self._checksum_file = checksum_file

    def task_description(self) -> Optional[str]:
        return f"Reading {self._checksum_file}"

    def work(self) -> bool:
        results = []

        checksums = hathi_validate.process.extracts_checksums(
            self._checksum_file)

        for report_md5_hash, filename in checksums:
            new_job_to_do = {
                JobValues.EXPECTED_HASH.value:
                    report_md5_hash,
                JobValues.ITEM_FILENAME.value:
                    filename,
                JobValues.ROOT_PATH.value:
                    os.path.dirname(self._checksum_file),
                JobValues.SOURCE_REPORT.value:
                    self._checksum_file
            }
            results.append(new_job_to_do)
        self.set_results(results)
        return True


class ValidateChecksumTask(speedwagon.tasks.Subtask):
    name = "Validating File Checksum"

    def __init__(self,
                 file_name: str,
                 file_path: str,
                 expected_hash: str,
                 source_report: str) -> None:
        super().__init__()
        self._file_name = file_name
        self._file_path = file_path
        self._expected_hash = expected_hash
        self._source_report = source_report

    def task_description(self) -> Optional[str]:
        return f"Validating checksum for {self._file_name}"

    def work(self) -> bool:
        self.log(f"Validating {self._file_name}")

        actual_md5 = hathi_validate.process.calculate_md5(
            os.path.join(self._file_path, self._file_name))

        result: Dict[ResultValues, TaskResult] = {
            ResultValues.FILENAME: self._file_name,
            ResultValues.PATH: self._file_path,
            ResultValues.CHECKSUM_REPORT_FILE: self._source_report
        }

        standard_comparison = CaseSensitiveComparison()
        valid_but_warnable_strategy = CaseInsensitiveComparison()

        if standard_comparison.compare(actual_md5, self._expected_hash):
            result[ResultValues.VALID] = True

        elif valid_but_warnable_strategy.compare(actual_md5,
                                                 self._expected_hash):
            result[ResultValues.VALID] = True
            self.log(f"Hash for {self._file_name} is valid but is presented"
                     f"in a different format than expected."
                     f"Expected: {self._expected_hash}. Actual: {actual_md5}")
        else:
            self.log(f"Hash mismatch for {self._file_name}. "
                     f"Expected: {self._expected_hash}. Actual: {actual_md5}")
            result[ResultValues.VALID] = False

        self.set_results(result)

        return True


class AbsComparisonMethod(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def compare(self, a: str, b: str) -> bool:
        pass


class CaseSensitiveComparison(AbsComparisonMethod):

    def compare(self, a: str, b: str) -> bool:
        return a == b


class CaseInsensitiveComparison(AbsComparisonMethod):

    def compare(self, a: str, b: str) -> bool:
        return a.lower() == b.lower()


class VerifyChecksumBatchSingleWorkflow(Workflow):
    """Verify Checksum Batch."""

    name = "Verify Checksum Batch [Single]"
    description = "Verify checksum values in checksum batch file, report " \
                  "errors. Verifies every entry in the checksum.md5 files " \
                  "matches expected hash value for the actual file.  Tool " \
                  "reports discrepancies in console of Speedwagon." \
                  "\n" \
                  "Input is a text file containing a list of multiple files " \
                  "and their md5 values. The listed files are expected to " \
                  "be siblings to the checksum file."

    @staticmethod
    def validate_user_options(**user_args: str) -> bool:
        """Validate user options."""
        input_data = user_args[UserArgs.INPUT.value]
        if input_data is None:
            raise ValueError("Missing value in input")

        if not os.path.exists(input_data) or os.path.isdir(input_data):
            raise ValueError("Invalid user arguments")
        return True

    def discover_task_metadata(self,
                               initial_results: List[
                                   speedwagon.tasks.Result],
                               additional_data: Dict[str, None],
                               **user_args: str) -> List[dict]:
        """Discover metadata needed for generating a task."""
        jobs: List[Dict[str, str]] = []
        relative_path = os.path.dirname(user_args[UserArgs.INPUT.value])
        checksum_report_file = os.path.abspath(user_args[UserArgs.INPUT.value])

        for report_md5_hash, filename in \
                sorted(hathi_validate.process.extracts_checksums(
                    checksum_report_file),
                    key=lambda x: x[1]
                ):

            new_job: Dict[str, str] = {
                JobValues.EXPECTED_HASH.value: report_md5_hash,
                JobValues.ITEM_FILENAME.value: filename,
                JobValues.ROOT_PATH.value: relative_path,
                JobValues.SOURCE_REPORT.value: checksum_report_file
            }
            jobs.append(new_job)
        return jobs

    def job_options(self) -> List[workflow.AbsOutputOptionDataType]:
        """Request user options.

        User Options include:
            * Input - path checksum file
        """
        input_file = workflow.FileSelectData(UserArgs.INPUT.value)
        input_file.filter = "Checksum files (*.md5)"
        return [
            input_file
        ]

    def create_new_task(
            self,
            task_builder: "speedwagon.tasks.TaskBuilder",
            **job_args: str
    ) -> None:
        """Generate a new checksum task."""
        new_task = ChecksumTask(**job_args)
        task_builder.add_subtask(new_task)

    @classmethod
    @add_report_borders
    def generate_report(
            cls,
            results: List[speedwagon.tasks.Result],
            **user_args: str
    ) -> Optional[str]:
        """Generate a report for files failed checksum test."""
        results = [res.data for res in results]

        line_sep = "\n" + "-" * 60
        sorted_results = cls.sort_results(results)
        results_with_failures = cls.find_failed(sorted_results)

        if len(results_with_failures) > 0:
            messages = []
            for checksum_file, failed_files in results_with_failures.items():
                status = \
                    f"{len(failed_files)} files failed checksum validation."

                failed_files_bullets = [
                    f"* {failure[ResultValues.FILENAME]}"
                    for failure in failed_files
                ]

                failure_list = "\n".join(failed_files_bullets)
                single_message = f"{checksum_file}" \
                                 f"\n\n{status}" \
                                 f"\n{failure_list}"
                messages.append(single_message)

            report = f"\n{line_sep}\n".join(messages)

        else:
            stats_message = f"All {len(results)} passed checksum validation."
            failure_list = ""
            report = f"Success" \
                     f"\n{stats_message}" \
                     f"\n{failure_list}"
        return report

    @classmethod
    def sort_results(cls, results: List[Any]) -> \
            Dict[str, List[Dict[ResultValues, TaskResult]]]:
        """Sort the data and put it into a dictionary using source as the key.

        Args:
            results:

        Returns: Dictionary of organized data where the source is the key and
                 the value contains all the files updated

        """
        new_results: DefaultDict[str, List[Dict[ResultValues, TaskResult]]] = \
            collections.defaultdict(list)

        sorted_results = sorted(
            results, key=lambda it: it[ResultValues.CHECKSUM_REPORT_FILE]
        )

        for key, value in itertools.groupby(
                sorted_results,
                key=lambda it: it[ResultValues.CHECKSUM_REPORT_FILE]
        ):
            for result_data in value:
                new_results[key].append(result_data)
        return dict(new_results)

    @classmethod
    def find_failed(
            cls,
            new_results: Dict[str, List[Dict[ResultValues, TaskResult]]]
    ) -> Dict[str, List[Dict[ResultValues, TaskResult]]]:
        """Locate failed results."""
        failed: DefaultDict[str, List[Dict[ResultValues, TaskResult]]] = \
            collections.defaultdict(list)

        for checksum_file, results in new_results.items():

            for failed_item in \
                    filter(lambda it: not it[ResultValues.VALID], results):

                failed[checksum_file].append(failed_item)
        return dict(failed)


class ChecksumTask(speedwagon.tasks.Subtask):
    name = "Verifying file checksum"

    def __init__(self, *_: None, **kwargs: Union[str, bool]) -> None:
        super().__init__()
        self._kwarg = kwargs

    def task_description(self) -> Optional[str]:
        return f"Calculating file checksum for " \
               f"{self._kwarg[JobValues.ITEM_FILENAME.value]}"

    def work(self) -> bool:
        filename = typing.cast(str, self._kwarg[JobValues.ITEM_FILENAME.value])

        source_report = \
            typing.cast(str, self._kwarg[JobValues.SOURCE_REPORT.value])

        expected = typing.cast(str, self._kwarg[JobValues.EXPECTED_HASH.value])

        checksum_path = \
            typing.cast(str, self._kwarg[JobValues.ROOT_PATH.value])

        full_path = os.path.join(checksum_path, filename)
        actual_md5: str = hathi_validate.process.calculate_md5(full_path)

        result: Dict[ResultValues, Union[str, bool]] = {
            ResultValues.FILENAME: filename,
            ResultValues.PATH: checksum_path,
            ResultValues.CHECKSUM_REPORT_FILE: source_report
        }

        standard_comparison = CaseSensitiveComparison()

        valid_but_warnable_strategy = CaseInsensitiveComparison()

        if standard_comparison.compare(actual_md5, expected):
            result[ResultValues.VALID] = True
        elif valid_but_warnable_strategy.compare(actual_md5, expected):
            result[ResultValues.VALID] = True
            self.log(f"Hash for {filename} is valid but is presented"
                     f"in a different format than expected."
                     f"Expected: {expected}. Actual: {actual_md5}")
        else:
            self.log(f"Hash mismatch for {filename}. "
                     f"Expected: {expected}. Actual: {actual_md5}")
            result[ResultValues.VALID] = False

        self.set_results(result)
        return True
