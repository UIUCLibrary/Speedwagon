import os
import typing

from forseti.worker import ProcessJob
from .abstool import AbsTool
from .tool_options import ToolOptionDataType
from forseti import worker
import hathi_validate

from hathi_validate import process


class VerifyChecksumBatch(AbsTool):
    name = "Verify Checksum Batch"
    description = "Verify checksum values in checksum batch file, report errors"

    def __init__(self) -> None:
        super().__init__()

    def new_job(self) -> typing.Type[worker.ProcessJob]:
        return ChecksumJob

    @staticmethod
    def discover_jobs(**user_args):
        jobs = []
        checksum_path = os.path.dirname(user_args["input"])
        for report_md5_hash, filename in hathi_validate.process.extracts_checksums(user_args["input"]):
            new_job = {
                "expected_hash": report_md5_hash,
                "filename": filename,
                "checksum_path": checksum_path
            }
            jobs.append(new_job)
            # )
        return jobs
        pass

    @staticmethod
    def get_user_options() -> typing.List[ToolOptionDataType]:
        return [
            ToolOptionDataType("input")
        ]

    @staticmethod
    def validate_args(**user_args):
        if not os.path.exists(user_args["input"]) or not os.path.splitext(user_args['input'])[1] == ".md5":
            raise ValueError("Invalid user arguments")

    @staticmethod
    def generate_report(*args, **kwargs):
        results = kwargs['results']
        failed_files = list(filter(lambda result: not result['valid'], results))
        if failed_files:
            status = "Failure!"
            stats_message = f"{len(failed_files)} files failed checksum validation."
            failed_files_bullet = [f"* {failure['filename']}" for failure in failed_files]
            failure_list = "\n".join(failed_files_bullet)
        else:
            status = "Success!"

            stats_message = f"All {len(results)} passed checksum validation."

            failure_list = ""
        return f"{status}" \
               f"\n{stats_message}" \
               f"\n{failure_list}"
        # super().generate_report(*args, **kwargs)


class ChecksumJob(ProcessJob):
    def process(self, *args, **kwargs):
        filename = kwargs['filename']
        expected = kwargs['expected_hash']
        full_path = os.path.join(kwargs['checksum_path'], kwargs['filename'])

        self.log("Validating {}".format(filename))
        actual_md5 = process.calculate_md5(full_path)
        result = {
            "filename": filename,
            "path": kwargs['checksum_path'],
        }
        if expected != actual_md5:
            self.log(f"Hash mismatch for {filename}. Expected: {expected}. Actual: {actual_md5}")
            result['valid'] = False
        else:
            result['valid'] = True
        self.result = result
        # self.log("comparing checksum to expected value")
        # return ""
