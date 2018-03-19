import collections
import typing
import enum
import os

import itertools
from PyQt5 import QtWidgets

from forseti.worker import ProcessJobWorker
from forseti.job import AbsTool
# from .options import ToolOptionDataType
from forseti.tools import options
from forseti import worker
# from pyhathiprep import checksum
from hathi_checksum import checksum_report, update_report
from hathi_checksum import utils as hathi_checksum_utils


class ResultValues(enum.Enum):
    FILENAME = "filename"
    CHECKSUM_SOURCE = "checksum_source"
    CHECKSUM_ACTUAL = "checksum_actual"
    CHECKSUM_EXPECTED = "checksum_expected"


class UserArgs(enum.Enum):
    INPUT = "Input"


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


def find_outdated(results: typing.List[typing.Dict[ResultValues, str]]):
    for result in results:
        if result[ResultValues.CHECKSUM_ACTUAL] != result[ResultValues.CHECKSUM_EXPECTED]:
            yield result


class UpdateChecksum(AbsTool):
    @classmethod
    def generate_report(cls, *args, **kwargs):
        results = kwargs['results']
        user_args = kwargs['user_args']
        outdated_items = cls.sort_results(results)

        report_lines = []
        if outdated_items:
            for checksum_report_name, outdated_files_ in outdated_items.items():
                report_lines.append(
                    "Updated md5 entries for [{}] in {}".format(", ".join(outdated_files_), checksum_report_name))

        if report_lines:
            return "\n".join(report_lines)
        else:
            return "No outdated entries found in {}".format(user_args[UserArgs.INPUT.value])

    @classmethod
    def sort_results(cls, results) -> typing.Dict[str, typing.List[str]]:
        """ Sort the data and put it into a dictionary with the source as the key

        Args:
            results:

        Returns: Dictionary of organized data where the source is the key and the value contains all the files updated

        """
        outdated_items = sorted([
            (res[ResultValues.FILENAME], res[ResultValues.CHECKSUM_SOURCE]) for res in find_outdated(results)],
            # (res['filename'], res['checksum_source']) for res in find_outdated(results)],
            key=lambda it: it[1])
        outdated_items_data: typing.DefaultDict[str, list] = collections.defaultdict(list)
        for k, v in itertools.groupby(outdated_items, key=lambda it: it[1]):
            for file_ in v:
                outdated_items_data[k].append(file_[0])
        return dict(outdated_items_data)

    @staticmethod
    def on_completion(*args, **kwargs):
        for outdated_result in find_outdated(kwargs['results']):
            update_report.update_hash_value(
                outdated_result[ResultValues.CHECKSUM_SOURCE],
                outdated_result[ResultValues.FILENAME],
                outdated_result[ResultValues.CHECKSUM_ACTUAL]
            )


class UpdateChecksumBatchSingle(UpdateChecksum):
    name = "Update Checksum Batch [Single]"
    description = "Updates the checksum hash in a checksum.md5 file" \
                  "\nInput: checksum.md5 file"

    # "\nInput: path to a root folder"

    @staticmethod
    def new_job() -> typing.Type[worker.ProcessJobWorker]:
        return ChecksumJob

    @staticmethod
    def discover_task_metadata(**user_args):
        jobs = []
        md5_report = user_args[UserArgs.INPUT.value]
        # md5_report = user_args['input']
        path = os.path.dirname(os.path.abspath(user_args[UserArgs.INPUT.value]))
        # path = os.path.dirname(os.path.abspath(user_args['input']))
        for report_md5_hash, filename in checksum_report.extracts_checksums(md5_report):
            job = {
                "filename": filename,
                "report_md5_hash": report_md5_hash,
                "location": path,
                "checksum_source": md5_report
            }
            jobs.append(job)
        return jobs
        pass

    @staticmethod
    def validate_user_options(**user_args):
        input_data = user_args[UserArgs.INPUT.value]
        # input_data = user_args["input"]

        if input_data is None:
            raise ValueError("Missing value in input")
        if not os.path.exists(input_data) or not os.path.isfile(input_data):
            raise ValueError("Invalid user arguments")
        if os.path.basename(input_data) != "checksum.md5":
            raise ValueError("Selected input is not a checksum.md5 file")

    @staticmethod
    def get_user_options() -> typing.List[options.UserOption2]:
        return [
            options.UserOptionCustomDataType(UserArgs.INPUT.value, ChecksumData),
        ]


class UpdateChecksumBatchMultiple(UpdateChecksum):
    name = "Update Checksum Batch [Multiple]"
    description = "Updates the checksum hash in all checksum.md5 file found in a path" \
                  "\nInput: path to a root folder"

    @staticmethod
    def new_job() -> typing.Type[worker.ProcessJobWorker]:
        return ChecksumJob

    @staticmethod
    def discover_task_metadata(**user_args) -> typing.List[dict]:
        jobs = []
        package_root = user_args[UserArgs.INPUT.value]
        # package_root = user_args['input']
        for root, dirs, files in os.walk(package_root):
            for file_ in files:
                if file_.lower() == "checksum.md5":
                    report = os.path.join(root, file_)
                    for filename, report_md5_hash in UpdateChecksumBatchMultiple.locate_files(report):
                        job = {
                            "filename": filename,
                            "report_md5_hash": report_md5_hash,
                            "location": root,
                            "checksum_source": report
                        }
                        jobs.append(job)
        return jobs

    @staticmethod
    def get_user_options() -> typing.List[options.UserOption2]:
        return [
            options.UserOptionCustomDataType(UserArgs.INPUT.value, options.FolderData),
        ]

    @staticmethod
    def validate_user_options(**user_args):
        input_data = user_args[UserArgs.INPUT.value]
        # input_data = user_args["input"]
        if input_data is None:
            raise ValueError("Missing value in input")

        if not os.path.exists(input_data) or not os.path.isdir(input_data):
            raise ValueError("Invalid user arguments")

    @staticmethod
    def locate_files(report) -> typing.Iterable[typing.Tuple[str, str]]:
        for report_md5_hash, filename in checksum_report.extracts_checksums(report):
            yield filename, report_md5_hash


class ChecksumJob(ProcessJobWorker):
    def process(self, *args, **kwargs):
        source_path = kwargs['location']
        source_file = kwargs['filename']
        report = kwargs['checksum_source']
        self.log(f"Calculating the md5 for {source_file}")
        hash_value = hathi_checksum_utils.calculate_md5(os.path.join(source_path, source_file))
        self.result = {
            ResultValues.FILENAME: source_file,
            ResultValues.CHECKSUM_ACTUAL: hash_value,
            ResultValues.CHECKSUM_EXPECTED: kwargs['report_md5_hash'],
            ResultValues.CHECKSUM_SOURCE: report
        }
