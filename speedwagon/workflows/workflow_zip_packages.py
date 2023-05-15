"""Workflow for creating zip archives."""

import logging

import os
from typing import List, Any, Optional

import hathizip.process
import hathizip

import speedwagon
from speedwagon import reports, workflow, utils
from speedwagon.job import Workflow


__all__ = ['ZipPackagesWorkflow']


class ZipPackagesWorkflow(Workflow):
    """Zip Package workflow for Speedwagon."""

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

    def discover_task_metadata(self,
                               initial_results: List[Any],
                               additional_data,
                               **user_args: str) -> List[dict]:
        """Generate metadata need by task."""
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
    def validate_user_options(**user_args: str) -> bool:
        """Validate user settings for source and output paths."""
        source = user_args["Source"]
        output = user_args["Output"]
        if not os.path.exists(source) or not os.path.isdir(source):
            raise ValueError("Invalid source")
        if not os.path.exists(output) or not os.path.isdir(output):
            raise ValueError("Invalid output")

        return True

    def job_options(self) -> List[workflow.AbsOutputOptionDataType]:
        """Request user settings for source and output paths."""
        source = workflow.DirectorySelect("Source")
        output = workflow.DirectorySelect("Output")

        return [
            source,
            output
        ]

    def create_new_task(
            self,
            task_builder: "speedwagon.tasks.TaskBuilder",
            **job_args
    ) -> None:
        """Create a Zip task."""
        new_task = ZipTask(**job_args)
        task_builder.add_subtask(new_task)

    @classmethod
    @reports.add_report_borders
    def generate_report(cls, results: List[speedwagon.tasks.Result],
                        **user_args: str) -> Optional[str]:
        """Generate report for all files added to zip file."""
        output = user_args.get("Output")
        if output:
            return f"Zipping complete. All files written to \"{output}\"."

        return "Zipping complete. All files written to output location"


class ZipTask(speedwagon.tasks.Subtask):
    name = "Zip Files"

    def __init__(
            self,
            source_path: str,
            destination_path: str,
            *args,
            **kwargs
    ) -> None:

        super().__init__()
        self._source_path = source_path
        self._destination_path = destination_path

    def task_description(self) -> Optional[str]:
        return f"Zipping files in {self._source_path}"

    def work(self) -> bool:
        my_logger = logging.getLogger(hathizip.__name__)
        my_logger.setLevel(logging.INFO)
        with utils.log_config(my_logger, self.log):
            self.log(f"Zipping {self._source_path}")
            hathizip.process.compress_folder_inplace(
                path=self._source_path,
                dst=self._destination_path)

            basename = os.path.basename(self._source_path)
            newfile = os.path.join(self._destination_path, f"{basename}.zip")
            self.log(f"Created {newfile}")
            self.set_results(newfile)

        return True
