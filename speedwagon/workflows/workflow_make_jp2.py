"""Workflow for making jp2 files."""

import os
import abc
from typing import List, Any, Optional, Iterable

from uiucprescon import images

import speedwagon
import speedwagon.workflow
from speedwagon import job

__all__ = ['MakeJp2Workflow']


def _filter_tif_only(item: os.DirEntry) -> bool:
    if not item.is_file():
        return False

    _, ext = os.path.splitext(item.name)

    if ext.lower() != ".tif":
        return False

    return True


class AbsProfile(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def locate_source_files(self, root: str) -> Iterable[str]:
        pass

    @property
    @abc.abstractmethod
    def image_factory(self) -> str:
        pass


class DigitalLibraryProfile(AbsProfile):
    image_factory = "Digital Library JPEG 2000"

    def locate_source_files(self, root: str) -> Iterable[str]:
        for root_access in self._find_root_access(root):
            for source_file in filter(_filter_tif_only,
                                      os.scandir(root_access)):

                yield source_file.path

    @staticmethod
    def _find_root_access(path: str) -> Iterable[str]:
        for root, dirs, _ in os.walk(path):
            for _dir in dirs:
                if _dir == "access":
                    yield os.path.join(root, _dir)


class HathiTrustProfile(AbsProfile):
    image_factory = "HathiTrust JPEG 2000"

    def locate_source_files(self, root: str) -> Iterable[str]:

        for root_access in self._find_root_access(root):
            for source_file in filter(
                    _filter_tif_only,
                    os.scandir(root_access)):
                yield source_file.path

    @staticmethod
    def _find_root_access(path: str) -> Iterable[str]:
        for root, dirs, _ in os.walk(path):
            for _dir in dirs:
                if _dir == "access":
                    yield os.path.join(root, _dir)


class ProfileFactory:
    profiles = {
        "HathiTrust":  HathiTrustProfile,
        "Digital Library": DigitalLibraryProfile
    }

    @classmethod
    def create(cls, name: str) -> AbsProfile:
        new_profile = cls.profiles[name]
        return new_profile()

    @classmethod
    def profile_names(cls) -> Iterable[str]:
        return cls.profiles.keys()


class MakeJp2Workflow(job.Workflow):
    """Workflow for creating Jpeg 2000 files from TIFF."""

    name = "Make JP2"
    description = "Makes Jpeg 2000 files from TIFF. Tool converts tiff " \
                  "files in access folder in each directory to an JP2000 " \
                  "files with Kakadu. \n" \
                  "\n" \
                  "For example, the following directory would have " \
                  "\"c:\\package_dirs\" for Input:\n" \
                  "\n" \
                  "| c:\\package_dirs\n"\
                  "|.└── 99423682912205899/\n"\
                  "|....└── access/\n" \
                  "|.......├── 99423682912205899-00000001.tif\n" \
                  "|.......├── 99423682912205899-00000002.tif\n" \
                  "\n" \
                  "    and etc...\n"

    active = True

    def job_options(
            self
    ) -> List[speedwagon.workflow.AbsOutputOptionDataType]:
        """Get user options.

        User options includes:
            * Source folder to use as source
            * Output folder to put new files
            * Image profile for selecting the type of files generated
        """
        profile = speedwagon.workflow.ChoiceSelection("Profile")
        profile.placeholder_text = "Select a profile"
        for profile_name in ProfileFactory.profile_names():
            profile.add_selection(profile_name)

        return [
            speedwagon.workflow.DirectorySelect("Input"),
            speedwagon.workflow.DirectorySelect("Output"),
            profile
        ]

    def discover_task_metadata(self,
                               initial_results: List[Any],
                               additional_data,
                               **user_args: str) -> List[dict]:
        """Generate data needed to create a task.

        Args:
            initial_results:
            additional_data:
            **user_args:

        Returns:
            Returns a list of job dictionaries containing input and output of
                individual files along with their conversion profile.

        """
        jobs = []
        source_root: str = user_args["Input"]
        destination_root: str = user_args["Output"]
        profile_name: str = user_args["Profile"]
        profile_factory = ProfileFactory()
        profile = profile_factory.create(profile_name)
        for source_file in profile.locate_source_files(source_root):

            new_name = \
                f"{os.path.splitext(os.path.basename(source_file))[0]}.jp2"

            rel_path = os.path.dirname(
                os.path.relpath(source_file, source_root))

            created_job = {
                "source_root": os.path.normpath(source_root),
                "source_file": os.path.basename(source_file),
                "relative_location": os.path.normpath(rel_path),
                "destination_root": os.path.normpath(destination_root),
                "new_file_name": new_name,
                "image_factory": profile.image_factory,


            }
            jobs.append(created_job)

        return jobs

    @staticmethod
    def validate_user_options(**user_args: str) -> bool:
        """Make sure that the options the user provided is valid.

        Args:
            **user_args:

        Returns:
            Returns true on valid.

        """
        input_path = user_args["Input"]
        destination_path = user_args["Output"]

        if input_path is None:
            raise ValueError("No input path selected")
        if not os.path.exists(input_path):
            raise ValueError(f"Unable to locate {input_path}.")

        if not os.path.isdir(input_path):
            raise ValueError(f"Input not a valid directory {input_path}")

        if destination_path is None:
            raise ValueError("No output path selected")

        if not os.path.exists(destination_path):
            raise ValueError(f"Unable to locate {destination_path}")

        if not os.path.isdir(destination_path):
            raise ValueError("Output is not a valid directory")
        return True

    def create_new_task(self,
                        task_builder: "speedwagon.tasks.TaskBuilder",
                        **job_args: str) -> None:
        """Add a new task to be accomplished when the workflow is started.

        This creates 2 subtasks.
           * Subtask for creating a destination folder
           * Subtask generating a jp2

        Args:
            task_builder:
            **job_args:

        """
        source_root = job_args['source_root']
        source_file = job_args["source_file"]
        relative_location = job_args["relative_location"]
        destination_root = job_args["destination_root"]
        new_name = job_args["new_file_name"]
        image_factory = job_args["image_factory"]

        source_file = os.path.join(source_root, relative_location, source_file)

        destination_file = os.path.join(destination_root,
                                        relative_location, new_name)

        make_dir = EnsurePathTask(
            os.path.join(destination_root, relative_location)
        )

        convert_task = ConvertFileTask(
            source_file=source_file,
            destination_file=destination_file,
            image_factory_name=image_factory
        )

        task_builder.add_subtask(make_dir)
        task_builder.add_subtask(convert_task)

    @classmethod
    def generate_report(cls,
                        results: List[speedwagon.tasks.Result],
                        **user_args: str
                        ) -> Optional[str]:
        """Generate a text report for the results of the workflow.

        Args:
            results:
            **user_args:

        Returns:
            Returns a text report about the number o files created as a string.

        """
        report_title = "Results:"
        files_generated: List[str] = []
        for res in results:
            files_generated.append(res.data["file_created"])
            print(res)
        files_generated_list = "\n".join(files_generated)
        return f"{report_title}" \
               f"\n" \
               f"\nCreated the following files:" \
               f"\n{files_generated_list}"


class EnsurePathTask(speedwagon.tasks.Subtask):
    name = "Ensure Path"

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path

    def task_description(self) -> Optional[str]:
        return f"Verifying directory {self._path}"

    def work(self) -> bool:
        if not os.path.exists(self._path):
            self.log(f"Creating {self._path}")
            os.makedirs(self._path)
        return True


class ConvertFileTask(speedwagon.tasks.Subtask):
    name = "Convert File"

    def __init__(self, source_file: str, destination_file: str,
                 image_factory_name: str) -> None:

        super().__init__()
        self._source_file = source_file
        self._destination_file = destination_file
        self._image_factory_name = image_factory_name

    def task_description(self) -> Optional[str]:
        return f"Converting {self._source_file}"

    def work(self) -> bool:
        self.log(f"Converting {os.path.basename(self._source_file)} "
                 f"to {os.path.basename(self._destination_file)}")

        images.convert_image(self._source_file,
                             self._destination_file,
                             self._image_factory_name)
        self.log(f"Created {self._destination_file}")
        self.set_results({
            "file_created": self._destination_file,
        })
        return os.path.exists(self._destination_file)
