import abc
import collections
import itertools
import os
from typing import DefaultDict, Iterable, Optional, Dict, List, Any, Union

import hathi_validate.process

from speedwagon import tasks
from speedwagon.job import AbsWorkflow
from speedwagon.reports import add_report_borders
from . import shared_custom_widgets

import enum


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


class ChecksumWorkflow(AbsWorkflow):
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

    def _locate_checksum_files(self, root) -> Iterable[str]:
        for root, dirs, files in os.walk(root):
            for file_ in files:
                if file_ != "checksum.md5":
                    continue
                yield os.path.join(root, file_)

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data,
                               **user_args) -> List[dict]:
        jobs = []
        for result in initial_results:
            for file_to_check in result.data:
                new_job = {
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

    def user_options(self):
        return shared_custom_widgets.UserOptionCustomDataType(
            UserArgs.INPUT.value, shared_custom_widgets.FolderData),

    @staticmethod
    def validate_user_options(**user_args):
        input_data = user_args[UserArgs.INPUT.value]
        if input_data is None:
            raise ValueError("Missing value in input")

        if not os.path.exists(input_data) or not os.path.isdir(input_data):
            raise ValueError("Invalid user arguments")

    def initial_task(self, task_builder: tasks.TaskBuilder,
                     **user_args) -> None:
        root = user_args['Input']
        for checksum_report_file in self._locate_checksum_files(root):
            task_builder.add_subtask(
                ReadChecksumReportTask(checksum_file=checksum_report_file))

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
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
    def generate_report(cls, results: List[tasks.Result],
                        **user_args) -> Optional[str]:

        def validation_result_filter(
                task_result: tasks.Result) -> bool:
            if task_result.source != ValidateChecksumTask:
                return False
            return True

        data = map(lambda x: x.data, filter(validation_result_filter, results))
        line_sep = "\n" + "-" * 60
        sorted_results = cls._sort_results(data)
        results_with_failures = cls.find_failed(sorted_results)

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
            report = "\n{}\n".format(line_sep).join(messages)

        else:
            stats_message = f"All {len(results)} passed checksum validation."
            failure_list = ""
            report = f"Success" \
                     f"\n{stats_message}" \
                     f"\n{failure_list}"
        return report

    @classmethod
    def find_failed(cls,
                    new_results: Dict[str,
                                      List[Dict[ResultValues,
                                                Union[bool, str]]]]) -> dict:
        failed: DefaultDict[str, list] = collections.defaultdict(list)
        for checksum_file, results in new_results.items():

            for failed_item in filter(lambda it: not it[ResultValues.VALID],
                                      results):
                failed[checksum_file].append(failed_item)
        return dict(failed)

    @classmethod
    def _sort_results(cls, results) -> Dict[str,
                                            List[
                                                Dict[ResultValues,
                                                     Union[bool, str]]]]:
        """ Sort the data and put it into a dictionary with the source as the
        key

        Args:
            results:

        Returns: Dictionary of organized data where the source is the key and
                 the value contains all the files updated

        """
        new_results: DefaultDict[str, list] = collections.defaultdict(list)
        sorted_results = sorted(results,
                                key=lambda it:
                                it[ResultValues.CHECKSUM_REPORT_FILE])
        for k, v in itertools.groupby(sorted_results,
                                      key=lambda it:
                                      it[ResultValues.CHECKSUM_REPORT_FILE]):
            for result_data in v:
                new_results[k].append(result_data)
        return dict(new_results)


class ReadChecksumReportTask(tasks.Subtask):

    def __init__(self, checksum_file):
        super().__init__()
        self._checksum_file = checksum_file

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


class ValidateChecksumTask(tasks.Subtask):

    def __init__(self,
                 file_name,
                 file_path,
                 expected_hash,
                 source_report) -> None:
        super().__init__()
        self._file_name = file_name
        self._file_path = file_path
        self._expected_hash = expected_hash
        self._source_report = source_report

    def work(self) -> bool:
        self.log(f"Validating {self._file_name}")

        actual_md5 = hathi_validate.process.calculate_md5(
            os.path.join(self._file_path, self._file_name))

        result = {
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


class VerifyChecksumBatchSingleWorkflow(AbsWorkflow):
    name = "Verify Checksum Batch [Single]"
    description = "Verify checksum values in checksum batch file, report " \
                  "errors. Verifies every entry in the checksum.md5 files " \
                  "matches expected hash value for the actual file.  Tool " \
                  "reports discrepancies in console of Speedwagon." \
                  "\n" \
                  "Input is a text file containing a list of multiple files " \
                  "and their md5 values. The listed files are expected to " \
                  "be siblings to the checksum file."

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        jobs = []
        relative_path = os.path.dirname(user_args[UserArgs.INPUT.value])
        checksum_report_file = os.path.abspath(user_args[UserArgs.INPUT.value])

        for report_md5_hash, filename in \
                hathi_validate.process.extracts_checksums(
                    checksum_report_file
                ):

            new_job = {
                JobValues.EXPECTED_HASH.value: report_md5_hash,
                JobValues.ITEM_FILENAME.value: filename,
                JobValues.ROOT_PATH.value: relative_path,
                JobValues.SOURCE_REPORT.value: checksum_report_file
            }
            jobs.append(new_job)
        return jobs

    def user_options(self):
        return [
            shared_custom_widgets.UserOptionCustomDataType(
                UserArgs.INPUT.value, shared_custom_widgets.ChecksumData),
        ]

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        new_task = ChecksumTask(**job_args)
        task_builder.add_subtask(new_task)

    @classmethod
    @add_report_borders
    def generate_report(cls, results: List[tasks.Result], **user_args) -> \
            Optional[str]:
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
            report = "\n{}\n".format(line_sep).join(messages)

        else:
            stats_message = f"All {len(results)} passed checksum validation."
            failure_list = ""
            report = f"Success" \
                     f"\n{stats_message}" \
                     f"\n{failure_list}"
        return report

    @classmethod
    def sort_results(cls, results) -> \
            Dict[str, List[Dict[ResultValues, Union[bool, str]]]]:

        """ Sort the data and put it into a dictionary with the source as the
        key

        Args:
            results:

        Returns: Dictionary of organized data where the source is the key and
                 the value contains all the files updated

        """
        new_results: DefaultDict[str, list] = \
            collections.defaultdict(list)

        sorted_results = sorted(
            results, key=lambda it: it[ResultValues.CHECKSUM_REPORT_FILE]
        )

        for k, v in itertools.groupby(
                sorted_results,
                key=lambda it: it[ResultValues.CHECKSUM_REPORT_FILE]
        ):
            for result_data in v:
                new_results[k].append(result_data)
        return dict(new_results)

    @classmethod
    def find_failed(cls, new_results: Dict[str,
                                           List[Dict[ResultValues,
                                                     Union[bool,
                                                           str]]]]) -> dict:

        failed: DefaultDict[str, list] = collections.defaultdict(list)

        for checksum_file, results in new_results.items():

            for failed_item in \
                    filter(lambda it: not it[ResultValues.VALID], results):

                failed[checksum_file].append(failed_item)
        return dict(failed)


class ChecksumTask(tasks.Subtask):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self._args = args
        self._kwarg = kwargs

    def work(self) -> bool:
        filename = self._kwarg[JobValues.ITEM_FILENAME.value]
        source_report = self._kwarg[JobValues.SOURCE_REPORT.value]
        expected = self._kwarg[JobValues.EXPECTED_HASH.value]
        checksum_path = self._kwarg[JobValues.ROOT_PATH.value]
        full_path = os.path.join(checksum_path, filename)
        self.log("Calculating MD5 for {}".format(filename))
        actual_md5 = hathi_validate.process.calculate_md5(full_path)
        result = {
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
