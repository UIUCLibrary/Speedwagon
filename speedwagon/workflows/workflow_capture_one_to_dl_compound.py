"""Workflow for converting Capture One tiff file into DL compound format."""
from __future__ import annotations
import logging

from typing import Any, Dict, Iterator

from contextlib import contextmanager

from uiucprescon import packager
from uiucprescon.packager.packages.collection import Package
from uiucprescon.packager.packages.collection_builder import Metadata

from speedwagon import tasks, validators
from speedwagon.job import AbsWorkflow
from speedwagon.worker import GuiLogHandler
from . import shared_custom_widgets as options


class CaptureOneToDlCompoundWorkflow(AbsWorkflow):
    """Settings for convert capture one tiff files to DL compound."""

    name = "Convert CaptureOne TIFF to Digital Library Compound Object"
    description = 'Input is a path to a folder of TIFF files all named with ' \
                  'a bibid as a prefacing identifier, a final delimiting ' \
                  'dash, and a sequence consisting of padded ' \
                  'zeroes and a number' \
                  '\n' \
                  '\n' \
                  'Output is a directory to put the new packages'
    active = True

    def user_options(self) -> list[options.UserOptionCustomDataType]:
        """Get the options types need to configuring the workflow.

        Returns:
            Returns a list of user option types
        """
        return [
            options.UserOptionCustomDataType("Input", options.FolderData),
            options.UserOptionCustomDataType("Output", options.FolderData)
                ]

    def discover_task_metadata(self,
                               initial_results: list[Any],
                               additional_data: Dict[str, Any],
                               **user_args: str
                               ) -> list[Dict[str, Any]]:
        """Loot at user settings and discover any data needed to build a task.

        Args:
            initial_results:
            additional_data:
            **user_args:

        Returns:
            Returns a list of data to create a job with

        """
        jobs: list[Dict[str, str | Package]] = []
        source_input = user_args["Input"]
        dest = user_args["Output"]

        package_factory = packager.PackageFactory(
            packager.packages.CaptureOnePackage(delimiter="-"))

        for package in package_factory.locate_packages(source_input):
            new_job: Dict[str, str | Package] = {
                "package": package,
                "output": dest,
                "source_path": source_input
            }
            jobs.append(new_job)
        return jobs

    def create_new_task(self,
                        task_builder: tasks.TaskBuilder,
                        **job_args: str | Package
                        ) -> None:
        """Generate a new task.

        Args:
            task_builder:
            **job_args:

        """
        existing_package: Package = job_args['package']
        new_package_root: str = job_args["output"]
        source_path: str = job_args["source_path"]
        package_id: str = existing_package.metadata[Metadata.ID]

        packaging_task = PackageConverter(
            source_path=source_path,
            existing_package=existing_package,
            new_package_root=new_package_root,
            packaging_id=package_id

        )
        task_builder.add_subtask(packaging_task)

    @staticmethod
    def validate_user_options(**user_args: str) -> None:
        """Validate the user's arguments.

        Raises a value error is something is not valid.

        Args:
            **user_args:

        """
        option_validators = validators.OptionValidator()
        option_validators.register_validator(
            'Output', validators.DirectoryValidation(key="Output")
        )

        option_validators.register_validator(
            'Input', validators.DirectoryValidation(key="Input")
        )
        invalid_messages = []
        for validation in [
            option_validators.get("Output"),
            option_validators.get("Input")

        ]:
            if not validation.is_valid(**user_args):
                invalid_messages.append(validation.explanation(**user_args))

        if len(invalid_messages) > 0:
            raise ValueError("\n".join(invalid_messages))


class PackageConverter(tasks.Subtask):
    """Convert packages formats."""

    @contextmanager
    def log_config(self, logger: logging.Logger) -> Iterator[None]:
        """Configure logs so they get forwarded to the speedwagon console.

        Args:
            logger:

        """
        gui_logger: logging.Handler = GuiLogHandler(self.log)
        try:
            logger.addHandler(gui_logger)
            yield
        finally:
            logger.removeHandler(gui_logger)

    def __init__(self,
                 source_path: str,
                 packaging_id: str,
                 existing_package: Package,
                 new_package_root: str) -> None:
        """Create a new PackageConverter object.

        Args:
            source_path:
            packaging_id:
            existing_package:
            new_package_root:
        """
        super().__init__()
        self.packaging_id = packaging_id
        self.existing_package = existing_package
        self.new_package_root = new_package_root
        self.source_path = source_path
        self.package_factory = None

    def work(self) -> bool:
        """Convert source package to the new type.

        Returns:
            True on success, False on failure

        """
        my_logger = logging.getLogger(packager.__name__)
        my_logger.setLevel(logging.INFO)
        with self.log_config(my_logger):
            self.log(
                f"Converting {self.packaging_id} from {self.source_path} "
                f"to a Hathi Trust Tiff package at {self.new_package_root}")

            package_factory = self.package_factory or packager.PackageFactory(
                packager.packages.DigitalLibraryCompound()
            )

            package_factory.transform(
                self.existing_package, dest=self.new_package_root
            )

        return True
