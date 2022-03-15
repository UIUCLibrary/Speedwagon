"""Workflow for converting tiff files to hathitrust jp2s."""

import abc
import enum
import os
import shutil
import itertools
import warnings
from typing import List, Any, Optional

import pykdu_compress
from py3exiv2bind.core import set_dpi
import speedwagon
from speedwagon.job import Workflow

__all__ = ['ConvertTiffToHathiJp2Workflow']


class TaskType(enum.Enum):
    COPY = "copy"
    CONVERT = "convert"


class AbsProcessStrategy(metaclass=abc.ABCMeta):

    def __init__(self) -> None:
        self.status = ""

    @abc.abstractmethod
    def process(self, source_file: str, destination_path: str) -> None:
        pass


class ProcessFile:
    def __init__(self, process_strategy: AbsProcessStrategy) -> None:
        self._strategy = process_strategy

    def process(self, source_file: str, destination_path: str) -> None:
        self._strategy.process(source_file, destination_path)

    def status_message(self):
        return self._strategy.status


class ConvertFile(AbsProcessStrategy):

    def process(self, source_file: str, destination_path: str) -> None:
        basename, _ = os.path.splitext(os.path.basename(source_file))

        output_file_path = os.path.join(destination_path,
                                        basename + ".jp2"
                                        )
        self.generate_jp2(source_file, output_file_path)
        self.status = f"Generated {output_file_path}"

    @staticmethod
    def generate_jp2(source_file: str, output_file_path: str):
        in_args = [
            "Clevels=5",
            "Clayers=8",
            "Corder=RLCP",
            "Cuse_sop=yes",
            "Cuse_eph=yes",
            "Cmodes=RESET|RESTART|CAUSAL|ERTERM|SEGMARK",
            "-no_weights",
            "-slope", "42988",
            "-jp2_space", "sRGB",
        ]
        pykdu_compress.kdu_compress_cli2(
            source_file, output_file_path, in_args=in_args
        )
        set_dpi(output_file_path, x=400, y=400)


class CopyFile(AbsProcessStrategy):

    def process(self, source_file: str, destination_path: str) -> None:
        filename = os.path.basename(source_file)
        shutil.copyfile(source_file, os.path.join(destination_path, filename))
        self.status = f"Copied {source_file} to {destination_path}"


class ConvertTiffToHathiJp2Workflow(Workflow):
    name = "Convert TIFF to HathiTrust JP2"
    active = False
    description = "Input is a path to a folder containing subfolders which " \
                  "may contain TIFF files." \
                  "\n" \
                  "Output is a new path where the input folder and its " \
                  "exact structure will be copied, but all TIFF files will " \
                  "be replaced by HathiTrust-compliant JP2 files."

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        warnings.warn(
            "Pending removal of Convert TIFF to HathiTrust JP2",
            DeprecationWarning
        )

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data,
                               **user_args: str) -> List[dict]:
        jobs = []
        source_input = user_args["Input"]
        dest = user_args["Output"]

        def filter_only_tif_files(filename: str) -> bool:
            _, ext = os.path.splitext(filename)
            if ext.lower() != ".tif":
                return False
            return True

        for root, _, files in os.walk(source_input):
            file_iter_1, file_iter_2 = itertools.tee(files)

            for file_ in filter(filter_only_tif_files, file_iter_1):

                jobs.append({
                    "source_root": source_input,
                    "output_root": dest,
                    "relative_path_to_root":
                        os.path.relpath(root, source_input),
                    "source_file": file_,
                    "task_type": TaskType.CONVERT.value
                })

            for file_ in filter(
                    lambda x: not filter_only_tif_files(x),
                    file_iter_2
            ):

                jobs.append({
                    "source_root": source_input,
                    "output_root": dest,
                    "relative_path_to_root":
                        os.path.relpath(root, source_input),
                    "source_file": file_,
                    "task_type": TaskType.COPY.value
                })

        return jobs

    def create_new_task(self,
                        task_builder: "speedwagon.tasks.TaskBuilder",
                        **job_args: str) -> None:

        output_root = job_args['output_root']
        relative_path_to_root = job_args['relative_path_to_root']
        source_root = job_args['source_root']
        source_file = job_args['source_file']
        task_type = job_args['task_type']

        output_path = os.path.join(output_root, relative_path_to_root)

        source_file_path = os.path.join(
            source_root, relative_path_to_root, source_file)

        if task_type == "convert":
            task_builder.add_subtask(
                ImageConvertTask(source_file_path, output_path))
        elif task_type == "copy":
            task_builder.add_subtask(CopyTask(source_file_path, output_path))

        else:
            raise RuntimeError(f"Don't know what to do for {task_type}")


class ImageConvertTask(speedwagon.tasks.Subtask):
    name = "Convert Images"

    def __init__(self, source_file_path: str, output_path: str) -> None:
        super().__init__()
        self._source_file_path = source_file_path
        self._output_path = output_path

    def task_description(self) -> Optional[str]:
        return f"Converting images in {self._source_file_path}"

    def work(self) -> bool:
        try:
            os.makedirs(self._output_path)
            self.log(f"Created {self._output_path}")
        except FileExistsError:
            pass

        process_task = ProcessFile(ConvertFile())
        process_task.process(self._source_file_path, self._output_path)
        self.log(process_task.status_message())
        return True


class CopyTask(speedwagon.tasks.Subtask):
    name = "Copy Files"

    def __init__(self, source_file_path: str, output_path: str) -> None:
        super().__init__()
        self._source_file_path = source_file_path
        self._output_path = output_path

    def task_description(self) -> Optional[str]:
        return f"Copying files from {self._source_file_path} " \
               f"to {self._output_path}"

    def work(self) -> bool:
        try:
            os.makedirs(self._output_path)
            self.log(f"Created {self._output_path}")
        except FileExistsError:
            pass

        process_task = ProcessFile(CopyFile())
        process_task.process(self._source_file_path, self._output_path)
        self.log(process_task.status_message())
        return True
