"""Workflow for batch converting HathiTrust tiff files."""

import itertools
import os
import warnings
from typing import Dict, Optional, List, Any, Type, Mapping
import typing
from collections.abc import Sized
from PySide6 import QtWidgets  # type: ignore
from uiucprescon.packager.packages.collection import Metadata
from uiucprescon import packager

import speedwagon
import speedwagon.tasks.packaging
import speedwagon.tasks.prep
from speedwagon.workflows import shared_custom_widgets, workflow_get_marc
from . title_page_selection import PackageBrowser
from .workflow_get_marc import UserOptions

__all__ = ['CaptureOneBatchToHathiComplete']


class CaptureOneBatchToHathiComplete(speedwagon.Workflow):
    """CaptureOne Batch to HathiTrust TIFF Complete Package.

    .. versionadded:: 0.1.5
        Supports MMSID and bibid id types
    """

    name = "CaptureOne Batch to HathiTrust TIFF Complete Package"
    description = "This workflow chains together a number of tools to take " \
                  "a batch of CaptureOne files and structure them as " \
                  "HathiTrust compliant packages. This includes putting " \
                  "them in the correct folder structure, importing MARC.XML " \
                  "files, generating YAML files, and generating a checksum " \
                  "file. It takes as its input a folder of CaptureOne batch " \
                  "files. It takes as its output a folder location where " \
                  "new files will be written."
    active = False

    def __init__(self,
                 global_settings: Optional[Dict[str, str]] = None
                 ) -> None:
        """Convert CaptureOne Batch to HathiTrust TIFF Complete Package.

        Args:
            global_settings:
                Settings that could affect the way the workflow runs.
        """
        warnings.warn(
            "Pending removal of CaptureOne Batch to HathiTrust TIFF Complete "
            "Package",
            DeprecationWarning
        )

        super().__init__()

        if global_settings is not None:
            self.global_settings = global_settings

    def discover_task_metadata(self, initial_results: List[
        speedwagon.tasks.Result],
                               additional_data: Dict[str, Any],
                               **user_args: str) -> List[Dict[str, str]]:
        server_url = self.global_settings.get("getmarc_server_url")
        tasks_metadata: List[Dict[str, Any]] = []
        if len(initial_results) == 1:
            packages = initial_results.pop()
            for package in packages.data:

                package_id = package.metadata[Metadata.ID]

                try:
                    title_page = additional_data["title_pages"][package_id]
                except KeyError:
                    print(f"Unable to locate title page for {package_id}")
                    title_page = None

                tasks_metadata.append(
                    {
                        "package": package,
                        "destination": user_args['Destination'],
                        "title_page": title_page,
                        'server_url': server_url,
                        'identifier_type': user_args['Identifier type']
                     }
                )
        return tasks_metadata

    def user_options(self) -> List[UserOptions]:
        suppoted_identifer_types: List[str] = [
            "Bibid",
            "MMS ID"
        ]
        workflow_options: List[UserOptions] = [
            shared_custom_widgets.UserOptionCustomDataType(
                "Source", shared_custom_widgets.FolderData
            ),
            shared_custom_widgets.UserOptionCustomDataType(
                "Destination", shared_custom_widgets.FolderData
            )
        ]
        id_type_option = shared_custom_widgets.ListSelection("Identifier type")
        for id_type in suppoted_identifer_types:
            id_type_option.add_selection(id_type)
        workflow_options.append(id_type_option)
        return workflow_options

    def initial_task(self, task_builder: speedwagon.tasks.TaskBuilder,
                     **user_args: str) -> None:
        super().initial_task(task_builder, **user_args)
        root = user_args['Source']
        task_builder.add_subtask(FindCaptureOnePackageTask(root=root))

    def create_new_task(
            self,
            task_builder: speedwagon.tasks.TaskBuilder,
            **job_args
    ) -> None:
        """Create new tasks."""
        package = job_args['package']
        destination_root: str = job_args['destination']
        title_page: str = job_args['title_page']

        # Package metadata
        package_id: str = package.metadata[Metadata.ID]

        new_package_location = os.path.join(destination_root, package_id)

        # Add the tasks
        # Transform the package into a HathiTiff package
        task_builder.add_subtask(
            subtask=TransformPackageTask(package, destination_root))
        # Generate marc file from the Package id
        identifier_type = job_args['identifier_type']
        task_builder.add_subtask(
            subtask=workflow_get_marc.MarcGeneratorTask(
                identifier=package_id,
                identifier_type=identifier_type,
                output_name=os.path.join(
                    new_package_location,
                    "MARC.xml"
                ),
                server_url=str(job_args['server_url'])

            )
        )

        # Generate a meta.yml file
        task_builder.add_subtask(
            subtask=speedwagon.tasks.prep.MakeMetaYamlTask(
                package_id,
                new_package_location,
                title_page
            )
        )
        # Generate checksum data
        task_builder.add_subtask(
            subtask=speedwagon.tasks.prep.GenerateChecksumTask(
                package_id,
                new_package_location
            )
        )

    def get_additional_info(self,
                            parent: typing.Optional[QtWidgets.QWidget],
                            options: Mapping[Any, Any],
                            pretask_results: List[speedwagon.tasks.Result]
                            ) -> Dict[str, Any]:
        """Request the title page information from the user."""
        extra_data: Dict[str, Dict[str, str]] = {}
        if len(pretask_results) == 1:
            title_pages: Dict[str, str] = {}
            results = pretask_results.pop()
            packages = results.data
            browser = PackageBrowser(packages, parent)
            browser.exec()

            if browser.result() != browser.Accepted:
                raise speedwagon.JobCancelled()
            data = browser.data()
            for package in data:
                bib_id = typing.cast(str, package.metadata[Metadata.ID])

                title_page = \
                    typing.cast(str, package.metadata[Metadata.TITLE_PAGE])

                title_pages[bib_id] = title_page
            extra_data["title_pages"] = title_pages

        return extra_data

    @classmethod
    def generate_report(cls, results: List[speedwagon.tasks.Result],
                        **user_args: str) -> Optional[str]:
        subtask_type = Type[speedwagon.tasks.tasks.AbsSubtask]
        results_grouped: Mapping[subtask_type, Sized] = \
            cls.group_results(
                sorted(results, key=lambda x: x.source.__name__)
            )
        package_transformed = results_grouped.get(TransformPackageTask, [])

        marc_files_generated = results_grouped.get(
            workflow_get_marc.MarcGeneratorTask,
            []
        )

        yaml_results = results_grouped.get(
            speedwagon.tasks.prep.MakeMetaYamlTask,
            []
        )

        checksum_files_generated = results_grouped.get(
            speedwagon.tasks.prep.GenerateChecksumTask,
            []
        )

        package_transformed_message = \
            f"{len(package_transformed)} objects transformed"

        marc_files_message = \
            f"{len(marc_files_generated)} marc.xml files generated"

        yaml_file_message = f"{len(yaml_results)} meta.yml files generated"

        checksum_message = \
            f"{len(checksum_files_generated)} checksum.md5 files generated"

        return f"Results:\n" \
               f"* {package_transformed_message}\n" \
               f"* {marc_files_message}\n" \
               f"* {yaml_file_message}\n" \
               f"* {checksum_message}"

    @classmethod
    def group_results(
            cls,
            results_sorted: List[speedwagon.tasks.Result]
    ) -> Dict[Type[speedwagon.tasks.tasks.AbsSubtask], List[Any]]:
        result_grouped = itertools.groupby(results_sorted, lambda x: x.source)
        return {
            key: [i.data for i in value] for key, value in result_grouped
        }


class TransformPackageTask(speedwagon.tasks.Subtask):
    name = "Transform Package"

    def __init__(self, package: packager.packages.collection.Package,
                 destination: str) -> None:
        super().__init__()
        self._package = package
        self._destination = destination
        self._bib_id: str = \
            typing.cast(str, self._package.metadata[Metadata.ID])

    def task_description(self) -> Optional[str]:
        return "Transforming CaptureOne package"

    def work(self) -> bool:
        package_factory = packager.PackageFactory(
            packager.packages.HathiTiff()
        )
        package_factory.transform(self._package, self._destination)

        self.log(
            f"Transformed CaptureOne package {self._bib_id} to a HathiTiff "
            f"package in {self._destination}"
        )

        self.set_results(
            {
                "bib_id": self._bib_id,
                "location": os.path.join(self._destination, self._bib_id)
             }
        )
        return True


class FindCaptureOnePackageTask(speedwagon.tasks.packaging.AbsFindPackageTask):

    def find_packages(self, search_path: str):
        package_factory = packager.PackageFactory(
            packager.packages.CaptureOnePackage()
        )

        return list(package_factory.locate_packages(self._root))
