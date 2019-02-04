import abc
import itertools
import os
import sys
import typing
from typing import List, Any, Optional

from speedwagon import tasks, reports
from speedwagon.tools import options
from speedwagon.job import AbsWorkflow

import pykdu_compress


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

#


class ConvertTiffPreservationToDLJp2Workflow(AbsWorkflow):
    name = "0 EXPERIMENTAL " \
           "Convert CaptureOne Preservation TIFF to Digital Library Access JP2"
    description = "This tool takes as its input a \"preservation\" folder " \
                  "of TIFF files and as its output creates a sibling folder " \
                  "called \"access\" containing digital-library " \
                  "compliant JP2 files named the same as the TIFFs."
    active = True

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        jobs = []
        source_input = user_args["Input"]

        dest = os.path.abspath(
            os.path.join(source_input,
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
                "source_file": tiff_file.path,
                "output_path": dest,
            })

        return jobs

    def user_options(self):
        return [
            options.UserOptionCustomDataType("Input", options.FolderData)
            ]

    def create_new_task(self, task_builder: tasks.TaskBuilder, **job_args):
        source_file = job_args['source_file']
        dest_path = job_args['output_path']
        new_task = PackageImageConverterTask(
            source_file_path=source_file,
            dest_path=dest_path
        )
        task_builder.add_subtask(new_task)

    @staticmethod
    def validate_user_options(**user_args):
        input_value = user_args["Input"]

        if input_value is None:
            raise ValueError("Input is required")

        if not os.path.exists(input_value):
            raise ValueError("Invalid value in input")

        if not os.path.isdir(input_value):
            raise ValueError("Invalid value in input: Not a directory")

        if not input_value.endswith("preservation"):
            raise ValueError("Invalid value in input: Not a preservation "
                             "directory")

    @classmethod
    @reports.add_report_borders
    def generate_report(cls, results: List[tasks.Result], **user_args) -> \
            Optional[str]:

        failure = False
        dest = None

        failed_results, successful_results = cls._partition_results(results)

        dest_paths = set()
        for result in successful_results:
            new_file = result.data["output_filename"]
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
                [result.data["source_filename"]
                 for result in failed_results]
            )

            report = "Failed!\n" \
                     "The following files failed to convert: \n" \
                     "{}".format(failed_list)
        return report

    @classmethod
    def _partition_results(cls, results):
        def successful(res):
            if not res.data["success"]:
                return False
            return True

        t1, t2 = itertools.tee(results)
        return itertools.filterfalse(successful, t1), filter(successful, t2)


class PackageImageConverterTask(tasks.Subtask):

    def __init__(self, source_file_path, dest_path) -> None:
        super().__init__()
        self._dest_path = dest_path
        self._source_file_path = source_file_path

    def work(self):
        des_path = self._dest_path

        basename, _ = os.path.splitext(self._source_file_path)

        process_task = ProcessFile(ConvertFile())

        try:
            os.makedirs(des_path)
            self.log("Created {}".format(des_path))
        except FileExistsError:
            pass

        try:
            process_task.process(self._source_file_path, des_path)
            success = True
        except ProcessingException as e:
            print(e, file=sys.stderr)
            success = False

        self.set_results(
            {
                "output_filename": process_task.output,
                "source_filename": self._source_file_path,
                "success": success
            }
        )

        self.log(process_task.status_message())
