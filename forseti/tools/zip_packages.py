import logging
import random
import typing
import time

import os
from contextlib import contextmanager

from forseti import worker
# from frames.tool import  ZipPackageJob
from forseti.tools.abstool import AbsTool
# from forseti.tool import ToolOption
from forseti.worker import ProcessJob, GuiLogHandler
# from .tool_options import UserOption
from forseti.tools import tool_options
import hathizip.process
import hathizip

class ZipPackages(AbsTool):
    name = "Zip packages"
    description = "This tool takes a folder, usually of HathiTrust packages, zips each subfolder, and copies the " \
                  " resultant tree to a different location. Input is a root folder, usually for a HathiTrust shipment, " \
                  " containing multiple subfolders, each one a HathiTrust digitized item." \
                  "\nOutput is a destination location for the newly generated files."

    def __init__(self) -> None:

        super().__init__()

        # input_data = SelectDirectory()
        # input_data.label = "Package root"
        # self.options.append(input_data)

    @staticmethod
    def new_job() -> typing.Type[worker.ProcessJob]:
        return ZipPackageJob

    @staticmethod
    def discover_jobs(source, output, *args, **kwargs) -> typing.List[dict]:  # type: ignore
        ZipPackages.validate_args(source, output, args, kwargs)

        job_requests = []
        for dir_ in filter(lambda x: x.is_dir(), os.scandir(source)):
            job_requests.append({"source_path": dir_.path,
                                 "destination_path": output,
                                 }
                                )
        return job_requests

    @staticmethod
    def validate_args(source, output, *args, **kwargs):

        if not os.path.exists(source) or not os.path.isdir(source):
            raise ValueError("Invalid source")
        if not os.path.exists(output) or not os.path.isdir(output):
            raise ValueError("Invalid output")

    @classmethod
    def generate_report(cls, *args, **kwargs):
        if "user_args" in kwargs:
            return "Zipping complete. All files written to {}.".format(kwargs["user_args"]["output"])
        return "Zipping complete. All files written to output location"

    @staticmethod
    def get_user_options() -> typing.List[tool_options.UserOption2]:
        return [
            tool_options.UserOptionCustomDataType("source", tool_options.FolderData),
            tool_options.UserOptionCustomDataType("output", tool_options.FolderData),
        ]


class ZipPackageJob(ProcessJob):
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
            hathizip.process.compress_folder(path=source_path, dst=destination_path)
            # self.log("{} successfully zipped to {}".format(source_path, destination_path))
            basename = os.path.basename(source_path)
            newfile = os.path.join(destination_path, f"{basename}.zip")
            self.log(f"Created {newfile}")
            self.result = newfile
