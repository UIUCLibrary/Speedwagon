import typing

from forseti.worker import ProcessJob
from forseti.tools.abstool import AbsTool
from forseti import worker

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
