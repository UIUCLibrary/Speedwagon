import typing

import os

from forseti.tools.tool_options import FileData
from forseti.worker import ProcessJob
from .abstool import AbsTool
# from .tool_options import ToolOptionDataType
from forseti.tools import tool_options
from forseti import worker
# from pyhathiprep import checksum
from hathi_checksum import checksum_report, update_report
from hathi_checksum import utils as hathi_checksum_utils
# import hathi_checksum

class ChecksumFile(FileData):

    @staticmethod
    def filename() -> str:
        return "checksum.md5"

    @staticmethod
    def filter() -> str:
        return "Checksum files (*.md5)"

def find_outdated(results: typing.List[typing.Dict[str, str]]):
    for result in results:
        if result['checksum_actual'] != result['checksum_expected']:
            yield result



class UpdateChecksumBatch(AbsTool):
    name = "Update Checksum Batch"
    description = "Updates the checksum hash in a checksum.md5 file" \
                  "\nInput: path to a root folder"

    def __init__(self) -> None:
        super().__init__()
        # source = SelectDirectory()
        # source.label = "Source"
        # self.options.append(source)

    def new_job(self) -> typing.Type[worker.ProcessJob]:
        return ChecksumJob

    @staticmethod
    def discover_jobs(**user_args):
        jobs = []
        md5_report = user_args['input']
        path = os.path.dirname(os.path.abspath(user_args['input']))
        for report_md5_hash, filename in checksum_report.extracts_checksums(md5_report):
            job = {
                "filename": filename,
                "report_md5_hash": report_md5_hash,
                "location": path
            }
            jobs.append(job)
        return jobs
        pass

    @staticmethod
    def validate_args(**user_args):
        if not os.path.exists(user_args["input"]) or not os.path.isfile(user_args["input"]):
            raise ValueError("Invalid user arguments")
        if os.path.basename(user_args['input']) != "checksum.md5":
            raise ValueError("Selected input is not a checksum.md5 file")

    @staticmethod
    def get_user_options() -> typing.List[tool_options.UserOption]:
        return [
            tool_options.UserOptionCustomDataType("input", ChecksumFile),
            # ToolOptionDataType(name="output"),
        ]

    @staticmethod
    def on_completion(*args, **kwargs):
        source_path = kwargs["user_args"]['input']
        for outdated_result in find_outdated(kwargs['results']):
            update_report.update_hash_value(source_path, outdated_result['filename'], outdated_result['checksum_actual'])

    @staticmethod
    def generate_report(*args, **kwargs):
        user_args = kwargs['user_args']
        results = kwargs['results']
        outdated = list(find_outdated(results))
        outdated_files = [res['filename'] for res in outdated]
        if outdated_files:
            return "Updated md5 entries for [{}] in {}".format(", ".join(outdated_files), user_args['input'])
        else:
            return "No outdated entries found in {}".format(user_args['input'])

    #     super().on_completion(*args, **kwargs)


class ChecksumJob(ProcessJob):
    def process(self, *args, **kwargs):
        source_path = kwargs['location']
        source_file = kwargs['filename']
        self.log(f"Calculating the md5 for {source_file}")
        hash_value = hathi_checksum_utils.calculate_md5(os.path.join(source_path, source_file))
        self.result = {
            "filename": source_file,
            "checksum_actual": hash_value,
            "checksum_expected": kwargs['report_md5_hash']
        }
