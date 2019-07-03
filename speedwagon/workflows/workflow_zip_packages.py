import logging

import os
from contextlib import contextmanager
from typing import List, Any, Optional

from speedwagon import tasks, reports
from speedwagon.job import AbsWorkflow
from speedwagon.worker import GuiLogHandler
from . import shared_custom_widgets as options
import hathizip.process
import hathizip


class ZipPackagesWorkflow(AbsWorkflow):
    name = "Zip Packages"

    description = "This tool takes a folder, usually of HathiTrust " \
                  "packages, zips each subfolder, and copies the resultant " \
                  "tree to a different location. Input is a root folder, " \
                  "usually for a HathiTrust shipment, containing multiple " \
                  "subfolders, each one a HathiTrust digitized item." \
                  "\n" \
                  "Output is a destination location for the newly generated " \
                  "file."

    active = True

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        source = user_args["Source"]
        output = user_args["Output"]

        job_requests = []
        for dir_ in filter(lambda x: x.is_dir(), os.scandir(source)):
            job_requests.append({"source_path": dir_.path,
                                 "destination_path": output,
                                 }
                                )
        return job_requests

    @staticmethod
    def validate_user_options(**user_args):

        source = user_args["Source"]
        output = user_args["Output"]
        if not os.path.exists(source) or not os.path.isdir(source):
            raise ValueError("Invalid source")
        if not os.path.exists(output) or not os.path.isdir(output):
            raise ValueError("Invalid output")

        return True

    def user_options(self):
        return [
            options.UserOptionCustomDataType("Source",
                                             options.FolderData),

            options.UserOptionCustomDataType("Output",
                                             options.FolderData),
        ]

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        new_task = ZipTask(**job_args)
        task_builder.add_subtask(new_task)

    @classmethod
    @reports.add_report_borders
    def generate_report(cls, results: List[tasks.Result],
                        **user_args) -> Optional[str]:

        output = user_args.get("Output")
        if output:
            return \
                "Zipping complete. All files written to \"{}\".".format(output)

        return "Zipping complete. All files written to output location"


class ZipTask(tasks.Subtask):
    def __init__(self, source_path, destination_path, *args, **kwargs) -> None:
        super().__init__()
        self._source_path = source_path
        self._destination_path = destination_path

    def work(self):
        my_logger = logging.getLogger(hathizip.__name__)
        my_logger.setLevel(logging.INFO)
        with self.log_config(my_logger):
            self.log("Zipping {}".format(self._source_path))
            hathizip.process.compress_folder_inplace(
                path=self._source_path,
                dst=self._destination_path)

            basename = os.path.basename(self._source_path)
            newfile = os.path.join(self._destination_path, f"{basename}.zip")
            self.log(f"Created {newfile}")
            self.set_results(newfile)

        return True

    @contextmanager
    def log_config(self, logger):
        gui_logger = GuiLogHandler(self.log)
        try:
            logger.addHandler(gui_logger)
            yield
        finally:
            logger.removeHandler(gui_logger)
