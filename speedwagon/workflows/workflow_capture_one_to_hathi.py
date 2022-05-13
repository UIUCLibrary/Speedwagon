"""Workflow for converting capture one packages to Hathi packages."""

import logging
import typing
import warnings
from typing import List, Any, Dict, Optional
from uiucprescon import packager
from uiucprescon.packager.packages.collection_builder import Metadata

import speedwagon.tasks.tasks
from speedwagon import utils
from speedwagon.job import Workflow


__all__ = ['CaptureOneToHathiTiffPackageWorkflow']


class CaptureOneToHathiTiffPackageWorkflow(Workflow):
    name = "Convert CaptureOne TIFF to Hathi TIFF package"
    description = "This workflow chains together a number of tools to take " \
                  "a batch of CaptureOne files and structure them as " \
                  "HathiTrust packages. This includes putting them in the " \
                  "correct folder structure, importing MARC.XML files, " \
                  "generating YAML files, and generating a checksum file. " \
                  "It takes as its input a folder of CaptureOne batch " \
                  "files. It takes as its output a folder location where " \
                  "new files will be written."
    active = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        warnings.warn(
            "Pending removal of Convert CaptureOne TIFF to Hathi TIFF package",
            DeprecationWarning
        )

    def discover_task_metadata(
            self,
            initial_results: List[Any],
            additional_data: Dict[str, Any],
            **user_args: str
    ) -> List[typing.Dict[str, Any]]:

        source_input: str = user_args["Input"]
        dest: str = user_args["Output"]

        package_factory = packager.PackageFactory(
            packager.packages.CaptureOnePackage())

        jobs: List[typing.Dict[str, Any]] = []
        for package in package_factory.locate_packages(source_input):
            jobs.append({
                "package": package,
                "output": dest,
                "source_path": source_input
            }
            )
        return jobs

    def create_new_task(
            self,
            task_builder: speedwagon.tasks.tasks.TaskBuilder,
            **job_args
    ) -> None:

        existing_package = job_args['package']
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


class PackageConverter(speedwagon.tasks.tasks.Subtask):
    name = "Convert Package"

    def __init__(
            self,
            source_path: str,
            packaging_id: str,
            existing_package,
            new_package_root: str
    ) -> None:

        super().__init__()
        self.packaging_id = packaging_id
        self.existing_package = existing_package
        self.new_package_root = new_package_root
        self.source_path = source_path

    def task_description(self) -> Optional[str]:
        return f"Converting package from {self.source_path}"

    def work(self) -> bool:
        my_logger = logging.getLogger(packager.__name__)
        my_logger.setLevel(logging.INFO)
        with utils.log_config(my_logger, self.log):
            self.log(f"Converting {self.packaging_id} from "
                     f"{self.source_path} to a Hathi Trust Tiff "
                     f"package at {self.new_package_root}")

            package_factory = packager.PackageFactory(
                packager.packages.HathiTiff())
            package_factory.transform(self.existing_package,
                                      dest=self.new_package_root)
        return True
