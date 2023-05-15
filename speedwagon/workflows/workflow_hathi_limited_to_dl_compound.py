"""Workflow to convert hathi limited packages to digital library format."""

import logging
import os
from typing import List, Any, Optional

from uiucprescon import packager

import speedwagon
import speedwagon.workflow
from speedwagon.job import Workflow
from speedwagon import reports, utils

__all__ = ['HathiLimitedToDLWorkflow']


class HathiLimitedToDLWorkflow(Workflow):
    """Converts Hathi Limited View file packages to Digital Library format."""

    name = "Convert HathiTrust limited view to Digital library"
    description = 'This tool converts HathiTrust limited view packages to ' \
                  'Digital library'

    active = True

    def discover_task_metadata(
            self,
            initial_results: List[Any],
            additional_data, **user_args: str
    ) -> List[dict]:
        """Find file packages."""
        hathi_limited_view_packager = packager.PackageFactory(
            packager.packages.HathiLimitedView())

        return [{
            "package": package,
            "destination": user_args['Output']
        } for package in hathi_limited_view_packager.locate_packages(
            user_args['Input'])]

    def create_new_task(
            self,
            task_builder: "speedwagon.tasks.TaskBuilder",
            **job_args
    ):
        """Create a task for converting a package."""
        task_builder.add_subtask(
            PackageConverter(src=job_args['package'],
                             dst=job_args['destination'])
        )

    def job_options(
            self
    ) -> List[speedwagon.workflow.AbsOutputOptionDataType]:
        """Get user options for input and output directories."""
        return [
            speedwagon.workflow.DirectorySelect("Input"),
            speedwagon.workflow.DirectorySelect("Output"),
        ]

    @classmethod
    @reports.add_report_borders
    def generate_report(cls, results: List[speedwagon.tasks.Result],
                        **user_args) -> Optional[str]:
        """Generate a report of packages converted."""
        total = len(results)

        return f"""All done. Converted {total} packages.
 Results located at {user_args['Output']}
"""

    @staticmethod
    def validate_user_options(**user_args: str) -> bool:
        """Validate user input and output args."""
        required = ['Input', "Output"]
        for arg in required:
            if user_args[arg] is None or str(user_args[arg]).strip() == "":
                raise ValueError(f"Missing required value for {arg}")

        if user_args['Output'] == user_args['Input']:
            raise ValueError("Input cannot be the same as Output")

        if not os.path.exists(user_args['Input']):
            raise ValueError("Input does not exist")

        if not os.path.exists(user_args['Output']):
            raise ValueError("Output does not exist")
        return True


class PackageConverter(speedwagon.tasks.Subtask):
    name = "Convert Package"

    def __init__(
            self,
            src: packager.package.collection.Package,
            dst: str
    ) -> None:
        super().__init__()
        self.src = src
        self.dst = dst
        self.output_packager = packager.PackageFactory(
            packager.packages.DigitalLibraryCompound())

    def task_description(self) -> Optional[str]:
        return f"Converting package {self.src}"

    def work(self) -> bool:

        my_logger = logging.getLogger(packager.__name__)
        my_logger.setLevel(logging.INFO)

        with utils.log_config(my_logger, self.log):
            self.log(f"Converting package from {self.src}")
            self.output_packager.transform(self.src, self.dst)
            self.set_results({
                "destination": self.dst
            })

        return True
