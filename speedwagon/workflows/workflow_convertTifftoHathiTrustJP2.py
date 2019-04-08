import abc
import enum
import os
import shutil
import itertools
from typing import List, Any

from speedwagon import tasks
from . import shared_custom_widgets as options
from speedwagon.job import AbsWorkflow
import pykdu_compress
from py3exiv2bind.core import set_dpi


class TaskType(enum.Enum):
    COPY = "copy"
    CONVERT = "convert"


class AbsProcessStrategy(metaclass=abc.ABCMeta):

    def __init__(self) -> None:
        self.status = ""

    @abc.abstractmethod
    def process(self, source_file, destination_path):
        pass


class ProcessFile:
    def __init__(self, process_strategy: AbsProcessStrategy) -> None:
        self._strategy = process_strategy

    def process(self, source_file, destination_path):
        self._strategy.process(source_file, destination_path)

    def status_message(self):
        return self._strategy.status


class ConvertFile(AbsProcessStrategy):

    def process(self, source_file, destination_path):
        basename, ext = os.path.splitext(os.path.basename(source_file))

        output_file_path = os.path.join(destination_path,
                                        basename + ".jp2"
                                        )

        # pykdu_compress.kdu_compress_cli(
        #     "-i {} "
        #     "Clevels=5 "
        #     "Clayers=8 "
        #     "Corder=RLCP "
        #     "Cuse_sop=yes "
        #     "Cuse_eph=yes "
        #     "Cmodes=RESET|RESTART|CAUSAL|ERTERM|SEGMARK "
        #     "-no_weights "
        #     "-slope 42988 "
        #     "-jp2_space sRGB "
        #     "-o {}".format(source_file, output_file_path))

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

        self.status = "Generated {}".format(output_file_path)


class CopyFile(AbsProcessStrategy):

    def process(self, source_file, destination_path):
        filename = os.path.basename(source_file)
        shutil.copyfile(source_file, os.path.join(destination_path, filename))
        self.status = "Copied {} to {}".format(source_file, destination_path)


class ConvertTiffToHathiJp2Workflow(AbsWorkflow):
    name = "Convert TIFF to HathiTrust JP2"
    active = True

    description = "Input is a path to a folder containing subfolders which " \
                  "may contain TIFF files." \
                  "\n" \
                  "\nOutput is a new path where the input folder and its " \
                  "exact structure will be copied, but all TIFF files will " \
                  "be replaced by HathiTrust-compliant JP2 files."

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        jobs = []
        source_input = user_args["Input"]
        dest = user_args["Output"]

        def filter_only_tif_files(filename):
            basename, ext = os.path.splitext(filename)
            if ext.lower() != ".tif":
                return False
            return True

        for root, dirs, files in os.walk(source_input):
            file_iter_1, file_iter_2 = itertools.tee(files)
            tiff_files = filter(filter_only_tif_files, file_iter_1)

            other_files = filter(lambda x: not filter_only_tif_files(x),
                                 file_iter_2)

            for file_ in tiff_files:

                jobs.append({
                    "source_root": source_input,
                    "output_root": dest,
                    "relative_path_to_root":
                        os.path.relpath(root, source_input),
                    "source_file": file_,
                    "task_type": TaskType.CONVERT.value
                })

            for file_ in other_files:

                jobs.append({
                    "source_root": source_input,
                    "output_root": dest,
                    "relative_path_to_root":
                        os.path.relpath(root, source_input),
                    "source_file": file_,
                    "task_type": TaskType.COPY.value
                })

        return jobs

    def user_options(self):
        return [
            options.UserOptionCustomDataType("Input", options.FolderData),
            options.UserOptionCustomDataType("Output", options.FolderData)
        ]

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
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
            raise Exception("Don't know what to do for {}".format(task_type))


class ImageConvertTask(tasks.Subtask):

    def __init__(self, source_file_path, output_path) -> None:
        super().__init__()
        self._source_file_path = source_file_path
        self._output_path = output_path

    def work(self) -> bool:
        try:
            os.makedirs(self._output_path)
            self.log("Created {}".format(self._output_path))
        except FileExistsError:
            pass

        process_task = ProcessFile(ConvertFile())
        process_task.process(self._source_file_path, self._output_path)
        self.log(process_task.status_message())
        return True


class CopyTask(tasks.Subtask):

    def __init__(self, source_file_path, output_path) -> None:
        super().__init__()
        self._source_file_path = source_file_path
        self._output_path = output_path

    def work(self) -> bool:
        try:
            os.makedirs(self._output_path)
            self.log("Created {}".format(self._output_path))
        except FileExistsError:
            pass

        process_task = ProcessFile(CopyFile())
        process_task.process(self._source_file_path, self._output_path)
        self.log(process_task.status_message())
        return True
