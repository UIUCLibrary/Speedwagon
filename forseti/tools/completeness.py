import typing

import os

from forseti import worker
from .abstool import AbsTool
# from .tool_options import ToolOptionDataType
from forseti.tools import tool_options
from forseti.worker import ProcessJob
from hathi_validate import process as validate_process, validator
from hathi_validate import report as hathi_reporter


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
        for d in os.scandir(user_args['Source']):
            jobs.append({
                "package_path": d.path,
                "check_page_data": user_args["Check for page_data in meta.yml"],
                "check_ocr_data": user_args["Check ALTO OCR xml files"],
            }
            )
        return jobs

    @staticmethod
    def get_user_options() -> typing.List[tool_options.UserOption2]:
        check_page_data_option = tool_options.UserOptionPythonDataType2("Check for page_data in meta.yml", bool)
        check_page_data_option.data = False
        check_ocr_option = tool_options.UserOptionPythonDataType2("Check ALTO OCR xml files", bool)
        check_ocr_option.data = True
        return [
            tool_options.UserOptionCustomDataType("Source", tool_options.FolderData),
            check_page_data_option,
            check_ocr_option
        ]

    @staticmethod
    def validate_args(Source, *args, **kwargs):
        src = Source
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
        # splitter = "*" * 80
        # title = "Validation report"
        # summary = "{} issues detected.".format(len(results))
        # if results:
        #     try:
        #         sorted_results = sorted(results, key=lambda r: r.source)
        #
        #     except Exception as e:
        #         print(e)
        #         raise
        #
        #     message_lines = []
        #     for result in sorted_results:
        #         message_lines.append(str(result))
        #     report_details = "\n".join(message_lines)
        # else:
        #     report_details = ""
        #
        # return "\n" \
        #        "{}\n" \
        #        "{}\n" \
        #        "{}\n" \
        #        "\n" \
        #        "{}\n" \
        #        "\n" \
        #        "{}\n" \
        #        "{}\n" \
        #     .format(splitter, title, splitter, summary, report_details, splitter)
        return hathi_reporter.get_report_as_str(results, 70)
        # re
    # @staticmethod
    # def get_user_options() -> typing.List["ToolOptionsModel2"]:
    #     return []


class HathiPackageCompletenessJob(ProcessJob):
    def process(self, **kwargs):
        package_path = os.path.normcase(kwargs['package_path'])
        check_ocr = kwargs['check_ocr_data']
        self.log("Checking the completeness of {}".format(package_path))
        # self.result = validate_process.process_directory(kwargs['package_path'],
        #                                                  require_page_data=kwargs['check_page_data'])
        # for result in self.result:
        #     self.log(str(result))
            
        # logger.debug("Looking for missing package files in {}".format(pkg))
        errors = []
        missing_files_errors = validate_process.run_validation(validator.ValidateMissingFiles(path=package_path))
        if missing_files_errors:
            for error in missing_files_errors:
                self.log(error.message)
                errors.append(error)

        # Look for missing components
        extensions = [".txt", ".jp2"]
        if check_ocr:
            extensions.append(".xml")
        # s.debug("Looking for missing component files in {}".format(pkg))
        missing_files_errors = validate_process.run_validation(validator.ValidateComponents(package_path, "^\d{8}$", *extensions))
        if not missing_files_errors:
            self.log("Found no missing component files in {}".format(package_path))
        else:
            for error in missing_files_errors:
                self.log(error.message)
                errors.append(error)
        # exit()
        # Validate extra subdirectories
        self.log("Looking for extra subdirectories in {}".format(package_path))
        extra_subdirectories_errors = validate_process.run_validation(validator.ValidateExtraSubdirectories(path=package_path))
        if not extra_subdirectories_errors:
            self.log("No extra subdirectories found in {}".format(package_path))
        else:
            for error in extra_subdirectories_errors:
                self.log(error.message)
                errors.append(error)

        # Validate Checksums
        checksum_report = os.path.join(package_path, "checksum.md5")
        self.log("Validating checksums found in {}".format(checksum_report))
        checksum_report_errors = validate_process.run_validation(validator.ValidateChecksumReport(package_path, checksum_report))
        if not checksum_report_errors:
            self.log("All checksums in {} successfully validated".format(checksum_report))
        else:
            for error in checksum_report_errors:
                errors.append(error)

        # Validate Marc
        marc_file=os.path.join(package_path, "marc.xml")
        if not os.path.exists(marc_file):
             self.log("Skipping \'{}\' due to file not found".format(marc_file))
        else:
            self.log("Validating marc.xml in {}".format(package_path))
            marc_errors = validate_process.run_validation(validator.ValidateMarc(marc_file))
            if not marc_errors:
                self.log("{} successfully validated".format(marc_file))
            else:
                for error in marc_errors:
                    self.log(error.message)
                    errors.append(error)

        # Validate YML
        yml_file = os.path.join(package_path, "meta.yml")
        if not os.path.exists(yml_file):
            self.log("Skipping \'{}\' due to file not found".format(yml_file))
        else:
            self.log("Validating meta.yml in {}".format(package_path))
            meta_yml_errors = validate_process.run_validation(validator.ValidateMetaYML(yaml_file=yml_file, path=package_path, required_page_data=True))
            if not meta_yml_errors:
                self.log("{} successfully validated".format(yml_file))
            else:
                for error in meta_yml_errors:
                    self.log(error.message)
                    errors.append(error)
        #

        # Validate ocr files
        if check_ocr:
            self.log("Validating ocr files in {}".format(package_path))
            ocr_errors = validate_process.run_validation(validator.ValidateOCRFiles(path=package_path))
            if ocr_errors:
                self.log("No validation errors found in ".format(package_path))
            # else:
                for error in ocr_errors:
                    self.log(error.message)
                    errors.append(error)
        self.result = errors
        # self.result = (kwargs['package_path'], res)
