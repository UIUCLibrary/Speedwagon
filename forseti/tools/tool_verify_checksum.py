import collections
import logging
import os
import typing

import itertools
from PyQt5 import QtWidgets

# from forseti.worker import ProcessJobWorker
# from .abstool import AbsTool
# from .options import ToolOptionDataType, UserOptionPythonDataType
from forseti.tools import options
import forseti.worker
import forseti.job
# from forseti import worker, job
import hathi_validate

from hathi_validate import process

import enum


class UserArgs(enum.Enum):
    INPUT = "Input"


class ResultValues(enum.Enum):
    VALID = "valid"
    FILENAME = "filename"
    PATH = "path"
    CHECKSUM_REPORT_FILE = "checksum_report_file"


class JobValues(enum.Enum):
    SOURCE_REPORT = "source_report"
    EXPECTED_HASH = "expected_hash"
    ITEM_FILENAME = "filename"
    ROOT_PATH = "path"


class ChecksumFile(options.AbsBrowseableWidget):
    def browse_clicked(self):
        selection = QtWidgets.QFileDialog.getOpenFileName(filter="Checksum files (*.md5)")
        if selection[0]:
            self.data = selection[0]
            self.editingFinished.emit()


class ChecksumData(options.AbsCustomData2):

    @classmethod
    def is_valid(cls, value) -> bool:
        if not os.path.exists(value):
            return False
        if os.path.basename(value) == "checksum":
            print("No a checksum file")
            return False
        return True

    @classmethod
    def edit_widget(cls) -> QtWidgets.QWidget:
        return ChecksumFile()


class VerifyChecksum(forseti.job.AbsTool):

    @staticmethod
    def new_job() -> typing.Type["forseti.worker.ProcessJobWorker"]:
        return ChecksumJob

    @classmethod
    def generate_report(cls, *args, **kwargs):
        results = kwargs['results']
        line_sep = "\n" + "-" * 60
        sorted_results = cls.sort_results(results)
        results_with_failures = cls.find_failed(sorted_results)

        if len(results_with_failures) > 0:
            messages = []
            for checksum_file, failed_files in results_with_failures.items():
                status = f"{len(failed_files)} files failed checksum validation."
                failed_files_bullets = [f"* {failure[ResultValues.FILENAME]}" for failure in failed_files]
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
    def sort_results(cls, results) -> typing.Dict[str, typing.List[typing.Dict[ResultValues, typing.Union[bool, str]]]]:
        """ Sort the data and put it into a dictionary with the source as the key

        Args:
            results:

        Returns: Dictionary of organized data where the source is the key and the value contains all the files updated

        """
        new_results: typing.DefaultDict[str, list] = collections.defaultdict(list)
        sorted_results = sorted(results, key=lambda it: it[ResultValues.CHECKSUM_REPORT_FILE])
        for k, v in itertools.groupby(sorted_results, key=lambda it: it[ResultValues.CHECKSUM_REPORT_FILE]):
            for result_data in v:
                new_results[k].append(result_data)
        return dict(new_results)

    @classmethod
    def find_failed(cls, new_results: typing.Dict[str,
                                                  typing.List[
                                                      typing.Dict[ResultValues,
                                                                  typing.Union[bool, str]]]]) -> dict:
        failed: typing.DefaultDict[str, list] = collections.defaultdict(list)
        for checksum_file, results in new_results.items():

            for failed_item in filter(lambda it: not it[ResultValues.VALID], results):
                failed[checksum_file].append(failed_item)
        return dict(failed)


class VerifyChecksumBatchSingle(VerifyChecksum):
    name = "Verify Checksum Batch [Single]"
    description = "Verify checksum values in checksum batch file, report errors. " \
                  "\n\nInput is a text file containing a list of multiple files and their md5 values. The listed files " \
                  "are expected to be siblings to the checksum file."

    @staticmethod
    def discover_task_metadata(**user_args):
        jobs = []
        relative_path = os.path.dirname(user_args[UserArgs.INPUT.value])
        checksum_report_file = os.path.abspath(user_args[UserArgs.INPUT.value])

        for report_md5_hash, filename in hathi_validate.process.extracts_checksums(checksum_report_file):
            new_job = {
                JobValues.EXPECTED_HASH.value: report_md5_hash,
                JobValues.ITEM_FILENAME.value: filename,
                JobValues.ROOT_PATH.value: relative_path,
                JobValues.SOURCE_REPORT.value: checksum_report_file
            }
            jobs.append(new_job)
        return jobs

    @staticmethod
    def get_user_options() -> typing.List[options.UserOption2]:
        return [
            options.UserOptionCustomDataType(UserArgs.INPUT.value, ChecksumData),

        ]

    @staticmethod
    def validate_user_options(**user_args):
        input_data = user_args[UserArgs.INPUT.value]
        if input_data is None:
            raise ValueError("Missing value in input")
        if not os.path.exists(input_data) or not os.path.splitext(input_data)[1] == ".md5":
            raise ValueError("Invalid user arguments")


class VerifyChecksumBatchMultiple(VerifyChecksum):
    name = "Verify Checksum Batch [Multiple]"
    description = "Verify checksum values in checksum batch file, report errors. " \
                  "\n\nInput is path that contains subdirectory which a text file containing a " \
                  "list of multiple files and their md5 values. The listed files are expected to be siblings to the " \
                  "checksum file."
    active = False

    @staticmethod
    def discover_task_metadata(**user_args) -> typing.List[dict]:
        jobs = []
        user_input = user_args[UserArgs.INPUT.value]
        for root, dirs, files in os.walk(os.path.abspath(user_input)):
            for file_ in files:
                if file_ != "checksum.md5":
                    continue

                checksum_report_file = os.path.join(root, file_)
                for report_md5_hash, filename in hathi_validate.process.extracts_checksums(checksum_report_file):
                    new_job = {
                        JobValues.EXPECTED_HASH.value: report_md5_hash,
                        JobValues.ITEM_FILENAME.value: filename,
                        JobValues.ROOT_PATH.value: root,
                        JobValues.SOURCE_REPORT.value: checksum_report_file
                    }
                    jobs.append(new_job)
        return jobs

    @staticmethod
    def get_user_options() -> typing.List[options.UserOption2]:
        return [
            options.UserOptionCustomDataType(UserArgs.INPUT.value, options.FolderData),
        ]

    @staticmethod
    def validate_user_options(**user_args):
        input_data = user_args[UserArgs.INPUT.value]
        if input_data is None:
            raise ValueError("Missing value in input")

        if not os.path.exists(input_data) or not os.path.isdir(input_data):
            raise ValueError("Invalid user arguments")


class ChecksumJob(forseti.worker.ProcessJobWorker):
    logger = logging.getLogger(hathi_validate.__name__)

    def process(self, *args, **kwargs):
        # self.logger.setLevel(logging.DEBUG)
        handler = forseti.worker.GuiLogHandler(self.log)
        self.logger.addHandler(handler)
        filename = kwargs[JobValues.ITEM_FILENAME.value]
        # filename = kwargs['filename']
        source_report = kwargs[JobValues.SOURCE_REPORT.value]
        expected = kwargs[JobValues.EXPECTED_HASH.value]
        checksum_path = kwargs[JobValues.ROOT_PATH.value]
        full_path = os.path.join(checksum_path, filename)
        # self.logger.debug("Starting with {}".format(full_path))
        self.log("Calculating MD5 for {}".format(filename))
        # self.logger.debug("Arguments = {}".format(kwargs) )
        # self.logger.debug("Calculating md5 for {}".format(full_path))
        actual_md5 = process.calculate_md5(full_path)
        # self.logger.debug("Comparing {}".format(filename))
        result = {
            ResultValues.FILENAME: filename,
            ResultValues.PATH: checksum_path,
            ResultValues.CHECKSUM_REPORT_FILE: source_report
        }
        # task_result = {
        #     "filename": filename,
        #     "path": kwargs['checksum_path'],
        # }
        if expected != actual_md5:
            self.log(f"Hash mismatch for {filename}. Expected: {expected}. Actual: {actual_md5}")
            result[ResultValues.VALID] = False
        else:
            self.log("MD5 for {} matches".format(filename))
            result[ResultValues.VALID] = True
        # if expected != actual_md5:
        #     self.log(f"Hash mismatch for {filename}. Expected: {expected}. Actual: {actual_md5}")
        #     task_result['valid'] = False
        # else:
        #     task_result['valid'] = True
        self.result = result
        self.logger.debug("Done validating {}".format(filename))
        # logging.debug("Done with {}".format(filename))

        self.logger.removeHandler(handler)
        # self.log("comparing checksum to expected value")
        # return ""
