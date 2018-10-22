import abc
import enum
import itertools
import os
import shutil
import sys
import typing
from speedwagon import worker
from speedwagon.tools import options
from speedwagon.job import AbsTool
import pykdu_compress


class UserArgs(enum.Enum):
    INPUT = "Input"


class ResultValues(enum.Enum):
    OUTPUT_FILENAME = "output_filename"
    SOURCE_FILENAME = "source_filename"
    SUCCESS = "success"


class JobValues(enum.Enum):
    SOURCE_FILE = "source_file"
    OUTPUT_PATH = "output_path"


class AbsProcessStrategy(metaclass=abc.ABCMeta):

    def __init__(self) -> None:
        self.output = None
        self.status = None

    @abc.abstractmethod
    def process(self, source_file, destination_path):
        pass


class ProcessFile:
    def __init__(self, process_strategy: AbsProcessStrategy) -> None:
        self._strategy = process_strategy

    def process(self, source_file, destination_path):
        self._strategy.process(source_file, destination_path)

    def status_message(self) -> typing.Optional[str]:
        return self._strategy.status

    @property
    def output(self) -> typing.Optional[str]:
        return self._strategy.output


class ProcessingException(Exception):
    pass


class ConvertFile(AbsProcessStrategy):

    def process(self, source_file, destination_path):
        basename, ext = os.path.splitext(os.path.basename(source_file))

        output_file_path = os.path.join(destination_path,
                                        basename + ".jp2"
                                        )

        # rc = pykdu_compress.kdu_compress_cli(
        #     "-i {} " "-o {}".format(source_file, output_file_path))

        rc = pykdu_compress.kdu_compress_cli2(
            infile=source_file, outfile=output_file_path)

        if rc != 0:
            raise ProcessingException("kdu_compress_cli returned "
                                      "nonzero value: {}.".format(rc))
        self.output = output_file_path
        self.status = "Generated {}".format(output_file_path)


def partition(pred, iterable):
    t1, t2 = itertools.tee(iterable)
    return itertools.filterfalse(pred, t1), filter(pred, t2)


class CopyFile(AbsProcessStrategy):

    def process(self, source_file, destination_path):
        filename = os.path.basename(source_file)
        shutil.copyfile(source_file, os.path.join(destination_path, filename))
        self.status = "Copied {} to {}".format(source_file, destination_path)


class ConvertTiffPreservationToDLJp2(AbsTool):
    name = "Convert CaptureOne Preservation TIFF to Digital Library Access JP2"
    description = "This tool takes as its input a \"preservation\" folder " \
                  "of TIFF files and as its output creates a sibling folder " \
                  "called \"access\" containing digital-library " \
                  "compliant JP2 files named the same as the TIFFs."

    active = True

    @staticmethod
    def discover_task_metadata(**user_args) -> typing.List[dict]:
        jobs = []
        source_input = user_args[UserArgs.INPUT.value]

        dest = os.path.abspath(
            os.path.join(user_args[UserArgs.INPUT.value],
                         "..",
                         "access")
        )

        def filter_only_tif_files(item: os.DirEntry):
            if not item.is_file():
                return False

            basename, ext = os.path.splitext(item.name)
            if ext.lower() != ".tif":
                return False

            return True

        for tiff_file in \
                filter(filter_only_tif_files, os.scandir(source_input)):

                jobs.append({
                    JobValues.SOURCE_FILE.value: tiff_file.path,
                    JobValues.OUTPUT_PATH.value: dest,
                })

        return jobs

    @staticmethod
    def generate_report(results, user_args):
        failure = False
        dest = None

        def successful(result):
            if not result[ResultValues.SUCCESS.value]:
                return False
            return True

        failed_results, successful_results = partition(successful, results)

        dest_paths = set()
        for result in successful_results:
            new_file = result[ResultValues.OUTPUT_FILENAME.value]
            dest_paths.add(os.path.dirname(new_file))

        if len(dest_paths) == 1:
            dest = dest_paths.pop()
        else:
            failure = True

        if not failure:
            report = "Success! [{}] JP2 files written to \"{}\" folder".format(
                len(results), dest)
        else:
            failed_list = "* \n".join(
                [result[ResultValues.SOURCE_FILENAME.value]
                 for result in failed_results]
            )

            report = "Failed!\n" \
                     "The following files failed to convert: \n" \
                     "{}".format(failed_list)
        return report

    @staticmethod
    def new_job() -> typing.Type[worker.ProcessJobWorker]:
        return PackageImageConverter

    @staticmethod
    def get_user_options() -> typing.List[options.UserOption2]:
        return [
            options.UserOptionCustomDataType(UserArgs.INPUT.value,
                                             options.FolderData)
        ]

    @staticmethod
    def validate_user_options(**user_args):
        input_value = user_args[UserArgs.INPUT.value]

        if input_value is None:
            raise ValueError("Input is required")

        if not os.path.exists(input_value):
            raise ValueError("Invalid value in input")

        if not os.path.isdir(input_value):
            raise ValueError("Invalid value in input: Not a directory")

        if not input_value.endswith("preservation"):
            raise ValueError("Invalid value in input: Not a preservation "
                             "directory")


class PackageImageConverter(worker.ProcessJobWorker):

    def process(self, *args, **kwargs):
        des_path = kwargs[JobValues.OUTPUT_PATH.value]

        basename, _ = os.path.splitext(kwargs[JobValues.SOURCE_FILE.value])
        source_file_path = kwargs[JobValues.SOURCE_FILE.value]

        process_task = ProcessFile(ConvertFile())

        try:
            os.makedirs(des_path)
            self.log("Created {}".format(des_path))
        except FileExistsError:
            pass

        try:
            process_task.process(source_file_path, des_path)
            success = True
        except ProcessingException as e:
            print(e, file=sys.stderr)
            success = False

        self.result = {
            ResultValues.OUTPUT_FILENAME.value: process_task.output,
            ResultValues.SOURCE_FILENAME.value: source_file_path,
            ResultValues.SUCCESS.value: success
        }

        self.log(process_task.status_message())
