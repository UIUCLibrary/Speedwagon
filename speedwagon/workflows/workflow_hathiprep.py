"""Hathi Prep Workflow."""
import itertools
import os
from typing import Mapping, List, Any, Sequence, Dict, Union, Optional
import typing
from PySide6 import QtWidgets  # type: ignore

import uiucprescon.packager.packages
from uiucprescon.packager import PackageFactory
from uiucprescon.packager.packages import collection

import speedwagon
import speedwagon.tasks.prep
import speedwagon.tasks.packaging
import speedwagon.workflow
from speedwagon.workflows.title_page_selection import PackageBrowser
from . import shared_custom_widgets
__all__ = ['HathiPrepWorkflow']

from .shared_custom_widgets import UserOption2, UserOption3


class HathiPrepWorkflow(speedwagon.Workflow):
    """Workflow for Hathi prep."""

    name = "Hathi Prep"
    description = "Enables user to select, from a dropdown list of image " \
                  "file names, the title page to be displayed on the " \
                  "HathiTrust website for the item. This updates the .yml " \
                  "file.\n" \
                  "\n" \
                  "NB: It is useful to first identify the desired " \
                  "title page and associated filename in a separate image " \
                  "viewer." \


    def get_user_options(
            self
    ) -> List[speedwagon.workflow.AbsOutputOptionDataType]:

        package_type = speedwagon.workflow.DropDownSelection("Image File Type")
        package_type.placeholder_text = "Select an Image Format"
        package_type.add_selection("JPEG 2000")
        package_type.add_selection("TIFF")

        input_option = speedwagon.workflow.DirectorySelect("input")
        # options.append(input_option)
        options = [
            package_type,
            input_option
        ]

        return options

    def user_options(self) -> List[Union[UserOption2, UserOption3]]:
        """Get the user arguments for the workflow.

        Returns:
            Returns information about the package type and the source directory
        """
        options: List[Union[UserOption2, UserOption3]] = []
        package_type = shared_custom_widgets.ListSelection("Image File Type")
        package_type.add_selection("JPEG 2000")
        package_type.add_selection("TIFF")
        input_option = shared_custom_widgets.UserOptionCustomDataType(
            "input", shared_custom_widgets.FolderData)

        options.append(input_option)
        options.append(package_type)
        return options

    def initial_task(self,
                     task_builder: "speedwagon.tasks.tasks.TaskBuilder",
                     **user_args: str
                     ) -> None:
        """Look for any packages located in the input argument directory.

        Args:
            task_builder:
            **user_args:

        """
        root = user_args['input']
        task_builder.add_subtask(FindHathiPackagesTask(root))

    def discover_task_metadata(self,
                               initial_results: List[Any],
                               additional_data: Dict[str, Any],
                               **user_args) -> List[Dict[str, str]]:
        """Get enough information about the packages to create a new job.

        Args:
            initial_results:
            additional_data:
            **user_args:

        Returns:
            Returns a dictionary containing the title page, package id, and
                the source path.

        """
        jobs: List[Dict[str, str]] = []
        packages: Sequence[collection.Package] = additional_data["packages"]
        for package in packages:
            job: Dict[str, str] = {
                "package_id":
                    typing.cast(str, package.metadata[collection.Metadata.ID]),
                "title_page":
                    typing.cast(
                        str,
                        package.metadata[collection.Metadata.TITLE_PAGE]
                    ),
                "source_path":
                    typing.cast(
                        str,
                        package.metadata[collection.Metadata.PATH]
                    )
            }
            jobs.append(job)

        return jobs

    def create_new_task(self,
                        task_builder: "speedwagon.tasks.TaskBuilder",
                        **job_args: str
                        ) -> None:
        """Add yaml and checksum tasks.

        Args:
            task_builder:
            **job_args:

        """
        title_page = job_args['title_page']
        source = job_args['source_path']
        package_id = job_args['package_id']

        task_builder.add_subtask(
            subtask=speedwagon.tasks.prep.MakeMetaYamlTask(
                package_id,
                source,
                title_page
            )
        )

        task_builder.add_subtask(
            subtask=speedwagon.tasks.prep.GenerateChecksumTask(
                package_id,
                source
            )
        )

    def get_additional_info(self,
                            parent: typing.Optional[QtWidgets.QWidget],
                            options: Mapping[str, str],
                            pretask_results: list
                            ) -> Dict[str, List[collection.Package]]:
        """Request information from user about the title page.

        Args:
            parent:
            options:
            pretask_results:

        Returns:
            Returns the title page information

        """
        image_type = options['Image File Type']

        root_dir = options['input']
        if image_type == "TIFF":
            package_factory = PackageFactory(
                uiucprescon.packager.packages.HathiTiff())
        elif image_type == "JPEG 2000":
            package_factory = PackageFactory(
                uiucprescon.packager.packages.HathiJp2())
        else:
            raise ValueError(f"Unknown type {image_type}")

        browser = PackageBrowser(
            list(package_factory.locate_packages(root_dir)),
            parent
        )
        browser.exec()
        result = browser.result()
        if result != browser.Accepted:
            raise speedwagon.JobCancelled()
        # List[collection.Package]
        return {
            'packages': browser.data()
        }

    @classmethod
    def generate_report(cls, results: List[speedwagon.tasks.tasks.Result],
                        **user_args) -> Optional[str]:
        """Generate a report about prepping work.

        Args:
            results:
            **user_args:

        Returns:
            Returns a string explaining the prepped objects.

        """
        results_sorted = sorted(results, key=lambda x: x.source.__name__)
        _result_grouped = itertools.groupby(results_sorted, lambda x: x.source)
        results_grouped = {k: [i.data for i in v] for k, v in _result_grouped}

        num_checksum_files = len(
            results_grouped[speedwagon.tasks.prep.GenerateChecksumTask]
        )

        num_yaml_files = len(
            results_grouped[speedwagon.tasks.prep.MakeMetaYamlTask]
        )

        objects = {
            result['package_id']
            for result in results_grouped[
                speedwagon.tasks.prep.GenerateChecksumTask
            ]
        }

        for result in results_grouped[speedwagon.tasks.prep.MakeMetaYamlTask]:
            objects.add(result['package_id'])

        objects_prepped_list = "\n  ".join(objects)

        return f"HathiPrep Report:" \
               f"\n" \
               f"\nPrepped the following objects:" \
               f"\n  {objects_prepped_list}" \
               f"\n" \
               f"\nTotal files generated: " \
               f"\n  {num_checksum_files} checksum.md5 files" \
               f"\n  {num_yaml_files} meta.yml files"


class FindHathiPackagesTask(speedwagon.tasks.packaging.AbsFindPackageTask):

    def find_packages(self, search_path: str):
        def find_dirs(item: os.DirEntry) -> bool:

            if not item.is_dir():
                return False
            return True

        directories = []

        for directory in filter(find_dirs, os.scandir(search_path)):
            directories.append(directory.path)
            self.log(f"Located {directory.name}")

        return directories
