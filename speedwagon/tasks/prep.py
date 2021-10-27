"""Tasks relating to preparing a workspace."""

import os
import shutil
from typing import Optional

from pyhathiprep import package_creater

import speedwagon


class MakeMetaYamlTask(speedwagon.tasks.Subtask):
    """HathiTrust YAML creation task."""

    name = "Create meta.yml"

    def __init__(self, package_id: str, source: str, title_page: str) -> None:
        """Create a YAML creation task."""
        super().__init__()

        self._source = source
        self._title_page = title_page
        self._package_id = package_id

    def task_description(self) -> Optional[str]:
        """Get user readable information about what the subtask is doing."""
        return f"Creating meta.yml in {self._source}"

    def work(self) -> bool:
        """Perform the job."""
        meta_filename = "meta.yml"
        self.log(f"Generating meta.yml for {self._package_id}")
        package_builder = package_creater.InplacePackage(self._source)
        package_builder.make_yaml(build_path=self.subtask_working_dir,
                                  title_page=self._title_page)

        meta_yml = os.path.join(self.subtask_working_dir, meta_filename)
        dest = os.path.join(self._source, meta_filename)
        successful = os.path.exists(meta_yml)
        assert successful

        shutil.move(meta_yml, dest)
        assert os.path.exists(dest)
        self.log(f"Added meta.yml to {self._source}")

        self.set_results(
            {
                "source": self._source,
                "meta.yml": dest,
                "package_id": self._package_id
            }
        )

        return successful


class GenerateChecksumTask(speedwagon.tasks.Subtask):
    """Checksum generation task."""

    name = "Generate Checksum"

    def __init__(self, package_id: str, source: str) -> None:
        """Create a checksum generation task."""
        super().__init__()
        self._source = source
        self._package_id = package_id

    def task_description(self) -> Optional[str]:
        """Get user readable information about what the subtask is doing."""
        return f"Generating checksums for files in {self._source}"

    def work(self) -> bool:
        """Generate the checksum."""
        checksum_filename = "checksum.md5"
        self.log(f"Generating checksums for {self._package_id}")
        package_builder = package_creater.InplacePackage(self._source)
        package_builder.create_checksum_report(self.subtask_working_dir)

        generated_checksum_file = os.path.join(
            self.subtask_working_dir, checksum_filename)

        dest = os.path.join(self._source, checksum_filename)

        success = os.path.exists(generated_checksum_file)
        assert success

        shutil.move(generated_checksum_file, dest)
        assert os.path.exists(dest)
        self.log(f"Added checksum.md5 to {self._source}")

        self.set_results(
            {
                "source": self._source,
                "checksum": dest,
                "package_id": self._package_id
            }
        )
        return success


class PrepTask(speedwagon.tasks.Subtask):
    """Prep package file structure."""

    name = "Prep"

    def __init__(self, source: str, title_page: str) -> None:
        """Create a new prep task."""
        super().__init__()

        self._source = source
        self._title_page = title_page

    def task_description(self) -> Optional[str]:
        """Get user readable information about what the subtask is doing."""
        return f"Prepping {self._source}"

    def work(self) -> bool:
        """Run the prep task."""
        self.log(f"Prepping on {self._source}")
        package_builder = package_creater.InplacePackage(self._source)
        package_builder.generate_package(destination=self._source,
                                         title_page=self._title_page)
        return True
