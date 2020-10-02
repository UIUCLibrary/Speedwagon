import os
from typing import List, Any
from uiucprescon import imagevalidate

from PyQt5 import QtWidgets  # type: ignore

from speedwagon import tasks
from speedwagon.job import AbsWorkflow
from . import shared_custom_widgets as options


class ImageFile(options.AbsBrowseableWidget):
    def browse_clicked(self):
        selection = QtWidgets.QFileDialog.getOpenFileName(
            filter="Tiff files (*.tif)"
        )

        if selection[0]:
            self.data = selection[0]
            self.editingFinished.emit()


class TiffFileCheckData(options.AbsCustomData3):

    @classmethod
    def is_valid(cls, value) -> bool:
        if not value:
            return False

        if not os.path.exists(value):
            return False
        if os.path.splitext(value)[1].lower() == ".tif":
            print("No a Tiff file")
            return False
        return True

    @classmethod
    def edit_widget(cls) -> QtWidgets.QWidget:
        return ImageFile()


class ValidateImageMetadataWorkflow(AbsWorkflow):
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

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        jobs = []
        source_input = user_args["Input"]
        jobs.append({
            "source_file": source_input
        })
        return jobs

    def user_options(self):
        return [
            options.UserOptionCustomDataType("Input",
                                             TiffFileCheckData),
        ]

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        source_file = job_args["source_file"]
        new_task = MetadataValidatorTask(source_file)
        task_builder.add_subtask(new_task)

    @staticmethod
    def validate_user_options(**user_args):
        file_path = user_args["Input"]

        if not file_path:
            raise ValueError("No image selected")

        if not os.path.exists(file_path):
            raise ValueError(f"Unable to locate {file_path}")

        if not os.path.isfile(file_path):
            raise ValueError("Invalid input selection")


class MetadataValidatorTask(tasks.Subtask):

    def __init__(self, source_file) -> None:
        super().__init__()
        self._source_file = source_file

    def work(self):
        hathi_tiff_profile = imagevalidate.Profile(
            imagevalidate.profiles.HathiTiff())

        report = hathi_tiff_profile.validate(self._source_file)
        self.log(str(report))
        return True
