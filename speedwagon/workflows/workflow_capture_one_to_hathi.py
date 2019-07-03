import logging
from typing import List, Any
from contextlib import contextmanager
from uiucprescon import packager
from speedwagon import tasks
from speedwagon.job import AbsWorkflow
from . import shared_custom_widgets as options
from speedwagon.worker import GuiLogHandler

from uiucprescon.packager.packages.collection_builder import Metadata


class CaptureOneToHathiTiffPackageWorkflow(AbsWorkflow):
    name = "Convert CaptureOne TIFF to Hathi TIFF package"
    description = "This workflow chains together a number of tools to take " \
                  "a batch of CaptureOne files and structure them as " \
                  "HathiTrust packages. This includes putting them in the " \
                  "correct folder structure, importing MARC.XML files, " \
                  "generating YAML files, and generating a checksum file. " \
                  "It takes as its input a folder of CaptureOne batch " \
                  "files. It takes as its output a folder location where " \
                  "new files will be written."
    active = True

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:

        jobs = []
        source_input = user_args["Input"]
        dest = user_args["Output"]

        package_factory = packager.PackageFactory(
            packager.packages.CaptureOnePackage())

        for package in package_factory.locate_packages(source_input):
            jobs.append({
                "package": package,
                "output": dest,
                "source_path": source_input
            }
            )
        return jobs

    def user_options(self):
        return [
            options.UserOptionCustomDataType("Input", options.FolderData),
            options.UserOptionCustomDataType("Output", options.FolderData)
            ]

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
            self.log(f"Converting {self.packaging_id} from "
                     f"{self.source_path} to a Hathi Trust Tiff "
                     f"package at {self.new_package_root}")

            package_factory = packager.PackageFactory(
                packager.packages.HathiTiff())
            package_factory.transform(self.existing_package,
                                      dest=self.new_package_root)
        return True
