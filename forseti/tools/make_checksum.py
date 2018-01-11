import typing

import os

from forseti.worker import ProcessJob
from .abstool import AbsTool
from forseti.tools import tool_options
# from .tool_options import ToolOptionDataType
from forseti import worker
from pyhathiprep import checksum


class MakeChecksumBatch(AbsTool):
    name = "Make Checksum Batch"
    description = "Makes a checksums" \
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
        package_root = user_args['input']
        for root, dirs, files in os.walk(package_root):
            for file_ in files:
                full_path = os.path.join(root, file_)
                relpath = os.path.relpath(full_path, package_root)
                job = {
                    "source_path": package_root,
                    "filename": relpath
                }
                jobs.append(job)
        return jobs
        pass

    @staticmethod
    def validate_args(**user_args):
        input_data = user_args["input"]
        if input_data is None:
            raise ValueError("Missing value in input")

        if not os.path.exists(input_data) or not os.path.isdir(input_data):
            raise ValueError("Invalid user arguments")

    @staticmethod
    def get_user_options() -> typing.List[tool_options.UserOption2]:
        return [
            tool_options.UserOptionCustomDataType("input", tool_options.FolderData),
            # tool_options.UserOptionPythonDataType2("input"),
            # ToolOptionDataType(name="output"),
        ]

    @staticmethod
    def on_completion(*args, **kwargs):
        source_path = kwargs["user_args"]['input']
        report_builder = checksum.HathiChecksumReport()
        for filename, hash_value in [(result['filename'], result['checksum']) for result in kwargs['results']]:
            # print(filename, hash_value)
            report_builder.add_entry(filename, hash_value)
        report = report_builder.build()
        checksum_file = os.path.join(source_path, "checksum.md5")
        print(checksum_file)
        with open(checksum_file, "w", encoding="utf-8") as wf:
            wf.write(report)

    @staticmethod
    def generate_report(*args, **kwargs):
        user_args = kwargs['user_args']
        results = kwargs['results']
        return f"Checksum values for {len(results)} files written to checksum.md5"

    #     super().on_completion(*args, **kwargs)


class ChecksumJob(ProcessJob):
    def process(self, *args, **kwargs):
        source_path = kwargs['source_path']
        source_file = kwargs['filename']
        self.log(f"Calculated the checksum for {source_file}")
        # create_checksum_report("dd")
        self.result = {
            "filename": source_file,
            "checksum": checksum.calculate_md5_hash(os.path.join(source_path, source_file))
        }
