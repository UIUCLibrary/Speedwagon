import enum
import logging
import typing

import os
from contextlib import contextmanager
from typing import List, Any

from speedwagon import worker
from speedwagon.job import AbsTool, AbsWorkflow
from speedwagon.worker import ProcessJobWorker, GuiLogHandler
from speedwagon.tools import options
import hathizip.process
import hathizip


class UserArgs(enum.Enum):
    SOURCE = "Source"
    OUTPUT = "Output"


class JobValues(enum.Enum):
    SOURCE_PATH = "source_path"
    DESTINATION_PATH = "destination_path"


class ZipPackages(AbsTool):
    name = "Zip Packages"
    description = "This tool takes a folder, usually of HathiTrust packages," \
                  " zips each subfolder, and copies the resultant tree to a " \
                  "different location. Input is a root folder, usually for a" \
                  " HathiTrust shipment, containing multiple subfolders, " \
                  "each one a HathiTrust digitized item." \
                  "\nOutput is a destination location for the newly " \
                  "generated files."

    def __init__(self) -> None:

        super().__init__()

        # input_data = SelectDirectory()
        # input_data.label = "Package root"
        # self.options.append(input_data)

    @staticmethod
    def new_job() -> typing.Type[worker.ProcessJobWorker]:
        return ZipPackageJob

    @staticmethod
    def discover_task_metadata(
            *args,
            **kwargs
    ) -> typing.List[dict]:  # type: ignore

        source = kwargs[UserArgs.SOURCE.value]
        output = kwargs[UserArgs.OUTPUT.value]
        ZipPackages.validate_user_options(**kwargs)
        job_requests = []
        for dir_ in filter(lambda x: x.is_dir(), os.scandir(source)):
            job_requests.append({JobValues.SOURCE_PATH.value: dir_.path,
                                 JobValues.DESTINATION_PATH.value: output,
                                 }
                                )
        return job_requests

    @staticmethod
    def validate_user_options(**user_args):
        source = user_args[UserArgs.SOURCE.value]
        output = user_args[UserArgs.OUTPUT.value]
        if not os.path.exists(source) or not os.path.isdir(source):
            raise ValueError("Invalid source")
        if not os.path.exists(output) or not os.path.isdir(output):
            raise ValueError("Invalid output")

    @classmethod
    def generate_report(cls, *args, **kwargs):
        if "kwargs" in kwargs:
            output = kwargs["kwargs"][UserArgs.OUTPUT.value]
            return \
                "Zipping complete. All files written to \"{}\".".format(output)

        return "Zipping complete. All files written to output location"

    @staticmethod
    def get_user_options() -> typing.List[options.UserOption2]:
        return [
            options.UserOptionCustomDataType(UserArgs.SOURCE.value,
                                             options.FolderData),

            options.UserOptionCustomDataType(UserArgs.OUTPUT.value,
                                             options.FolderData),
        ]


class ZipPackageJob(ProcessJobWorker):
    @contextmanager
    def log_config(self, logger):
        gui_logger = GuiLogHandler(self.log)
        try:
            logger.addHandler(gui_logger)
            yield
        finally:
            logger.removeHandler(gui_logger)

    def process(self, source_path, destination_path, *args, **kwargs):
        my_logger = logging.getLogger(hathizip.__name__)
        my_logger.setLevel(logging.INFO)
        with self.log_config(my_logger):
            self.log("Zipping {}".format(source_path))
            hathizip.process.compress_folder_inplace(
                path=source_path,
                dst=destination_path)

            basename = os.path.basename(source_path)
            newfile = os.path.join(destination_path, f"{basename}.zip")
            self.log(f"Created {newfile}")
            self.result = newfile


class ZipPackagesWorkflow(AbsWorkflow):
    name = "0 EXPERIMENTAL " \
           "Zip Packages"

    description = "This tool takes a folder, usually of HathiTrust packages," \
                  " zips each subfolder, and copies the resultant tree to a " \
                  "different location. Input is a root folder, usually for a" \
                  " HathiTrust shipment, containing multiple subfolders, " \
                  "each one a HathiTrust digitized item." \
                  "\nOutput is a destination location for the newly " \
                  "generated files."
    active = False

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:

        return ZipPackages.discover_task_metadata(**user_args)

    def user_options(self):
        return ZipPackages.get_user_options()
