"""Workflow for converting Capture One tiff file into two formats."""
from __future__ import annotations
import logging
import os
import typing

try:  # pragma: no cover
    from typing import TypedDict
except ImportError:  # pragma: no cover
    from typing_extensions import TypedDict

from typing import List, Any, Dict, Callable, Iterator, Optional, Union, \
    Iterable
from contextlib import contextmanager
from uiucprescon import packager
from uiucprescon.packager.packages.abs_package_builder import AbsPackageBuilder
from uiucprescon.packager.packages.collection_builder import Metadata
from uiucprescon.packager.packages.collection import AbsPackageComponent
import speedwagon
from speedwagon import validators
from speedwagon.job import Workflow
from speedwagon.workflows import shared_custom_widgets as options
from speedwagon.logging import GuiLogHandler
import speedwagon.exceptions

__all__ = ['CaptureOneToDlCompoundAndDLWorkflow']

# =========================== USER OPTIONS CONSTANTS ======================== #
OUTPUT_HATHITRUST: typing.Final[str] = "Output HathiTrust"
OUTPUT_DIGITAL_LIBRARY: typing.Final[str] = "Output Digital Library"
USER_INPUT_PATH: typing.Final[str] = "Input"
PACKAGE_TYPE: typing.Final[str] = "Package Type"
# =========================================================================== #

UserArgs = TypedDict(
    'UserArgs',
    {
        'Input': str,
        "Package Type": str,
        "Output Digital Library": str,
        "Output HathiTrust": str
    },
)


class JobArguments(TypedDict):
    package: AbsPackageComponent
    output_dl: Optional[str]
    output_ht: Optional[str]
    source_path: str


SUPPORTED_PACKAGE_SOURCES = {
    "Capture One": packager.packages.CaptureOnePackage(delimiter="-"),
    "Archival collections/Non EAS": packager.packages.ArchivalNonEAS(),
    "Cataloged collections/Non EAS": packager.packages.CatalogedNonEAS(),
    "EAS": packager.packages.Eas()
}


class CaptureOneToDlCompoundAndDLWorkflow(Workflow):
    """Settings for convert capture one tiff files.

    .. versionchanged:: 0.1.5
        workflow only requires a single output to be set. Any empty output
            parameters will result in that output format not being made.

        Add EAS package format support for input

    """

    name = "Convert CaptureOne TIFF to Digital Library Compound Object and " \
           "HathiTrust"
    description = "Input is a path to a folder of TIFF files all named with " \
                  "a bibid as a prefacing identifier, a final delimiting " \
                  "dash, and a sequence consisting of " \
                  "padded zeroes and a number." \
                  "\n" \
                  "Output Hathi is a directory to put the new packages for " \
                  "HathiTrust."
    active = True

    def user_options(self) -> List[Union[options.UserOption2,
                                         options.UserOption3]]:
        """Get the options types need to configuring the workflow.

        Returns:
            Returns a list of user option types

        """
        user_options: List[Union[options.UserOption2, options.UserOption3]] = [
            options.UserOptionCustomDataType(USER_INPUT_PATH,
                                             options.FolderData),
            ]
        package_type_selection = options.ListSelection(
            PACKAGE_TYPE)
        for package_type_name in SUPPORTED_PACKAGE_SOURCES:
            package_type_selection.add_selection(package_type_name)
        user_options.append(package_type_selection)
        user_options += [
            options.UserOptionCustomDataType(
                OUTPUT_DIGITAL_LIBRARY, options.FolderData),
            options.UserOptionCustomDataType(
                OUTPUT_HATHITRUST, options.FolderData),
                ]
        return user_options

    def discover_task_metadata(
            self,
            initial_results: List[Any],
            additional_data: Dict[str, str],
            **user_args: typing.Optional[str]
    ) -> List[Dict[str, Union[str, AbsPackageComponent]]]:
        """Loot at user settings and discover any data needed to build a task.

        Args:
            initial_results:
            additional_data:
            **user_args:

        Returns:
            Returns a list of data to create a job with

        """
        user_arguments: UserArgs = typing.cast(UserArgs, user_args)
        source_input = user_arguments['Input']
        dest_dl = user_arguments["Output Digital Library"]
        dest_ht = user_arguments["Output HathiTrust"]
        package_type = SUPPORTED_PACKAGE_SOURCES.get(
            user_arguments["Package Type"]
        )
        if package_type is None:
            raise ValueError(
                f"Unknown package type {user_arguments['Package Type']}"
            )
        package_factory = packager.PackageFactory(package_type)

        jobs: List[JobArguments] = []
        try:
            for package in package_factory.locate_packages(source_input):
                jobs.append(
                    JobArguments({
                        "package": package,
                        "output_dl": dest_dl,
                        "output_ht": dest_ht,
                        "source_path": source_input
                    })
                )
        except Exception as error:
            raise speedwagon.exceptions.SpeedwagonException(
                f"Failed to locate packages at {source_input}. Reason: {error}"
            ) from error

        return typing.cast(List[Dict[str, typing.Union[str, Any]]], jobs)

    @staticmethod
    def validate_user_options(**user_args: str) -> bool:
        """Validate the user's arguments.

        Raises a value error is something is not valid.

        Args:
            **user_args:

        """
        user_arguments: UserArgs = typing.cast(UserArgs, user_args)
        option_validators = validators.OptionValidator()

        option_validators.register_validator(
            'At least one output',
            MinimumOutputsValidator(
                at_least_one_of=[
                    OUTPUT_DIGITAL_LIBRARY,
                    OUTPUT_HATHITRUST
                ]
            )
        )
        option_validators.register_validator(
            'At least one output exists',
            OutputsValidValuesValidator(
                keys_to_check=[
                    OUTPUT_DIGITAL_LIBRARY,
                    OUTPUT_HATHITRUST
                ]
            )
        )

        option_validators.register_validator(
            'Input',
            validators.DirectoryValidation(key=USER_INPUT_PATH)
        )
        invalid_messages: List[str] = []
        for validation in [
            option_validators.get('At least one output'),
            option_validators.get('At least one output exists'),
            option_validators.get(USER_INPUT_PATH)

        ]:
            if not validation.is_valid(**user_arguments):
                invalid_messages.append(
                    validation.explanation(**user_arguments)
                )

        if len(invalid_messages) > 0:
            raise ValueError("\n".join(invalid_messages))
        return True

    def create_new_task(self,
                        task_builder: speedwagon.tasks.TaskBuilder,
                        **job_args: Union[str, AbsPackageComponent]
                        ) -> None:
        """Generate a new task.

        Args:
            task_builder:
            **job_args:

        """
        job_arguments = typing.cast(JobArguments, job_args)
        existing_package: AbsPackageComponent = job_arguments['package']

        source_path = job_arguments["source_path"]
        package_id: str = existing_package.metadata[Metadata.ID]
        new_dl_package_root = job_arguments.get("output_dl")
        if new_dl_package_root is not None:
            dl_packaging_task = PackageConverter(
                source_path=source_path,
                existing_package=existing_package,
                new_package_root=new_dl_package_root,
                packaging_id=package_id,
                package_format="Digital Library Compound",
            )
            task_builder.add_subtask(dl_packaging_task)

        new_ht_package_root = job_arguments.get("output_ht")
        if new_ht_package_root is not None:
            ht_packaging_task = PackageConverter(
                source_path=source_path,
                existing_package=existing_package,
                new_package_root=new_ht_package_root,
                packaging_id=package_id,
                package_format="HathiTrust jp2",

            )
            task_builder.add_subtask(ht_packaging_task)


class OutputsValidValuesValidator(validators.AbsOptionValidator):
    """Validator to make sure that output directories are valid."""

    def __init__(self, keys_to_check: Iterable[str]) -> None:
        super().__init__()
        self.keys_to_check = keys_to_check
        self.directory_validator = None

    @staticmethod
    def is_entry_valid_dir(
            entry: str,
            callback: Optional[Callable[[str], bool]] = None
    ) -> bool:

        if entry is None or entry == "":
            return True
        return (callback or os.path.exists)(entry)

    def is_valid(self, **user_data: Any) -> bool:
        return all(self.is_entry_valid_dir(
                    user_data[key],
                    self.directory_validator
            ) for key in self.keys_to_check)

    def explanation(self, **user_data: Any) -> str:
        folders_not_exists: typing.Set[str] = {
            user_data[key]
            for key in self.keys_to_check
            if not self.is_entry_valid_dir(
                user_data[key], self.directory_validator
            )
        }
        if len(folders_not_exists) > 0:
            return "\n".join(
                f"Directory {directory} does not exist"
                for directory in folders_not_exists
            )
        return "ok"


class MinimumOutputsValidator(validators.AbsOptionValidator):

    def __init__(self, at_least_one_of: List[str]) -> None:
        super().__init__()
        self.keys = at_least_one_of
        self._validators = []
        for k in self.keys:
            self._validators.append(validators.DirectoryValidation(k))

    def is_valid(self, **user_data: Any) -> bool:
        return any(f.is_valid(**user_data) for f in self._validators)

    def explanation(self, **user_data: Any) -> str:
        if self.is_valid(**user_data) is False:
            return \
                f'One of the follow outputs must be valid: ' \
                f'{", ".join(self.keys)}'
        return "ok"


class PackageConverter(speedwagon.tasks.Subtask):
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

    def task_description(self) -> Optional[str]:
        return f"Converting {self.source_path}"

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
