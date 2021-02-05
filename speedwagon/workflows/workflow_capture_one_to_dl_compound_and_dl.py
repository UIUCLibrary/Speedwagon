"""Workflow for converting Capture One tiff file into two formats."""
from __future__ import annotations
import logging

from typing import List, Any, Dict, Callable, Iterator
from contextlib import contextmanager
from uiucprescon import packager
from uiucprescon.packager.packages.abs_package_builder import AbsPackageBuilder
from uiucprescon.packager.packages.collection_builder import Metadata
from uiucprescon.packager.packages.collection import AbsPackageComponent
from speedwagon import tasks, validators
from speedwagon.job import AbsWorkflow
from speedwagon.workflows import shared_custom_widgets as options
from speedwagon.worker import GuiLogHandler


class CaptureOneToDlCompoundAndDLWorkflow(AbsWorkflow):
    """Settings for convert capture one tiff files."""

    name = "Convert CaptureOne TIFF to Digital Library Compound Object and " \
           "HathiTrust"
    description = "Input is a path to a folder of TIFF files all named with " \
                  "a bibid as a prefacing identifier, a final delimiting " \
                  "underscore, and a sequence consisting of " \
                  "padded zeroes and a number." \
                  "\n" \
                  "Output Hathi is a directory to put the new packages for " \
                  "HathiTrust."
    active = True

    def user_options(self) -> List[options.UserOptionCustomDataType]:
        """Get the options types need to configuring the workflow.

        Returns:
            Returns a list of user option types

        """
        return [
            options.UserOptionCustomDataType("Input", options.FolderData),
            options.UserOptionCustomDataType(
                "Output Digital Library", options.FolderData),
            options.UserOptionCustomDataType(
                "Output HathiTrust", options.FolderData),
                ]

    def discover_task_metadata(
            self,
            initial_results: List[Any],
            additional_data: Dict[str, str],
            **user_args: str
    ) -> List[Dict[str, str | AbsPackageComponent]]:
        """Loot at user settings and discover any data needed to build a task.

        Args:
            initial_results:
            additional_data:
            **user_args:

        Returns:
            Returns a list of data to create a job with

        """
        jobs: List[Dict[str, str | AbsPackageComponent]] = []

        source_input = user_args["Input"]
        dest_dl = user_args["Output Digital Library"]
        dest_ht = user_args["Output HathiTrust"]

        package_factory = packager.PackageFactory(
            packager.packages.CaptureOnePackage(delimiter="-"))
        for package in package_factory.locate_packages(source_input):
            new_job: Dict[str, str | AbsPackageComponent] = {
                "package": package,
                "output_dl": dest_dl,
                "output_ht": dest_ht,
                "source_path": source_input
            }
            jobs.append(new_job)
        return jobs

    @staticmethod
    def validate_user_options(**user_args: str) -> None:
        """Validate the user's arguments.

        Raises a value error is something is not valid.

        Args:
            **user_args:

        """
        option_validators = validators.OptionValidator()

        option_validators.register_validator(
            'Output Digital Library',
            validators.DirectoryValidation(key="Output Digital Library")
        )

        option_validators.register_validator(
            'Output HathiTrust',
            validators.DirectoryValidation(key="Output HathiTrust")
        )

        option_validators.register_validator(
            'Input',
            validators.DirectoryValidation(key="Input")
        )
        invalid_messages = []
        for validation in [
            option_validators.get("Output Digital Library"),
            option_validators.get("Output HathiTrust"),
            option_validators.get("Input")

        ]:
            if not validation.is_valid(**user_args):
                invalid_messages.append(validation.explanation(**user_args))

        if len(invalid_messages) > 0:
            raise ValueError("\n".join(invalid_messages))

    def create_new_task(self,
                        task_builder: tasks.TaskBuilder,
                        **job_args: str | AbsPackageComponent
                        ) -> None:
        """Generate a new task.

        Args:
            task_builder:
            **job_args:

        """
        existing_package: AbsPackageComponent = job_args['package']
        new_dl_package_root: str = job_args["output_dl"]
        new_ht_package_root: str = job_args["output_ht"]
        source_path: str = job_args["source_path"]
        package_id: str = existing_package.metadata[Metadata.ID]
        dl_packaging_task = PackageConverter(
            source_path=source_path,
            existing_package=existing_package,
            new_package_root=new_dl_package_root,
            packaging_id=package_id,
            package_format="Digital Library Compound",

        )
        task_builder.add_subtask(dl_packaging_task)
        ht_packaging_task = PackageConverter(
            source_path=source_path,
            existing_package=existing_package,
            new_package_root=new_ht_package_root,
            packaging_id=package_id,
            package_format="HathiTrust jp2",

        )
        task_builder.add_subtask(ht_packaging_task)


class PackageConverter(tasks.Subtask):
    """Convert packages formats."""

    name = "Package Conversion"
    package_formats: Dict[str, AbsPackageBuilder] = {
        "Digital Library Compound": packager.packages.DigitalLibraryCompound(),
        "HathiTrust jp2": packager.packages.HathiJp2()
    }

    @contextmanager
    def log_config(self, logger: logging.Logger) -> Iterator[None]:
        """Configure logs so they get forwarded to the speedwagon console.

        Args:
            logger:

        """
        gui_logger = GuiLogHandler(self.log)
        try:
            logger.addHandler(gui_logger)
            yield
        finally:
            logger.removeHandler(gui_logger)

    def __init__(self,
                 source_path: str,
                 packaging_id: str,
                 existing_package: AbsPackageComponent,
                 new_package_root: str,
                 package_format: str) -> None:
        """Create PackageConverter object.

        Args:
            source_path:
            packaging_id:
            existing_package:
            new_package_root:
            package_format:
        """
        super().__init__()
        self.package_factory: \
            Callable[[AbsPackageBuilder], packager.PackageFactory] \
            = packager.PackageFactory

        self.packaging_id = packaging_id
        self.existing_package = existing_package
        self.new_package_root = new_package_root
        if package_format not in PackageConverter.package_formats.keys():
            raise ValueError(f"{package_format} is not a known value")
        self.package_format = package_format
        self.source_path = source_path

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
                f"to a {self.package_format} package at "
                f"{self.new_package_root}")

            package_factory = self.package_factory(
                PackageConverter.package_formats[self.package_format]
            )

            package_factory.transform(
                self.existing_package, dest=self.new_package_root)
        return True
