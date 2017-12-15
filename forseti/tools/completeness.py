import typing

import os

from forseti import worker
from .abstool import AbsTool
from .tool_options import ToolOption
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
    def discover_jobs(source, *args, **kwargs):
        HathiPackageCompleteness.validate_args(source)
        jobs = []
        for d in os.scandir(source):
            jobs.append({"package_path": d.path, "check_ocr": kwargs["Check for OCR XML"]})
        return jobs

    @staticmethod
    def get_user_options() -> typing.List[ToolOption]:
        check_option = ToolOption("Check for OCR XML", bool)
        check_option.data = False
        return [
            ToolOption("source"),
            check_option,
        ]

    @staticmethod
    def validate_args(source, *args, **kwargs):
        if not os.path.exists(source) or not os.path.isdir(source):
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
    def process(self, *args, **kwargs):
        self.log("Checking the completeness of {}".format(kwargs['package_path']))
        # TODO Handle variations when it comes to require_page_data
        self.result = validate_process.process_directory(kwargs['package_path'], require_page_data=kwargs['check_ocr'])
        for result in self.result:
            self.log(str(result))
        # self.result = (kwargs['package_path'], res)
