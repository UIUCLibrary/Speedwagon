import os
import typing

from frames.worker import ProcessJob
from frames.tools.abstool import AbsTool
from frames import worker

class VerifyChecksumBatch(AbsTool):
    name = "Verify Checksum Batch"
    description = "Verifies the checksum values"

    def __init__(self) -> None:
        super().__init__()


    def new_job(self) -> typing.Type[worker.ProcessJob]:
        return ChecksumJob

    @staticmethod
    def discover_jobs(Input, output, *args, **kwargs):
        if not os.path.exists(Input) or not os.path.isdir(Input):
            raise ValueError("Input is not a valid path")
        print(Input)
        print(output)
        print(args, kwargs)
        return []
        pass

    @staticmethod
    def get_arguments() -> dict:
        return {"Input": "",
                "output": ""
                }


class ChecksumJob(ProcessJob):
    def process(self, *args):
        self.log("Calculated the checksum of file")
        self.log("comparing checksum to expected value")
        # return ""