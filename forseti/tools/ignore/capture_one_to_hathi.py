import typing

import os

from forseti import worker
from forseti.tools.abstool import AbsTool
# from forseti.tools.tool_options import UserOption
from forseti.tools import tool_options
from forseti.worker import ProcessJob

import MedusaPackager


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
    def discover_jobs(**user_args) -> typing.List[dict]:
        jobs = []
        source_input = user_args['input']
        dest = user_args['output']
        unsorted_data = MedusaPackager.find_package_files(source_input)
        packages = unsorted_data.split_items(MedusaPackager.dash_grouper)
        for package in sorted(packages, key=lambda x: x.package_name):
            data = package.sorted()
            new_package_path = os.path.join(dest, data.package_name)
            jobs.append(
                {
                    "existing_package": data,
                    "new_package_root": new_package_path
                }
            )
            # jobs.append(package.sorted())
            if not os.path.exists(new_package_path):
                MedusaPackager.create_empty_package(new_package_path)
        # cli.get_packages()
        # TODO: Fix this so that it only happen once in another method
        return jobs

    def new_job(self) -> typing.Type[worker.ProcessJob]:
        return PackageConverter

    @staticmethod
    def get_user_options() -> typing.List[tool_options.UserOption2]:
        return [
            tool_options.UserOptionPythonDataType2("input"),
            tool_options.UserOptionPythonDataType2("output"),
        ]

    @staticmethod
    def validate_args(**user_args):
        if not os.path.exists(user_args["input"]) or not os.path.isdir(user_args["input"]):
            raise ValueError("Invalid value in input ")

        if not os.path.exists(user_args["output"]) or not os.path.isdir(user_args["output"]):
            raise ValueError("Invalid value in output ")


class PackageConverter(ProcessJob):

    def process(self, *args, **kwargs):
        existing_package = kwargs['existing_package']
        new_package_root = kwargs['new_package_root']
        # if not os.path.exists()
        print(f"args = {args} kwargs={kwargs}")
