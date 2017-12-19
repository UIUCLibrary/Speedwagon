import typing

import os

from forseti import worker
from forseti.tools.abstool import AbsTool
from forseti.tools.tool_options import ToolOptionDataType
from forseti.worker import ProcessJob

# TODO: This needs the code from https://github.com/UIUCLibrary/DCCMedusaPackager

class CaptureOneToHathiTiffPackage(AbsTool):
    name = "Convert CaptureOne TIFF to Hathi TIFF package"
    description = "Work in progress!!" \
                  "\n" \
                  "\nInput is a path to a folder of TIFF files all named with a bibID as a prefacing identifier, a " \
                  "final delimiting underscore or dash, and a sequence consisting of padded zeroes and a number." \
                  "\n" \
                  "\nOutput is a directory of folders named by bibID with the prefacing delimiter stripped from each " \
                  "filename."

    @staticmethod
    def discover_jobs(**user_args):
        jobs = []
        jobs.append(user_args['input'])
        # cli.get_packages()
        return jobs

    def new_job(self) -> typing.Type[worker.ProcessJob]:
        return PackageConverter

    @staticmethod
    def get_user_options() -> typing.List[ToolOptionDataType]:
        return [
            ToolOptionDataType(name="input"),
            ToolOptionDataType(name="output"),
        ]

    @staticmethod
    def validate_args(**user_args):
        if not os.path.exists(user_args["input"]) or not os.path.isdir(user_args["input"]):
            raise ValueError("Invalid value in input ")

        if not os.path.exists(user_args["output"]) or not os.path.isdir(user_args["output"]):
            raise ValueError("Invalid value in output ")


class PackageConverter(ProcessJob):

    def process(self, *args, **kwargs):
        pass