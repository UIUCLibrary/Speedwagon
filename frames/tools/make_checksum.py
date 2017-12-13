import typing

from frames.worker import ProcessJob
from frames.tools.abstool import AbsTool
from frames import worker

class MakeChecksumBatch(AbsTool):
    name = "Make Checksum Batch"
    description = "Makes a checksums"

    def __init__(self) -> None:
        super().__init__()
        # source = SelectDirectory()
        # source.label = "Source"
        # self.options.append(source)

    def new_job(self) -> typing.Type[worker.ProcessJob]:
        return ChecksumJob

    @staticmethod
    def discover_jobs(*args, **kwargs):
        return []
        pass

    @staticmethod
    def get_arguments() -> dict:
        return {"input": "",
                "output": "",
                }


class ChecksumJob(ProcessJob):
    def process(self, *args):
        self.log("Calculated the checksum of file")
        self.log("Adding checksum hash to file")
