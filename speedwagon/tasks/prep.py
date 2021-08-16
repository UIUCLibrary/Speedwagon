import os
import shutil
from typing import Optional

from pyhathiprep import package_creater

import speedwagon


class FindPackagesTask(speedwagon.tasks.Subtask):
    name = "Locate Packages"

    def __init__(self, root: str) -> None:
        super().__init__()
        self._root = root

    def task_description(self) -> Optional[str]:
        return f"Locating packages in {self._root}"

    def work(self) -> bool:
        self.log("Locating packages in {}".format(self._root))

        def find_dirs(item: os.DirEntry) -> bool:

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
    name = "Create meta.yml"

    def __init__(self, package_id: str, source: str, title_page: str) -> None:
        super().__init__()

        self._source = source
        self._title_page = title_page
        self._package_id = package_id

    def task_description(self) -> Optional[str]:
        return f"Creating meta.yml in {self._source}"

    def work(self) -> bool:
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
    name = "Generate Checksum"

    def __init__(self, package_id: str, source: str) -> None:
        super().__init__()
        self._source = source
        self._package_id = package_id

    def task_description(self) -> Optional[str]:
        return f"Generating checksums for files in {self._source}"

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
    name = "Prep"

    def __init__(self, source: str, title_page: str) -> None:
        super().__init__()

        self._source = source
        self._title_page = title_page

    def task_description(self) -> Optional[str]:
        return f"Prepping {self._source}"

    def work(self) -> bool:
        self.log("Prepping on {}".format(self._source))
        package_builder = package_creater.InplacePackage(self._source)
        package_builder.generate_package(destination=self._source,
                                         title_page=self._title_page)
        return True
