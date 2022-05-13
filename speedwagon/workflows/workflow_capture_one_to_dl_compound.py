"""Workflow for converting Capture One tiff file into DL compound format."""
from __future__ import annotations
import logging
import typing
import warnings

from typing import Any, Dict, List, Union, Optional

from uiucprescon import packager
from uiucprescon.packager.packages.collection import Package
from uiucprescon.packager.packages.collection_builder import Metadata

import speedwagon
from speedwagon import validators, utils
from speedwagon.job import Workflow

__all__ = ['CaptureOneToDlCompoundWorkflow']


class CaptureOneToDlCompoundWorkflow(Workflow):
    """Settings for convert capture one tiff files to DL compound."""

    name = "Convert CaptureOne TIFF to Digital Library Compound Object"
    description = 'Input is a path to a folder of TIFF files all named with ' \
                  'a bibid as a prefacing identifier, a final delimiting ' \
                  'dash, and a sequence consisting of padded ' \
                  'zeroes and a number' \
                  '\n' \
                  '\n' \
                  'Output is a directory to put the new packages'
    active = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        warnings.warn(
            "Pending removal of Convert CaptureOne TIFF to Digital "
            "Library Compound Object",
            DeprecationWarning
        )

    def discover_task_metadata(self,
                               initial_results: List[Any],
                               additional_data: Dict[str, Any],
                               **user_args: str
                               ) -> List[Dict[str, Any]]:
        """Loot at user settings and discover any data needed to build a task.

        Args:
            initial_results:
            additional_data:
            **user_args:

        Returns:
            Returns a list of data to create a job with

        """
        jobs: List[Dict[str, Union[str, Package]]] = []
        source_input = user_args["Input"]
        dest = user_args["Output"]

        package_factory = packager.PackageFactory(
            packager.packages.CaptureOnePackage(delimiter="-"))

        for package in package_factory.locate_packages(source_input):
            new_job: Dict[str, Union[str, Package]] = {
                "package": package,
                "output": dest,
                "source_path": source_input
            }
            jobs.append(new_job)
        return jobs

    def create_new_task(
            self,
            task_builder: speedwagon.tasks.TaskBuilder,
            **job_args: Union[str, Package]
    ) -> None:
        """Generate a new task.

        Args:
            task_builder:
            **job_args:

        """
        existing_package: Package = typing.cast(Package, job_args['package'])
        new_package_root: str = typing.cast(str, job_args["output"])
        source_path: str = typing.cast(str, job_args["source_path"])

        package_id: str = typing.cast(
            str,
            existing_package.metadata[Metadata.ID]
        )

        packaging_task = PackageConverter(
            source_path=source_path,
            existing_package=existing_package,
            new_package_root=new_package_root,
            packaging_id=package_id

        )
        task_builder.add_subtask(packaging_task)

    @staticmethod
    def validate_user_options(**user_args: str) -> bool:
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
        return True


class PackageConverter(speedwagon.tasks.Subtask):
    """Convert packages formats."""

    name = "Package Conversion"

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

    def task_description(self) -> Optional[str]:
        return \
            f"Creating a new Digital Library package from {self.source_path}"

    def work(self) -> bool:
        """Convert source package to the new type.

        Returns:
            True on success, False on failure

        """
        my_logger = logging.getLogger(packager.__name__)
        my_logger.setLevel(logging.INFO)
        with utils.log_config(my_logger, self.log):
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
