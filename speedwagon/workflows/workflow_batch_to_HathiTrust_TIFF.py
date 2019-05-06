import itertools
import os
import typing

from PyQt5 import QtWidgets  # type: ignore
from uiucprescon.packager.packages.collection import Metadata

import speedwagon
from speedwagon import tasks
from speedwagon.workflows import shared_custom_widgets
from uiucprescon import packager, pygetmarc
from . title_page_selection import PackageBrowser
from pyhathiprep import package_creater
import shutil


class CaptureOneBatchToHathiComplete(speedwagon.Workflow):
    name = "CaptureOne Batch to HathiTrust TIFF Complete Package"
    description = "This workflow chains together a number of tools to take " \
                  "a batch of CaptureOne files and structure them as " \
                  "HathiTrust compliant packages. This includes putting " \
                  "them in the correct folder structure, importing MARC.XML " \
                  "files, generating YAML files, and generating a checksum " \
                  "file. It takes as its input a folder of CaptureOne batch " \
                  "files. It takes as its output a folder location where " \
                  "new files will be written."

    def discover_task_metadata(self, initial_results: typing.List[typing.Any],
                               additional_data,
                               **user_args) -> typing.List[dict]:
        tasks_metadata = []
        if len(initial_results) == 1:
            packages = initial_results.pop()
            for package in packages.data:

                bib_id = package.metadata[Metadata.ID]

                try:
                    title_page = additional_data["title_pages"][bib_id]
                except KeyError:
                    print("Unable to locate title page for {}".format(bib_id))
                    title_page = None

                tasks_metadata.append(
                    {"package": package,
                     "destination": user_args['Destination'],
                     "title_page": title_page
                     }
                )
        return tasks_metadata

    def user_options(self):
        source = shared_custom_widgets.UserOptionCustomDataType(
            "Source", shared_custom_widgets.FolderData)

        destination = shared_custom_widgets.UserOptionCustomDataType(
            "Destination", shared_custom_widgets.FolderData)

        return [source, destination]

    def initial_task(self, task_builder: tasks.TaskBuilder,
                     **user_args) -> None:
        super().initial_task(task_builder, **user_args)
        root = user_args['Source']
        task_builder.add_subtask(FindPackageTask(root=root))

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):

        package = job_args['package']
        destination_root = job_args['destination']
        title_page = job_args['title_page']

        # Package metadata
        bib_id = package.metadata[Metadata.ID]

        new_package_location = os.path.join(destination_root, bib_id)

        # Add the tasks
        # Transform the package into a HathiTiff package
        task_builder.add_subtask(
            subtask=TransformPackageTask(package, destination_root))

        # Generate marc file from the Bib id
        task_builder.add_subtask(
            subtask=GenerateMarcTask(
                bib_id=bib_id, destination=new_package_location)
        )

        # Generate a meta.yml file
        task_builder.add_subtask(
            subtask=MakeYamlTask(bib_id, new_package_location, title_page))

        # Generate checksum data
        task_builder.add_subtask(
            subtask=GenerateChecksumTask(bib_id, new_package_location))

    def get_additional_info(self, parent: QtWidgets.QWidget, options: dict,
                            pretask_results: list) -> dict:
        extra_data = {}
        if len(pretask_results) == 1:
            title_pages = dict()
            results = pretask_results.pop()
            packages = results.data
            browser = PackageBrowser(packages, parent)
            browser.exec()

            if browser.result() != browser.Accepted:
                raise speedwagon.JobCancelled()
            data = browser.data()
            for package in data:
                bib_id = package.metadata[Metadata.ID]

                title_page = package.metadata[Metadata.TITLE_PAGE]

                title_pages[bib_id] = title_page
            extra_data["title_pages"] = title_pages

        return extra_data

    @classmethod
    def generate_report(cls, results: typing.List[tasks.Result],
                        **user_args) -> typing.Optional[str]:

        results_sorted = sorted(results, key=lambda x: x.source.__name__)
        _result_grouped = itertools.groupby(results_sorted, lambda x: x.source)
        results_grouped = dict()

        for k, v in _result_grouped:
            results_grouped[k] = [i.data for i in v]

        package_transformed = results_grouped[TransformPackageTask]
        marc_files_generated = results_grouped[GenerateMarcTask]
        yaml_results = results_grouped[MakeYamlTask]
        checksum_files_generated = results_grouped[GenerateChecksumTask]

        package_transformed_message = "{} objects transformed".format(
            len(package_transformed))

        marc_files_message = "{} marc.xml files generated".format(
            len(marc_files_generated))

        yaml_file_message = "{} meta.yml files generated".format(
            len(yaml_results)
        )

        checksum_message = "{} checksum.md5 files generated".format(
            len(checksum_files_generated)
        )

        message = f"Results:\n" \
                  f"* {package_transformed_message}\n" \
                  f"* {marc_files_message}\n" \
                  f"* {yaml_file_message}\n" \
                  f"* {checksum_message}"
        return message


class TransformPackageTask(tasks.Subtask):

    def __init__(self, package: packager.packages.collection.PackageObject,
                 destination) -> None:
        super().__init__()
        self._package = package
        self._destination = destination

        self._bib_id = \
            self._package.metadata[Metadata.ID]

    def work(self) -> bool:
        package_factory = packager.PackageFactory(
            packager.packages.HathiTiff()
        )
        package_factory.transform(self._package, self._destination)

        self.log("Transformed CaptureOne package {} to a HathiTiff package "
                 "in {}".format(self._bib_id, self._destination))
        self.set_results(
            {
                "bib_id": self._bib_id,
                "location: ": os.path.join(self._destination, self._bib_id)
             }
        )
        return True


class FindPackageTask(tasks.Subtask):

    def __init__(self, root) -> None:
        super().__init__()
        self._root = root

    def work(self) -> bool:
        self.log("Locating packages in {}".format(self._root))

        package_factory = packager.PackageFactory(
            packager.packages.CaptureOnePackage()
        )

        packages = [job for job in package_factory.locate_packages(self._root)]

        self.set_results(packages)

        return True


class GenerateMarcTask(tasks.Subtask):

    def __init__(self, bib_id, destination) -> None:
        super().__init__()

        self._bib_id = bib_id
        self._destination = destination

    def work(self) -> bool:
        self.log(f"Retrieving marc record for {self._bib_id}")
        marc_file = os.path.join(self._destination, "marc.xml")
        result: typing.Dict[str, typing.Optional[typing.Union[str, bool]]] = {}

        try:
            marc = pygetmarc.get_marc(int(self._bib_id))

            with open(marc_file, "w", encoding="utf-8-sig") as f:
                f.write(f"{marc}\n")
            self.log(f"Generated marc.xml in {self._destination}")
            success = True
            result["location"] = marc_file
        except ValueError:

            self.log(
                f"Error! Could not retrieve marc record for {self._bib_id}"
            )
            success = False
            result['location'] = None

        result["success"] = success

        self.set_results(result)
        return success


class MakeYamlTask(tasks.Subtask):
    def __init__(self, bib_id, source, title_page) -> None:
        super().__init__()

        self._source = source
        try:
            self._title_page = title_page.split("_")[1]
        except KeyError:
            print("Unable to split {} with a _ delimiter".format(title_page))
            self._title_page = title_page
        self._bib_id = bib_id

    def work(self):
        meta_filename = "meta.yml"
        self.log("Generating meta.yml for {}".format(self._bib_id))
        package_builder = package_creater.InplacePackage(self._source)
        package_builder.make_yaml(build_path=self.subtask_working_dir,
                                  title_page=self._title_page)

        meta_yml = os.path.join(self.subtask_working_dir, meta_filename)
        dest = os.path.join(self._source, meta_filename)
        successful = os.path.exists(meta_yml)
        assert successful

        shutil.move(meta_yml, dest)
        assert os.path.exists(dest)
        self.log("Added meta.yml to {}".format(self._source))

        self.set_results(
            {
                "source": self._source,
                "meta.yml": dest,
                "package_id": self._bib_id
            }
        )

        return successful


class GenerateChecksumTask(speedwagon.tasks.Subtask):

    def __init__(self, bib_id, source) -> None:
        super().__init__()
        self._source = source
        self._bib_id = bib_id

    def work(self) -> bool:
        checksum_filename = "checksum.md5"
        self.log("Generating checksums for {}".format(self._bib_id))
        package_builder = package_creater.InplacePackage(self._source)
        package_builder.create_checksum_report(self.subtask_working_dir)

        generated_checksum_file = os.path.join(
            self.subtask_working_dir, checksum_filename)

        dest = os.path.join(self._source, checksum_filename)

        success = os.path.exists(generated_checksum_file)
        assert success

        shutil.move(generated_checksum_file, dest)
        assert os.path.exists(dest)
        self.log("Added checksum.md5 to {}".format(self._source))

        self.set_results(
            {
                "source": self._source,
                "checksum": dest,
                "package_id": self._bib_id
            }
        )
        return success
