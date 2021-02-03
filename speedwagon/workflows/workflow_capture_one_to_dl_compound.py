import logging
import abc
import os

from uiucprescon import packager
from typing import List, Any
from contextlib import contextmanager
from speedwagon import tasks
from speedwagon.job import AbsWorkflow
from . import shared_custom_widgets as options
from speedwagon.worker import GuiLogHandler
from uiucprescon.packager.packages.collection_builder import Metadata


class CaptureOneToDlCompoundWorkflow(AbsWorkflow):
    name = "Convert CaptureOne TIFF to Digital Library Compound Object"
    description = 'Input is a path to a folder of TIFF files all named with ' \
                  'a bibid as a prefacing identifier, a final delimiting ' \
                  'underscore, and a sequence consisting of padded ' \
                  'zeroes and a number' \
                  '\n' \
                  '\n' \
                  'Output is a directory to put the new packages'
    active = True

    def user_options(self):
        return [
            options.UserOptionCustomDataType("Input", options.FolderData),
            options.UserOptionCustomDataType("Output", options.FolderData)
                ]

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        jobs = []
        source_input = user_args["Input"]
        dest = user_args["Output"]

        package_factory = packager.PackageFactory(
            packager.packages.CaptureOnePackage(delimiter="-"))

        for package in package_factory.locate_packages(source_input):
            jobs.append({
                "package": package,
                "output": dest,
                "source_path": source_input
            }
            )
        return jobs

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        existing_package = job_args['package']
        new_package_root = job_args["output"]
        source_path = job_args["source_path"]
        package_id = existing_package.metadata[Metadata.ID]

        packaging_task = PackageConverter(
            source_path=source_path,
            existing_package=existing_package,
            new_package_root=new_package_root,
            packaging_id=package_id

        )
        task_builder.add_subtask(packaging_task)

    @staticmethod
    def validate_user_options(**user_args):
        option_validators = OptionValidator()
        option_validators.register_validator('Output', DirectoryValidation(key="Output"))
        option_validators.register_validator('Input', DirectoryValidation(key="Input"))
        validators = [
            option_validators.get("Output"),
            option_validators.get("Input")

        ]
        invalid_messages = []
        for v in validators:
            if not v.is_valid(**user_args):
                invalid_messages.append(v.explanation(**user_args))

        if len(invalid_messages) > 0:
            raise ValueError("\n".join(invalid_messages))


class PackageConverter(tasks.Subtask):
    @contextmanager
    def log_config(self, logger):
        gui_logger = GuiLogHandler(self.log)
        try:
            logger.addHandler(gui_logger)
            yield
        finally:
            logger.removeHandler(gui_logger)

    def __init__(self, source_path, packaging_id,
                 existing_package, new_package_root) -> None:

        super().__init__()
        self.packaging_id = packaging_id
        self.existing_package = existing_package
        self.new_package_root = new_package_root
        self.source_path = source_path

    def work(self):
        my_logger = logging.getLogger(packager.__name__)
        my_logger.setLevel(logging.INFO)
        with self.log_config(my_logger):
            self.log(
                f"Converting {self.packaging_id} from {self.source_path} "
                f"to a Hathi Trust Tiff package at {self.new_package_root}")

            package_factory = packager.PackageFactory(
                packager.packages.DigitalLibraryCompound())

            package_factory.transform(
                self.existing_package, dest=self.new_package_root)
        return True


class AbsOptionValidator(abc.ABC):
    @abc.abstractmethod
    def is_valid(self, **user_data) -> bool:
        """Evaluate if the kwargs are valid"""

    @abc.abstractmethod
    def explanation(self, **user_data) -> str:
        """Get reason for is_valid.

        Args:
            **user_data:

        Returns:
            returns a message explaining why something isn't valid, otherwise
                produce the message "ok"
        """


class DirectoryValidation(AbsOptionValidator):

    def __init__(self, key) -> None:
        self._key = key

    @staticmethod
    def destination_exists(path) -> bool:
        if not os.path.exists(path):
            return False

    def is_valid(self, **user_data) -> bool:
        output = user_data.get(self._key)
        if not output:
            return False
        if self.destination_exists(output) is False:
            return False
        return True

    def explanation(self, **user_data) -> str:
        if self.destination_exists(user_data[self._key]) is False:
            return f"Directory {user_data[self._key]} does not exist"
        return "ok"


class OptionValidatorFactory:
    def __init__(self):
        self._validators = {}

    def register_validator(self, key, validator):
        self._validators[key] = validator

    def create(self, key, **kwargs):
        builder = self._validators.get(key)
        if not builder:
            raise ValueError(key)
        return builder


class OptionValidator(OptionValidatorFactory):
    def get(self, service_id, **kwargs):
        return self.create(service_id, **kwargs)
