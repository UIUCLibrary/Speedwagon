import random
import typing
import time

import os

from frames import worker
# from frames.tool import  ZipPackageJob
from frames.tools.abstool import AbsTool
from frames.worker import ProcessJob

import hathizip.process

class ZipPackages(AbsTool):
    name = "Zip packages"
    description = "This tool takes a folder, usually of HathiTrust packages, zips each subfolder, and copies the " \
                " resultant tree to a different location. Input is a root folder, usually for a HathiTrust shipment, " \
                " containing multiple subfolders, each one a HathiTrust digitized item." \
                "\nOutput is a destination location for the newly generated files."

    def __init__(self) -> None:

        super().__init__()

        # input_data = SelectDirectory()
        # input_data.label = "Package root"
        # self.options.append(input_data)

    def new_job(self) -> typing.Type[worker.ProcessJob]:
        return ZipPackageJob

    @staticmethod
    def discover_jobs(source, output, *args, **kwargs) -> typing.List[dict]:
        ZipPackages.validate_args(source, output, args, kwargs)

        job_requests = []
        for dir_ in filter(lambda x: x.is_dir(), os.scandir(source)):
            job_requests.append({"source_path": dir_.path,
                                 "destination_path": output,
                                 }
                                )
        return job_requests

    @staticmethod
    def get_arguments() -> dict:
        return {"source": "",
                "output": ""
                }

    @staticmethod
    def validate_args(source, output, *args, **kwargs):

        if not os.path.exists(source) or not os.path.isdir(source):
            raise ValueError("Invalid source")
        if not os.path.exists(output) or not os.path.isdir(output):
            raise ValueError("Invalid output")




class ZipPackageJob(ProcessJob):

    def process(self, source_path, destination_path, *args, **kwargs):

        self.log("Zipping {}".format(source_path))
        hathizip.process.compress_folder(path=source_path, dst=destination_path)
        self.log("{} successfully zipped to {}".format(source_path, destination_path))

