import enum
import os
import typing
from typing import List, Any
from uiucprescon import imagevalidate

from PyQt5 import QtWidgets

from speedwagon import worker
from speedwagon.job import AbsTool, AbsWorkflow
from speedwagon.tools import options
from speedwagon.worker import ProcessJobWorker


class UserArgs(enum.Enum):
    INPUT = "Input"


class JobValues(enum.Enum):
    SOURCE_FILE = "source_file"


class ImageFile(options.AbsBrowseableWidget):
    def browse_clicked(self):
        selection = QtWidgets.QFileDialog.getOpenFileName(
            filter="Tiff files (*.tif)"
        )

        if selection[0]:
            self.data = selection[0]
            self.editingFinished.emit()


class TiffFileCheckData(options.AbsCustomData2):

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


class ValidateImageMetadata(AbsTool):
    name = "Validate Tiff Image Metadata for HathiTrust"
    description = "Validate the metadata located within a tiff file."

    @staticmethod
    def new_job() -> typing.Type[worker.ProcessJobWorker]:
        return MetadataValidator

    @staticmethod
    def get_user_options() -> typing.List[options.UserOption2]:
        return [
            options.UserOptionCustomDataType(UserArgs.INPUT.value,
                                             TiffFileCheckData),
        ]

    def discover_task_metadata(self, **user_args) -> typing.List[dict]:
        jobs = []
        source_input = user_args[UserArgs.INPUT.value]
        jobs.append({
            JobValues.SOURCE_FILE.value: source_input
        })
        return jobs

    @staticmethod
    def validate_user_options(**user_args):
        file_path = user_args[UserArgs.INPUT.value]

        if not file_path:
            raise ValueError("No image selected")

        if not os.path.exists(file_path):
            raise ValueError(f"Unable to locate {file_path}")

        if not os.path.isfile(file_path):
            raise ValueError(f"Invalid input selection")


class MetadataValidator(ProcessJobWorker):
    def process(self, *args, **kwargs):
        source_file = kwargs[JobValues.SOURCE_FILE.value]
        hathi_tiff_profile = imagevalidate.Profile(
            imagevalidate.profiles.HathiTiff())

        report = hathi_tiff_profile.validate(source_file)
        self.log(str(report))


class ValidateImageMetadataWorkflow(AbsWorkflow):
    name = "0 EXPERIMENTAL " \
           "Validate Tiff Image Metadata for HathiTrust"
    description = "Validate the metadata located within a tiff file."

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        return ValidateImageMetadata.discover_task_metadata(**user_args)

    def user_options(self):
        return ValidateImageMetadata.get_user_options()
