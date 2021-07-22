"""Workflow to convert hathi limited packages to digital library format."""

import logging
import os
from contextlib import contextmanager
from typing import List, Any, Optional

from uiucprescon import packager
from speedwagon.job import Workflow
from speedwagon import tasks, reports
from speedwagon.logging import GuiLogHandler
from . import shared_custom_widgets as options
__all__ = ['HathiLimitedToDLWorkflow']


class HathiLimitedToDLWorkflow(Workflow):
    name = "Convert HathiTrust limited view to Digital library"
    description = 'This tool converts HathiTrust limited view packages to ' \
                  'Digital library'

    active = True

    def discover_task_metadata(
            self,
            initial_results: List[Any],
            additional_data, **user_args: str
    ) -> List[dict]:

        hathi_limited_view_packager = packager.PackageFactory(
            packager.packages.HathiLimitedView())

        return [{
            "package": package,
            "destination": user_args['Output']
        } for package in hathi_limited_view_packager.locate_packages(
            user_args['Input'])]

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        task_builder.add_subtask(
            PackageConverter(src=job_args['package'],
                             dst=job_args['destination'])
        )

    def user_options(self) -> List[options.UserOption3]:
        return [
            options.UserOptionCustomDataType("Input", options.FolderData),
            options.UserOptionCustomDataType("Output", options.FolderData)
        ]

    @classmethod
    @reports.add_report_borders
    def generate_report(cls, results: List[tasks.Result],
                        **user_args) -> Optional[str]:
        total = len(results)

        return f"""All done. Converted {total} packages.
 Results located at {user_args['Output']}
"""

    @staticmethod
    def validate_user_options(**user_args: str) -> bool:
        required = ['Input', "Output"]
        for arg in required:
            if user_args[arg] is None or str(user_args[arg]).strip() == "":
                raise ValueError("Missing required value for {}".format(arg))

        if user_args['Output'] == user_args['Input']:
            raise ValueError("Input cannot be the same as Output")

        if not os.path.exists(user_args['Input']):
            raise ValueError("Input does not exist")

        if not os.path.exists(user_args['Output']):
            raise ValueError("Output does not exist")
        return True


class PackageConverter(tasks.Subtask):

    @contextmanager
    def log_config(self, logger: logging.Logger):
        gui_logger = GuiLogHandler(self.log)
        try:
            logger.addHandler(gui_logger)
            yield
        finally:
            logger.removeHandler(gui_logger)

    def __init__(self, src: str, dst: str) -> None:
        super().__init__()
        self.src = src
        self.dst = dst
        self.output_packager = packager.PackageFactory(
            packager.packages.DigitalLibraryCompound())

    def work(self) -> bool:

        my_logger = logging.getLogger(packager.__name__)
        my_logger.setLevel(logging.INFO)

        with self.log_config(my_logger):
            self.log("Converting package from {}".format(self.src))
            self.output_packager.transform(self.src, self.dst)
            self.set_results({
                "destination": self.dst
            })

        return True
