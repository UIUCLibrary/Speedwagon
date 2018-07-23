import os
import warnings
from typing import Iterable, Optional, List, Any

from uiucprescon import imagevalidate
from speedwagon import tasks
from speedwagon.job import AbsWorkflow
from speedwagon.tools import options as tool_options
import speedwagon.tasks
import enum


class UserArgs(enum.Enum):
    INPUT = "Input"


class JobValues(enum.Enum):
    ITEM_FILENAME = "filename"
    ROOT_PATH = "path"
    PROFILE_NAME = "profile_name"


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
                  "containing a series of tiff or jp2 files. " \
                  "\n" \
                  "\n" \
                  "Note: The HathiTrust JPEG 2000 profile does not check " \
                  "color space at this time."

    def _locate_checksum_files(self, root) -> Iterable[str]:
        for root, dirs, files in os.walk(root):
            for file_ in files:
                if file_ != "checksum.md5":
                    continue
                yield os.path.join(root, file_)

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data,
                               **user_args) -> List[dict]:
        new_tasks = []

        for image_file in initial_results[0].data:
            new_tasks .append({
                JobValues.ITEM_FILENAME.value: image_file,
                JobValues.PROFILE_NAME.value: user_args["Profile"]
            })
        return new_tasks

    def initial_task(self, task_builder: tasks.TaskBuilder,
                     **user_args) -> None:
        # profile = imagevalidate.get_profile(user_args["Profile"])

        task_builder.add_subtask(
            LocateImagesTask(user_args[UserArgs.INPUT.value],
                             user_args["Profile"])
        )

    def user_options(self):
        options = []

        input_option = \
            tool_options.UserOptionCustomDataType(UserArgs.INPUT.value,
                                                  tool_options.FolderData)

        profile_type = tool_options.ListSelection("Profile")

        for profile_name in imagevalidate.available_profiles():
            profile_type.add_selection(profile_name)

        options.append(input_option)
        options.append(profile_type)

        return options

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

        subtask = \
            ValidateImageMetadataTask(filename,
                                      job_args[JobValues.PROFILE_NAME.value])

        task_builder.add_subtask(subtask)

    @classmethod
    def generate_report(cls,
                        results: List[speedwagon.tasks.Result],
                        **user_args) -> Optional[str]:

        def validation_result_filter(
                task_result: speedwagon.tasks.Result) -> bool:
            if task_result.source != ValidateImageMetadataTask:
                return False
            return True

        def filter_only_invalid(task_result):
            if task_result[ResultValues.VALID]:
                return False
            else:
                return True

        def invalid_messages(task_result):
            source = task_result[ResultValues.FILENAME]
            messages = task_result[ResultValues.REPORT]
            message = "\n".join([
                f"{source}",
                messages
            ])
            return message

        data = [i for i in map(
            lambda x: x.data, filter(validation_result_filter, results))]

        line_sep = "\n" + "-" * 60
        total_results = len(data)
        filtered_data = filter(filter_only_invalid, data)
        data_points = list(map(invalid_messages, filtered_data))

        report_data = "\n\n".join(data_points)

        summary = "\n".join([
            f"Validated files located in: {user_args[UserArgs.INPUT.value]}",
            f"Total files checked: {total_results}",

        ])

        report = f"\n{line_sep}\n".join(
            [
                "\nReport:",
                summary,
                report_data,
                "\n"
            ]
        )
        return report


class LocateTiffImageTask(speedwagon.tasks.Subtask):

    def __init__(self, root) -> None:
        warnings.warn("Use LocateImagesTask instead", DeprecationWarning)
        super().__init__()
        self._root = root

    def work(self) -> bool:
        tiff_files = []
        for root, dirs, files in os.walk(self._root):
            for file_name in files:
                base, ext = os.path.splitext(file_name)
                if not ext.lower() == ".tif":
                    continue
                tiff_file = os.path.join(root, file_name)
                self.log(f"Found {tiff_file}")
                tiff_files.append(tiff_file)
        self.set_results(tiff_files)
        return True


class LocateImagesTask(speedwagon.tasks.Subtask):
    def __init__(self, root,
                 profile_name: str) -> None:
        super().__init__()
        self._root = root
        self._profile = imagevalidate.get_profile(profile_name)

    def work(self) -> bool:
        image_files = []
        for root, dirs, files in os.walk(self._root):
            for file_name in files:
                base, ext = os.path.splitext(file_name)
                if not ext.lower() in self._profile.valid_extensions:
                    continue
                image_file = os.path.join(root, file_name)
                self.log(f"Found {image_file}")
                image_files.append(image_file)
        self.set_results(image_files)
        return True


class ValidateImageMetadataTask(speedwagon.tasks.Subtask):
    def __init__(self, filename, profile_name: str) -> None:

        super().__init__()
        self._filename = filename
        self._profile = imagevalidate.get_profile(profile_name)

    def work(self) -> bool:
        self.log(f"Validating {self._filename}")

        profile_validator = imagevalidate.Profile(self._profile)

        try:
            report = profile_validator.validate(self._filename)
            is_valid = report.valid
            report_text = "\n* ".join(report.issues())
        except RuntimeError as e:
            is_valid = False
            report_text = str(e)
        self.log(f"Validating {self._filename} -- {is_valid}")

        result = {
            ResultValues.FILENAME: self._filename,
            ResultValues.VALID: is_valid,
            ResultValues.REPORT: f"* {report_text}"
        }

        self.set_results(result)
        return True
