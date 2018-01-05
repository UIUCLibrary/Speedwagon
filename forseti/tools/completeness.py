import typing

import os

from forseti import worker
from .abstool import AbsTool
# from .tool_options import ToolOptionDataType
from forseti.tools import tool_options
from forseti.worker import ProcessJob
from hathi_validate import process as validate_process


class HathiPackageCompleteness(AbsTool):
    name = "Verify HathiTrust Package Completeness"
    description = "This workflow takes as its input a directory of HathiTrust packages. It evaluates each subfolder " \
                  "as a HathiTrust package, and verifies its structural completeness (that it contains correctly " \
                  "named marc.xml, meta.yml, and checksum.md5 files); that its page files (image files, OCR, and " \
                  "optional OCR XML) are formatted as required (named according to HathiTrust’s convention, and an " \
                  "equal number of each); and that its XML, YML, and TIFF or JP2 files are well-formed and valid. " \
                  "(This workflow provides console feedback, but doesn’t write new files as output)."

    def new_job(self) -> typing.Type[worker.ProcessJob]:
        return HathiPackageCompletenessJob

    @staticmethod
    def discover_jobs(**user_args):
        # HathiPackageCompleteness.validate_args(user_args['source'])
        jobs = []
        for d in os.scandir(user_args['source']):
            jobs.append({"package_path": d.path, "check_ocr": user_args["Check for OCR XML"]})
        return jobs

    @staticmethod
    def get_user_options() -> typing.List[tool_options.UserOption]:
        check_option = tool_options.UserOptionPythonDataType("Check for OCR XML", bool)
        check_option.data = False
        return [
            tool_options.UserOptionPythonDataType("source"),
            check_option,
        ]

    @staticmethod
    def validate_args(source, *args, **kwargs):
        src = source
        if not src:
            raise ValueError("Missing value")
        if not os.path.exists(src) or not os.path.isdir(src):
            raise ValueError("Invalid source")

    @staticmethod
    def generate_report(*args, **kwargs):
        results = []
        for result_group in kwargs['results']:
            for result in result_group:
                results.append(result)
        splitter = "*" * 80
        title = "Validation report"
        summary = "{} issues detected.".format(len(results))
        if results:
            try:
                sorted_results = sorted(results, key=lambda r: r.source)

            except Exception as e:
                print(e)
                raise

            message_lines = []
            for result in sorted_results:
                message_lines.append(str(result))
            report_details = "\n".join(message_lines)
        else:
            report_details = ""

        return "\n" \
               "{}\n" \
               "{}\n" \
               "{}\n" \
               "\n" \
               "{}\n" \
               "\n" \
               "{}\n" \
               "{}\n" \
            .format(splitter, title, splitter, summary, report_details, splitter)
    # @staticmethod
    # def get_user_options() -> typing.List["ToolOptionsModel2"]:
    #     return []

class HathiPackageCompletenessJob(ProcessJob):
    def process(self, **kwargs):
        self.log("Checking the completeness of {}".format(kwargs['package_path']))
        self.result = validate_process.process_directory(kwargs['package_path'], require_page_data=kwargs['check_ocr'])
        for result in self.result:
            self.log(str(result))
        # self.result = (kwargs['package_path'], res)
