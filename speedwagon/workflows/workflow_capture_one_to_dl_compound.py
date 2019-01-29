import logging

import uiucprescon
from typing import List, Any
from contextlib import contextmanager
from speedwagon import tasks
from speedwagon.job import AbsWorkflow
from speedwagon.tools import options
from speedwagon.worker import GuiLogHandler
from uiucprescon.packager.packages.collection_builder import Metadata


class CaptureOneToDlCompoundWorkflow(AbsWorkflow):
    name = "0 EXPERIMENTAL " \
           "Convert CaptureOne TIFF to Digital Library Compound Object"
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

        package_factory = uiucprescon.packager.PackageFactory(
            uiucprescon.packager.packages.CaptureOnePackage())

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
        super().create_new_task(task_builder, **job_args)


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
        my_logger = logging.getLogger(uiucprescon.packager.__name__)
        my_logger.setLevel(logging.INFO)
        with self.log_config(my_logger):
            self.log(
                f"Converting {self.packaging_id} from {self.source_path} "
                f"to a Hathi Trust Tiff package at {self.new_package_root}")

            package_factory = uiucprescon.packager.PackageFactory(
                uiucprescon.packager.packages.DigitalLibraryCompound())

            package_factory.transform(
                self.existing_package, dest=self.new_package_root)
        return True
