import os
from typing import Iterable, Optional, List, Any

from uiucprescon import imagevalidate
from speedwagon.job import AbsWorkflow
from speedwagon.tools import options
import speedwagon.tasks
import enum


class UserArgs(enum.Enum):
    INPUT = "Input"


class JobValues(enum.Enum):
    ITEM_FILENAME = "filename"
    ROOT_PATH = "path"


class ResultValues(enum.Enum):
    VALID = "valid"
    FILENAME = "filename"
    REPORT = "report"


class ValidateMetadataWorkflow(AbsWorkflow):
    name = "Validate Metadata"
    description = "Validate the metadata for images located inside a " \
                  "directory. " \
                  "\n" \
                  "\n" \
                  "Input is path that contains subdirectory which " \
                  "containing a series of tiff files."

    def _locate_checksum_files(self, root) -> Iterable[str]:
        for root, dirs, files in os.walk(root):
            for file_ in files:
                if file_ != "checksum.md5":
                    continue
                yield os.path.join(root, file_)

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data,
                               **user_args) -> List[dict]:
        def locate_tiffs(root_dir):
            for root, dirs, files in os.walk(root_dir):
                for file_name in files:
                    base, ext = os.path.splitext(file_name)
                    if not ext.lower() == ".tif":
                        continue
                    yield os.path.join(root, file_name)
        tasks = []
        for image_file in locate_tiffs(user_args[UserArgs.INPUT.value]):
            tasks.append({
                JobValues.ITEM_FILENAME.value: image_file
            })
        return tasks

    def user_options(self):
        return options.UserOptionCustomDataType(UserArgs.INPUT.value,
                                                options.FolderData),

    @staticmethod
    def validate_user_options(**user_args):
        input_data = user_args[UserArgs.INPUT.value]
        if input_data is None:
            raise ValueError("Missing value in input")

        if not os.path.exists(input_data) or not os.path.isdir(input_data):
            raise ValueError("Invalid user arguments")

    def create_new_task(self,
                        task_builder: "speedwagon.tasks.TaskBuilder",
                        **job_args):
        filename = job_args[JobValues.ITEM_FILENAME.value]
        subtask = ValidateImageMetadataTask(filename)

        task_builder.add_subtask(subtask)

    @classmethod
    def generate_report(cls,
                        results: List[speedwagon.tasks.Result],
                        **user_args) -> Optional[str]:
        total_results = len(results)
        summary = f"Total files checked: {total_results}"

        def validation_result_filter(
                task_result: speedwagon.tasks.Result) -> bool:
            if task_result.source != ValidateImageMetadataTask:
                return False
            return True

        def filter_only_invalid(task_result):
            return not task_result[ResultValues.VALID]

        def invalid_messages(task_result):
            message = task_result[ResultValues.REPORT]
            return message

        data = map(lambda x: x.data, filter(validation_result_filter, results))
        data = filter(filter_only_invalid, data)
        data_points = list(map(invalid_messages, data))
        line_sep = "\n" + "-" * 60
        report_data = "\n\n".join(list(data_points))

        report = f"\n{line_sep}\n".join(
            [
                "\nReport\n",
                summary,
                report_data,
                "\n"
            ]
        )
        return report


class ValidateImageMetadataTask(speedwagon.tasks.Subtask):
    def __init__(self, filename) -> None:
        super().__init__()
        self._filename = filename

    def work(self) -> bool:
        self.log(f"Validating {self._filename}")
        hathi_tiff_profile = imagevalidate.Profile(
            imagevalidate.profiles.HathiTiff())
        try:
            report = hathi_tiff_profile.validate(self._filename)
            is_valid = report.valid
            report_text = str(report)
        except RuntimeError as e:
            is_valid = False
            report_text = str(e)
        self.log(f"Validating {self._filename} -- {is_valid}")

        #
        #
        result = {
            ResultValues.FILENAME: self._filename,
            ResultValues.VALID: is_valid,
            ResultValues.REPORT: report_text
        }
        #
        self.set_results(result)
        #
        return True
