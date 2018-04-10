import enum
import logging
import typing
from contextlib import contextmanager

from speedwagon import worker
from speedwagon.tools import options
from speedwagon.job import AbsTool
import uiucprescon.packager
import uiucprescon.packager.packages
from uiucprescon.packager.packages.collection_builder import Metadata


class UserArgs(enum.Enum):
    INPUT = "Input"
    OUTPUT = "Output"


class ResultValues(enum.Enum):
    VALID = "valid"
    FILENAME = "filename"
    PATH = "path"
    CHECKSUM_REPORT_FILE = "checksum_report_file"


class JobValues(enum.Enum):
    PACKAGE = "package"
    OUTPUT = "output"
    SOURCE_PATH = "source_path"


class CaptureOneToDLCompound(AbsTool):
    name = "Convert CaptureOne TIFF to Digital Library Compound Object"
    description = "Input is a path to a folder of TIFF files all named with " \
                  "a bibID as a prefacing identifier, a final delimiting " \
                  "underscore or dash, and a sequence consisting of padded " \
                  "zeroes and a number." \
                  "\n" \
                  "\nOutput is a directory to put the new packages." \
                  "\n" \
                  "\nInput:" \
                  "\n  + batch folder" \
                  "\n      - uniqueID1_00000001.tif" \
                  "\n      - uniqueID1_00000002.tif" \
                  "\n      - uniqueID1_00000003.tif" \
                  "\n      - uniqueID2_00000001.tif" \
                  "\n      - uniqueID2_00000002.tif" \
                  "\n" \
                  "\nOutput:" \
                  "\n + uniqueID1 (folder)" \
                  "\n     + preservation (folder)" \
                  "\n         - uniqueID1_00000001.tif" \
                  "\n         - uniqueID1_00000002.tif" \
                  "\n         - uniqueID1_00000003.tif" \
                  "\n     + access (folder)" \
                  "\n         - uniqueID1_00000001.jp2" \
                  "\n         - uniqueID1_00000002.jp2" \
                  "\n         - uniqueID1_00000003.jp2" \
                  "\n + uniqueID2 (folder)" \
                  "\n     + preservation (folder)" \
                  "\n         - uniqueID2_00000001.tif" \
                  "\n         - uniqueID2_00000002.tif" \
                  "\n     + access (folder)" \
                  "\n         - uniqueID2_00000001.jp2" \
                  "\n         - uniqueID2_00000002.jp2"
    active = True

    @staticmethod
    def discover_task_metadata(**user_args) -> typing.List[dict]:
        jobs = []
        source_input = user_args[UserArgs.INPUT.value]
        dest = user_args[UserArgs.OUTPUT.value]

        package_factory = uiucprescon.packager.PackageFactory(
            uiucprescon.packager.packages.CaptureOnePackage())

        for package in package_factory.locate_packages(source_input):
            jobs.append({
                JobValues.PACKAGE.value: package,
                JobValues.OUTPUT.value: dest,
                JobValues.SOURCE_PATH.value: source_input
            }
            )
        return jobs

    @staticmethod
    def new_job() -> typing.Type[worker.ProcessJobWorker]:
        return PackageConverter

    @staticmethod
    def get_user_options() -> typing.List[options.UserOption2]:
        return [
            options.UserOptionCustomDataType(UserArgs.INPUT.value,
                                             options.FolderData),

            options.UserOptionCustomDataType(UserArgs.OUTPUT.value,
                                             options.FolderData),
        ]


class PackageConverter(worker.ProcessJobWorker):

    @contextmanager
    def log_config(self, logger):
        gui_logger = worker.GuiLogHandler(self.log)
        try:
            logger.addHandler(gui_logger)
            yield
        finally:
            logger.removeHandler(gui_logger)

    def process(self, *args, **kwargs):
        my_logger = logging.getLogger(uiucprescon.packager.__name__)
        my_logger.setLevel(logging.INFO)
        with self.log_config(my_logger):
            existing_package = kwargs[JobValues.PACKAGE.value]
            new_package_root = kwargs[JobValues.OUTPUT.value]
            source_path = kwargs[JobValues.SOURCE_PATH.value]
            package_id = existing_package.metadata[Metadata.ID]

            self.log(f"Converting {package_id} from {source_path} "
                     f"to a Hathi Trust Tiff package at {new_package_root}")

            package_factory = uiucprescon.packager.PackageFactory(
                uiucprescon.packager.packages.DigitalLibraryCompound())

            package_factory.transform(existing_package, dest=new_package_root)
