"""Workflow for validating image metadata."""

import os
from typing import List, Any, Optional
from uiucprescon import imagevalidate

import speedwagon
from speedwagon.job import Workflow

__all__ = ['ValidateImageMetadataWorkflow']

from .. import workflow


class ValidateImageMetadataWorkflow(Workflow):
    name = "Validate Tiff Image Metadata for HathiTrust"
    description = "Validate the metadata located within a tiff file. " \
                  "Validates the technical metadata to include x and why " \
                  "resolution, bit depth and color space for images located " \
                  "inside a directory.  The tool also verifies values exist " \
                  "for address, city, state, zip code, country, phone " \
                  "number insuring the provenance of the file. " \
                  "\n" \
                  "Input is path that contains subdirectory which " \
                  "containing a series of tiff files."

    active = True

    def discover_task_metadata(self,
                               initial_results: List[Any],
                               additional_data,
                               **user_args: str) -> List[dict]:
        jobs = []
        source_input = user_args["Input"]
        jobs.append({
            "source_file": source_input
        })
        return jobs

    def get_user_options(self) -> List[workflow.AbsOutputOptionDataType]:
        return [
            workflow.DirectorySelect("Input")
        ]

    def create_new_task(
            self,
            task_builder: "speedwagon.tasks.TaskBuilder",
            **job_args: str
    ) -> None:

        source_file = job_args["source_file"]
        new_task = MetadataValidatorTask(source_file)
        task_builder.add_subtask(new_task)

    @staticmethod
    def validate_user_options(**user_args: str) -> bool:
        file_path = user_args["Input"]

        if not file_path:
            raise ValueError("No image selected")

        if not os.path.exists(file_path):
            raise ValueError(f"Unable to locate {file_path}")

        if not os.path.isfile(file_path):
            raise ValueError("Invalid input selection")
        return True


class MetadataValidatorTask(speedwagon.tasks.Subtask):
    name = "Metadata Validation"

    def __init__(self, source_file: str) -> None:
        super().__init__()
        self._source_file = source_file

    def task_description(self) -> Optional[str]:
        return f"Validating Metadata for {self._source_file}"

    def work(self) -> bool:
        hathi_tiff_profile = imagevalidate.Profile(
            imagevalidate.get_profile('HathiTrust Tiff')
        )

        report = hathi_tiff_profile.validate(self._source_file)
        self.log(str(report))
        return True
