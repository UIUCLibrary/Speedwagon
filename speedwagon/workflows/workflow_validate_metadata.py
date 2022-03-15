"""Validating technical metadata."""

import os
import typing
from typing import Optional, List, Any
import enum

from uiucprescon import imagevalidate

import speedwagon
import speedwagon.workflow
import speedwagon.tasks.validation
from speedwagon.job import Workflow

__all__ = ['ValidateMetadataWorkflow']


class UserArgs(enum.Enum):
    INPUT = "Input"


class JobValues(enum.Enum):
    ITEM_FILENAME = "filename"
    ROOT_PATH = "path"
    PROFILE_NAME = "profile_name"


class ValidateMetadataWorkflow(Workflow):
    name = "Validate Metadata"
    description = "Validates the technical metadata for JP2000 files to " \
                  "include x and why resolution, bit depth and color space " \
                  "for images located inside a directory.  The tool also " \
                  "verifies values exist for address, city, state, zip " \
                  "code, country, phone number insuring the provenance of " \
                  "the file." \
                  "\n" \
                  "Input is path that contains subdirectory which " \
                  "containing a series of jp2 files."

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data,
                               **user_args) -> List[dict]:
        new_tasks = []

        for image_file in initial_results[0].data:
            new_tasks.append({
                JobValues.ITEM_FILENAME.value: image_file,
                JobValues.PROFILE_NAME.value: user_args["Profile"]
            })
        return new_tasks

    def initial_task(
            self,
            task_builder: "speedwagon.tasks.TaskBuilder",
            **user_args
    ) -> None:

        task_builder.add_subtask(
            LocateImagesTask(
                user_args[UserArgs.INPUT.value],
                user_args["Profile"]
            )
        )

    def get_user_options(
            self
    ) -> List[speedwagon.workflow.AbsOutputOptionDataType]:
        input_option = \
            speedwagon.workflow.DirectorySelect(UserArgs.INPUT.value)

        profile_type = speedwagon.workflow.DropDownSelection("Profile")
        profile_type.placeholder_text = "Select a Profile"

        for profile_name in imagevalidate.available_profiles():
            profile_type.add_selection(profile_name)

        return [
            input_option,
            profile_type
        ]

    @staticmethod
    def validate_user_options(**user_args: str) -> bool:
        input_data = user_args[UserArgs.INPUT.value]
        if input_data is None:
            raise ValueError("Missing value in input")

        if not os.path.exists(input_data) or not os.path.isdir(input_data):
            raise ValueError("Invalid user arguments")
        return True

    def create_new_task(self,
                        task_builder: "speedwagon.tasks.TaskBuilder",
                        **job_args: str):
        filename = job_args[JobValues.ITEM_FILENAME.value]

        subtask = \
            speedwagon.tasks.validation.ValidateImageMetadataTask(
                filename,
                job_args[JobValues.PROFILE_NAME.value]
            )

        task_builder.add_subtask(subtask)

    @classmethod
    def generate_report(cls,
                        results: List[speedwagon.tasks.Result],
                        **user_args) -> Optional[str]:
        result_keys = \
            speedwagon.tasks.validation.ValidateImageMetadataTask.ResultValues

        def validation_result_filter(
                task_result: speedwagon.tasks.Result
        ) -> bool:
            if task_result.source != \
                    speedwagon.tasks.validation.ValidateImageMetadataTask:
                return False
            return True

        def filter_only_invalid(task_result) -> bool:
            if task_result[result_keys.VALID]:
                return False
            return True

        def invalid_messages(task_result) -> str:
            source = task_result[result_keys.FILENAME]

            messages = task_result[result_keys.REPORT]

            message = "\n".join([
                f"{source}",
                messages
            ])
            return message

        data = list(
            map(lambda x: x.data, filter(validation_result_filter, results))
        )

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


class LocateImagesTask(speedwagon.tasks.Subtask):
    name = "Locate Image Files"

    def __init__(self,
                 root: str,
                 profile_name: str) -> None:
        super().__init__()
        self._root = root

        self._profile = typing.cast(
            imagevalidate.profiles.AbsProfile,
            imagevalidate.get_profile(profile_name)
        )

    def task_description(self) -> Optional[str]:
        return f"Locating images in {self._root}"

    def work(self) -> bool:
        image_files = []
        for root, _, files in os.walk(self._root):
            for file_name in files:
                _, ext = os.path.splitext(file_name)
                if not ext.lower() in self._profile.valid_extensions:
                    continue
                image_file = os.path.join(root, file_name)
                self.log(f"Found {image_file}")
                image_files.append(image_file)
        self.set_results(image_files)
        return True
