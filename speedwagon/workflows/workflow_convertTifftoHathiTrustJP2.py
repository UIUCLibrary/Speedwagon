import abc
import enum
import os
import shutil
import typing
from contextlib import contextmanager
import itertools
from typing import List, Any

from speedwagon import worker
from speedwagon.tools import options
from speedwagon.job import AbsTool, AbsWorkflow
import pykdu_compress
from py3exiv2bind.core import set_dpi


class UserArgs(enum.Enum):
    INPUT = "Input"
    OUTPUT = "Output"


class ResultValues(enum.Enum):
    VALID = "valid"
    FILENAME = "filename"
    PATH = "path"
    CHECKSUM_REPORT_FILE = "checksum_report_file"


class TaskType(enum.Enum):
    COPY = "copy"
    CONVERT = "convert"


class JobValues(enum.Enum):
    SOURCE_ROOT = "source_root"
    OUTPUT_ROOT = "output_root"
    RELATIVE_PATH_TO_ROOT = "relative_path_to_root"
    SOURCE_FILE = "source_file"
    TASK = "task_type"


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


class ConvertTiffToHathiJp2(AbsTool):
    name = "Convert TIFF to HathiTrust JP2"
    description = "Input is a path to a folder containing subfolders which " \
                  "may contain TIFF files." \
                  "\n" \
                  "\nOutput is a new path where the input folder and its " \
                  "exact structure will be copied, but all TIFF files will " \
                  "be replaced by HathiTrust-compliant JP2 files."

    active = True

    @staticmethod
    def discover_task_metadata(**user_args) -> typing.List[dict]:
        jobs = []
        source_input = user_args[UserArgs.INPUT.value]
        dest = user_args[UserArgs.OUTPUT.value]

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
                    JobValues.SOURCE_ROOT.value: source_input,
                    JobValues.OUTPUT_ROOT.value: dest,
                    JobValues.RELATIVE_PATH_TO_ROOT.value:
                        os.path.relpath(root, source_input),
                    JobValues.SOURCE_FILE.value: file_,
                    JobValues.TASK.value: TaskType.CONVERT.value
                })

            for file_ in other_files:

                jobs.append({
                    JobValues.SOURCE_ROOT.value: source_input,
                    JobValues.OUTPUT_ROOT.value: dest,
                    JobValues.RELATIVE_PATH_TO_ROOT.value:
                        os.path.relpath(root, source_input),
                    JobValues.SOURCE_FILE.value: file_,
                    JobValues.TASK.value: TaskType.COPY.value
                })

        return jobs

    @staticmethod
    def new_job() -> typing.Type[worker.ProcessJobWorker]:
        return PackageImageConverter

    @staticmethod
    def get_user_options() -> typing.List[options.UserOption2]:
        return [
            options.UserOptionCustomDataType(UserArgs.INPUT.value,
                                             options.FolderData),

            options.UserOptionCustomDataType(UserArgs.OUTPUT.value,
                                             options.FolderData),
        ]


class PackageImageConverter(worker.ProcessJobWorker):

    @contextmanager
    def log_config(self, logger):
        gui_logger = worker.GuiLogHandler(self.log)
        try:
            logger.addHandler(gui_logger)
            yield
        finally:
            logger.removeHandler(gui_logger)

    def process(self, *args, **kwargs):
        des_path = os.path.join(
            kwargs[JobValues.OUTPUT_ROOT.value],
            kwargs[JobValues.RELATIVE_PATH_TO_ROOT.value]
        )
        basename, _ = os.path.splitext(kwargs[JobValues.SOURCE_FILE.value])
        task_type = kwargs[JobValues.TASK.value]

        if task_type == TaskType.CONVERT.value:
            process_task = ProcessFile(ConvertFile())
        elif task_type == TaskType.COPY.value:
            process_task = ProcessFile(CopyFile())
        else:
            self.log("Don't know what to do for {}".format(task_type))
            return None

        output_path = os.path.join(
            kwargs[JobValues.OUTPUT_ROOT.value],
            kwargs[JobValues.RELATIVE_PATH_TO_ROOT.value],
            )

        source_file_path = \
            os.path.join(kwargs[JobValues.SOURCE_ROOT.value],
                         kwargs[JobValues.RELATIVE_PATH_TO_ROOT.value],
                         kwargs[JobValues.SOURCE_FILE.value])

        try:
            os.makedirs(des_path)
            self.log("Created {}".format(des_path))
        except FileExistsError:
            pass
        process_task.process(source_file_path, output_path)

        self.log(process_task.status_message())


class ConvertTiffToHathiJp2Workflow(AbsWorkflow):
    name = "0 EXPERIMENTAL " \
           "Convert TIFF to HathiTrust JP2"
    description = "Input is a path to a folder containing subfolders which " \
                  "may contain TIFF files." \
                  "\n" \
                  "\nOutput is a new path where the input folder and its " \
                  "exact structure will be copied, but all TIFF files will " \
                  "be replaced by HathiTrust-compliant JP2 files."

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        return ConvertTiffToHathiJp2.discover_task_metadata(**user_args)

    def user_options(self):
        return ConvertTiffToHathiJp2.get_user_options()
