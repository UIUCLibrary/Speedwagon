import itertools
import os
import shutil
import typing

from PyQt5 import QtWidgets

import speedwagon.tasks
import speedwagon

from speedwagon.tools import options as tool_options

import uiucprescon.packager.packages
from uiucprescon.packager import PackageFactory
from uiucprescon.packager.packages import collection

from pyhathiprep import package_creater

from speedwagon.workflows.title_page_selection import PackageBrowser


class HathiPrepWorkflow(speedwagon.Workflow):
    name = "Hathi Prep"
    description = "Something goes here later"

    def user_options(self):
        options = []
        package_type = tool_options.ListSelection("Image File Type")
        package_type.add_selection("JPEG 2000")
        package_type.add_selection("TIFF")
        input_option = tool_options.UserOptionCustomDataType(
            "input", tool_options.FolderData)

        options.append(input_option)
        options.append(package_type)
        return options

    def initial_task(self, task_builder: speedwagon.tasks.TaskBuilder,
                     **user_args) -> None:

        root = user_args['input']
        task_builder.add_subtask(FindPackagesTask(root))

    def discover_task_metadata(self, initial_results: typing.List[typing.Any],
                               additional_data,
                               **user_args) -> typing.List[dict]:
        jobs = []
        for package in additional_data["packages"]:
            job = {
                "package_id": package.metadata[collection.Metadata.ID],
                "title_page": package.metadata[collection.Metadata.TITLE_PAGE],
                "source_path": package.metadata[collection.Metadata.PATH]
            }
            jobs.append(job)

        return jobs

    def create_new_task(self, task_builder: "speedwagon.tasks.TaskBuilder",
                        **job_args):
        title_page = job_args['title_page']
        source = job_args['source_path']
        package_id = job_args['package_id']

        task_builder.add_subtask(
            subtask=MakeYamlTask(package_id, source, title_page))

        task_builder.add_subtask(
            subtask=GenerateChecksumTask(package_id, source))

    def get_additional_info(self, parent: QtWidgets.QWidget, options: dict,
                            initial_results: list) -> dict:
        image_type = options['Image File Type']

        root_dir = options['input']
        if image_type == "TIFF":
            package_factory = PackageFactory(
                uiucprescon.packager.packages.HathiTiff())
        elif image_type == "JPEG 2000":
            package_factory = PackageFactory(
                uiucprescon.packager.packages.HathiJp2())
        else:
            raise ValueError("Unknown type {}".format(image_type))

        packages = [package for package in
                    package_factory.locate_packages(root_dir)]
        browser = PackageBrowser(packages, parent)
        browser.exec()
        result = browser.result()
        if result != browser.Accepted:
            raise speedwagon.JobCancelled()

        extra = {
            'packages': browser.data()
        }

        return extra

    @classmethod
    def generate_report(cls, results: typing.List[speedwagon.tasks.Result],
                        **user_args) -> typing.Optional[str]:
        results_sorted = sorted(results, key=lambda x: x.source.__name__)
        _result_grouped = itertools.groupby(results_sorted, lambda x: x.source)
        results_grouped = dict()

        for k, v in _result_grouped:
            results_grouped[k] = [i.data for i in v]

        objects = set()

        num_checksum_files = len(results_grouped[GenerateChecksumTask])
        num_yaml_files = len(results_grouped[MakeYamlTask])

        for result in results_grouped[GenerateChecksumTask]:
            objects.add(result['package_id'])

        for result in results_grouped[MakeYamlTask]:
            objects.add(result['package_id'])

        objects_prepped_list = "\n  ".join(objects)

        process_report = f"HathiPrep Report:" \
                         f"\n" \
                         f"\nPrepped the following objects:" \
                         f"\n  {objects_prepped_list}" \
                         f"\n" \
                         f"\nTotal files generated: " \
                         f"\n  {num_checksum_files} checksum.md5 files" \
                         f"\n  {num_yaml_files} meta.yml files" \

        return process_report


class FindPackagesTask(speedwagon.tasks.Subtask):

    def __init__(self, root) -> None:
        super().__init__()
        self._root = root

    def work(self) -> bool:
        self.log("Locating packages in {}".format(self._root))

        def find_dirs(item: os.DirEntry):

            if not item.is_dir():
                return False
            return True

        directories = []

        for directory in filter(find_dirs, os.scandir(self._root)):
            directories.append(directory.path)
            self.log(f"Located {directory.name}")
        self.set_results(directories)

        return True


class MakeYamlTask(speedwagon.tasks.Subtask):
    def __init__(self, package_id, source, title_page) -> None:
        super().__init__()

        self._source = source
        self._title_page = title_page
        self._package_id = package_id
        # self._working_dir = subtask_working_dir

    def work(self):
        meta_filename = "meta.yml"
        self.log("Generating meta.yml for {}".format(self._package_id))
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
                "package_id": self._package_id
            }
        )

        return successful


class GenerateChecksumTask(speedwagon.tasks.Subtask):

    def __init__(self, package_id, source) -> None:
        super().__init__()
        self._source = source
        self._package_id = package_id

    def work(self) -> bool:
        checksum_filename = "checksum.md5"
        self.log("Generating checksums for {}".format(self._package_id))
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
                "package_id": self._package_id
            }
        )
        return success


class PrepTask(speedwagon.tasks.Subtask):

    def __init__(self, source, title_page) -> None:
        super().__init__()

        self._source = source
        self._title_page = title_page

    def work(self) -> bool:
        self.log("Prepping on {}".format(self._source))
        package_builder = package_creater.InplacePackage(self._source)
        package_builder.generate_package(destination=self._source,
                                         title_page=self._title_page)
        return True
