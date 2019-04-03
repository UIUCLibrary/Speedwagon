import logging
import sys
import traceback

from uiucprescon import packager
from typing import List, Any
from contextlib import contextmanager
from speedwagon import tasks
from speedwagon.job import AbsWorkflow
from speedwagon.tools import options
from speedwagon.worker import GuiLogHandler
from uiucprescon.packager.packages.collection_builder import Metadata


class CaptureOneToDlCompoundAndDLWorkflow(AbsWorkflow):
    name = "Convert CaptureOne TIFF to Digital Library Compound Object and HathiTrust"
    description = "Input is a path to a folder of TIFF files all named with " \
                  "a bibID as a prefacing identifier, a final delimiting " \
                  "underscore or dash, and a sequence consisting of padded " \
                  "zeroes and a number." \
                  "\n" \
                  "\nOutput Hathi is a directory to put the new packages " \
                  "for HathiTrust."

    active = True

    def user_options(self):
        return [
            options.UserOptionCustomDataType("Input", options.FolderData),
            options.UserOptionCustomDataType("Output Digital Library", options.FolderData),
            options.UserOptionCustomDataType("Output HathiTrust", options.FolderData),
                ]

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        jobs = []
        source_input = user_args["Input"]
        dest_dl = user_args["Output Digital Library"]
        dest_ht = user_args["Output HathiTrust"]

        package_factory = packager.PackageFactory(
            packager.packages.CaptureOnePackage())
        try:
            for package in package_factory.locate_packages(source_input):
                jobs.append({
                    "package": package,
                    "output_dl": dest_dl,
                    "output_ht": dest_ht,
                    "source_path": source_input
                }
                )
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            print(e)
        return jobs

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        existing_package = job_args['package']
        new_dl_package_root = job_args["output_dl"]
        new_ht_package_root = job_args["output_ht"]
        source_path = job_args["source_path"]
        package_id = existing_package.metadata[Metadata.ID]
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
    name = "Package Conversion"
    package_formats = {
        "Digital Library Compound": packager.packages.DigitalLibraryCompound(),
        "HathiTrust jp2": packager.packages.HathiJp2()
    }
    @contextmanager
    def log_config(self, logger):
        gui_logger = GuiLogHandler(self.log)
        try:
            logger.addHandler(gui_logger)
            yield
        finally:
            logger.removeHandler(gui_logger)

    def __init__(self, source_path, packaging_id,
                 existing_package, new_package_root,
                 package_format) -> None:

        super().__init__()
        self.packaging_id = packaging_id
        self.existing_package = existing_package
        self.new_package_root = new_package_root
        if package_format not in PackageConverter.package_formats.keys():
            raise ValueError(f"{package_format} is not a known value")
        self.package_format = package_format
        self.source_path = source_path

    def work(self):
        my_logger = logging.getLogger(packager.__name__)
        my_logger.setLevel(logging.INFO)
        with self.log_config(my_logger):
            self.log(
                f"Converting {self.packaging_id} from {self.source_path} "
                f"to a {self.package_format} package at {self.new_package_root}")
            package_factory = packager.PackageFactory(
                PackageConverter.package_formats[self.package_format])

            package_factory.transform(
                self.existing_package, dest=self.new_package_root)
        return True
