import logging
import typing

import os

import sys
from contextlib import contextmanager
from functools import wraps

from forseti import worker
from .abstool import AbsTool
# from .tool_options import ToolOptionDataType
from forseti.tools import tool_options
from forseti.worker import ProcessJob, GuiLogHandler
from hathi_validate import process as validate_process, validator
from hathi_validate import report as hathi_reporter
import hathi_validate


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

        return hathi_reporter.get_report_as_str(results, 70)



class HathiPackageCompletenessJob(ProcessJob):

    def __init__(self):
        super().__init__()

    @contextmanager
    def log_config(self, logger):
        gui_logger = GuiLogHandler(self.log)
        try:
            logger.addHandler(gui_logger)
            yield
        finally:
            logger.removeHandler(gui_logger)

    def process(self, **kwargs):
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)
        with self.log_config(my_logger):

            # logger = logging.getLogger(hathi_validate.__name__)
            # logger.setLevel(logging.INFO)
            # gui_logger = GuiLogHandler(self.log)
            # logger.addHandler(logging.StreamHandler())
            # logger.addHandler(gui_logger)


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
            missing_files_errors = validate_process.run_validation(
                validator.ValidateComponents(package_path, "^\d{8}$", *extensions))
            if not missing_files_errors:
                self.log("Found no missing component files in {}".format(package_path))
            else:
                for error in missing_files_errors:
                    self.log(error.message)
                    errors.append(error)
            # exit()
            # Validate extra subdirectories
            self.log("Looking for extra subdirectories in {}".format(package_path))
            extra_subdirectories_errors = validate_process.run_validation(
                validator.ValidateExtraSubdirectories(path=package_path))
            if not extra_subdirectories_errors:
                self.log("No extra subdirectories found in {}".format(package_path))
            else:
                for error in extra_subdirectories_errors:
                    self.log(error.message)
                    errors.append(error)

            # Validate Checksums
            checksum_report = os.path.join(package_path, "checksum.md5")
            files_to_check = []
            for a, file_name in validate_process.extracts_checksums(checksum_report):
                files_to_check.append(file_name)

            self.log("Validating checksums of the {} files included in {}".format(len(files_to_check), checksum_report))
            checksum_report_errors = validate_process.run_validation(
                validator.ValidateChecksumReport(package_path, checksum_report))
            if not checksum_report_errors:
                self.log("All checksums in {} successfully validated".format(checksum_report))
            else:
                for error in checksum_report_errors:
                    errors.append(error)

            # Validate Marc
            marc_file = os.path.join(package_path, "marc.xml")
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
                meta_yml_errors = validate_process.run_validation(
                    validator.ValidateMetaYML(yaml_file=yml_file, path=package_path, required_page_data=True))
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
            self.log("Package completeness evaluation of {} completed".format(package_path))
        # logger.removeHandler(gui_logger)
        # print("I have {} handlers going out".format(len(logger.handlers)))
        # self.result = (kwargs['package_path'], res)
