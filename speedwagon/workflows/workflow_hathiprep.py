"""Hathi Prep Workflow."""
import itertools
import os
from typing import List, Any, Sequence, Dict, Optional
import typing

from uiucprescon.packager.packages import collection
from uiucprescon.packager.common import Metadata

import speedwagon
import speedwagon.tasks.prep
import speedwagon.tasks.packaging
import speedwagon.workflow
from speedwagon.frontend.interaction import UserRequestFactory, DataItem

__all__ = ['HathiPrepWorkflow']


class TitlePageResults(typing.TypedDict):
    title_pages: Dict[str, Optional[str]]
    # title_pages: Dict[str, str]


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


    def job_options(
            self
    ) -> List[speedwagon.workflow.AbsOutputOptionDataType]:
        """Get user options.

        User Settings:
            * input - folder used as a source path
            * Image File Type - select the type of file to use

        """
        package_type = speedwagon.workflow.ChoiceSelection("Image File Type")
        package_type.placeholder_text = "Select an Image Format"
        package_type.add_selection("JPEG 2000")
        package_type.add_selection("TIFF")

        input_option = speedwagon.workflow.DirectorySelect("input")

        return [
            input_option,
            package_type,
        ]

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

    def get_additional_info(
            self,
            user_request_factory: UserRequestFactory,
            options: dict,
            pretask_results: list
    ) -> dict:
        """Request title pages information for the packages from the user."""
        if len(pretask_results) != 1:
            return {}

        def process_data(
                data: List[Sequence[DataItem]]
        ) -> TitlePageResults:
            return {
                "title_pages": {
                    typing.cast(str, row[0].value): row[1].value
                    for row in data
                }
            }

        def data_gathering_callback(
                results,  # pylint: disable=unused-argument
                pretask_results
        ) -> List[Sequence[DataItem]]:
            rows: List[Sequence[DataItem]] = []
            values = pretask_results[0]
            for package in values.data:
                title_page = DataItem(
                    name="Title Page",
                    value=package.metadata[Metadata.TITLE_PAGE]
                )
                title_page.editable = True
                files = []
                for i in package:
                    for instance in i.instantiations.values():
                        files += [os.path.basename(f) for f in instance.files]
                title_page.possible_values = files

                rows.append(
                    (
                        DataItem(
                            name="Object",
                            value=package.metadata[Metadata.ID]
                        ),
                        title_page,
                        DataItem(
                            name="Location",
                            value=package.metadata[Metadata.PATH]
                        )
                    )
                )

            return rows

        selection_editor = user_request_factory.table_data_editor(
            enter_data=data_gathering_callback,
            process_data=process_data
        )
        selection_editor.title = "Title Page Selection"
        selection_editor.column_names = ["Object", "Title Page", "Location"]
        return selection_editor.get_user_response(options, pretask_results)

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

    def find_packages(self, search_path: str) -> List[str]:
        def find_dirs(item: os.DirEntry) -> bool:

            if not item.is_dir():
                return False
            return True

        directories = []

        for directory in filter(find_dirs, os.scandir(search_path)):
            directories.append(directory.path)
            self.log(f"Located {directory.name}")

        return directories
