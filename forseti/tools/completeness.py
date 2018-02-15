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
from hathi_validate import process as validate_process
from hathi_validate import validator
from hathi_validate import manifest as validate_manifest
from hathi_validate import report as hathi_reporter
from hathi_validate import result as hathi_result
import hathi_validate


class HathiPackageCompleteness(AbsTool):
    name = "Verify HathiTrust Package Completeness"
    description = "This workflow takes as its input a directory of HathiTrust packages. It evaluates each subfolder " \
                  "as a HathiTrust package, and verifies its structural completeness (that it contains correctly " \
                  "named marc.xml, meta.yml, and checksum.md5 files); that its page files (image files, OCR, and " \
                  "optional OCR XML) are formatted as required (named according to HathiTrust’s convention, and an " \
                  "equal number of each); and that its XML, YML, and TIFF or JP2 files are well-formed and valid. " \
                  "(This workflow provides console feedback, but doesn’t write new files as output)."

    @staticmethod
    def new_job() -> typing.Type[worker.ProcessJob]:
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
                "_check_ocr_utf8": user_args['Check OCR xml files are utf-8'],
            }
            )
        return jobs

    @staticmethod
    def get_user_options() -> typing.List[tool_options.UserOption2]:
        check_page_data_option = tool_options.UserOptionPythonDataType2("Check for page_data in meta.yml", bool)
        check_page_data_option.data = False
        check_ocr_option = tool_options.UserOptionPythonDataType2("Check ALTO OCR xml files", bool)
        check_ocr_utf8_option = tool_options.UserOptionPythonDataType2('Check OCR xml files are utf-8', bool)
        check_ocr_utf8_option.data = False
        check_ocr_option.data = True
        return [
            tool_options.UserOptionCustomDataType("Source", tool_options.FolderData),
            check_page_data_option,
            check_ocr_option,
            check_ocr_utf8_option
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
        user_args = kwargs['user_args']
        batch_root = user_args['Source']
        batch_manifest_builder = validate_manifest.PackageManifestDirector()
        for package_path in filter(lambda i: i.is_dir(), os.scandir(batch_root)):
            package_builder = batch_manifest_builder.add_package(package_path.path)
            for root, dirs, files in os.walk(package_path.path):
                for file_ in files:
                    relative = os.path.relpath(root, os.path.abspath(batch_root))
                    package_builder.add_file(os.path.join(relative, file_))

        manifest_report = validate_manifest.get_report_as_str(batch_manifest_builder.build_manifest(), width=70)

        # Error report
        for result_group in kwargs['results']:
            for result in result_group:
                results.append(result)

        error_report = hathi_reporter.get_report_as_str(results, 70)
        return f"{manifest_report}" \
               f"\n" \
               f"\n{error_report}"


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

            package_path = os.path.normcase(kwargs['package_path'])
            request_ocr_validation = kwargs['check_ocr_data']
            request_ocr_utf8_validation = kwargs['_check_ocr_utf8']
            self.log("Checking the completeness of {}".format(package_path))

            errors = []

            # Look for missing package level files
            errors += self._check_missing_package_files(package_path)

            # Look for missing components
            errors += self._check_missing_components(request_ocr_validation, package_path)

            # Validate extra subdirectories
            self.log("Looking for extra subdirectories in {}".format(package_path))
            errors += self._check_extra_subdirectory(package_path)

            # Validate Checksums
            errors += self._check_checksums(package_path)

            # Validate Marc
            errors += self._check_marc(package_path)

            # Validate YML
            errors += self._check_yaml(package_path)

            # Validate ocr files
            if request_ocr_validation:
                self.log("Validating ocr files in {}".format(package_path))
                errors += self._check_ocr(package_path)

            if request_ocr_utf8_validation:
                self.log("Validating ocr files in {} only have utf-8 characters".format(package_path))
                errors += self._check_ocr_utf8(package_path)

            self.result = errors
            self.log("Package completeness evaluation of {} completed".format(package_path))

    def _check_ocr(self, package_path) -> typing.List[hathi_result.ResultSummary]:
        errors = []
        ocr_errors = validate_process.run_validation(validator.ValidateOCRFiles(path=package_path))
        if ocr_errors:
            self.log("No validation errors found in ".format(package_path))
            # else:
            for error in ocr_errors:
                self.log(error.message)
                errors.append(error)
        return errors

    def _check_yaml(self, package_path) -> typing.List[hathi_result.ResultSummary]:
        yml_file = os.path.join(package_path, "meta.yml")
        errors = []
        report_builder = hathi_result.SummaryDirector(source=yml_file)
        try:
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
        except FileNotFoundError as e:
            report_builder.add_error(report_builder.add_error("Unable to validate YAML. Reason: {}".format(e)))
        for error in report_builder.construct():
            errors.append(error)
        return errors

    def _check_marc(self, package_path) -> typing.List[hathi_result.ResultSummary]:
        marc_file = os.path.join(package_path, "marc.xml")
        result_builder = hathi_result.SummaryDirector(source=marc_file)
        errors = []

        try:
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
        except FileNotFoundError as e:
            result_builder.add_error("Unable to Validate Marc. Reason: {}".format(e))
        for error in result_builder.construct():
            errors.append(error)
        return errors

    def _check_checksums(self, package_path) -> typing.List[hathi_result.ResultSummary]:
        errors = []
        checksum_report = os.path.join(package_path, "checksum.md5")
        report_builder = hathi_result.SummaryDirector(source=checksum_report)
        try:
            files_to_check = []
            for a, file_name in validate_process.extracts_checksums(checksum_report):
                files_to_check.append(file_name)
            self.log(
                "Validating checksums of the {} files included in {}".format(len(files_to_check), checksum_report))

            checksum_report_errors = validate_process.run_validation(
                validator.ValidateChecksumReport(package_path, checksum_report))
            if not checksum_report_errors:
                self.log("All checksums in {} successfully validated".format(checksum_report))
            else:
                for error in checksum_report_errors:
                    errors.append(error)
        except FileNotFoundError as e:
            report_builder.add_error("Unable to validate checksums. Reason: {}".format(e))
        for error in report_builder.construct():
            errors.append(error)
        return errors

    def _check_extra_subdirectory(self, package_path) -> typing.List[hathi_result.ResultSummary]:
        errors = []
        extra_subdirectories_errors = validate_process.run_validation(
            validator.ValidateExtraSubdirectories(path=package_path))
        if not extra_subdirectories_errors:
            self.log("No extra subdirectories found in {}".format(package_path))
        else:
            for error in extra_subdirectories_errors:
                self.log(error.message)
                errors.append(error)

        return errors

    def _check_missing_package_files(self, package_path) -> typing.List[hathi_result.ResultSummary]:
        errors = []
        missing_files_errors = validate_process.run_validation(validator.ValidateMissingFiles(path=package_path))
        if missing_files_errors:
            for error in missing_files_errors:
                self.log(error.message)
                errors.append(error)
        return errors

    def _check_missing_components(self, check_ocr: bool, package_path: str) -> typing.List[hathi_result.ResultSummary]:
        errors = []
        extensions = [".txt", ".jp2"]
        if check_ocr:
            extensions.append(".xml")
        missing_files_errors = validate_process.run_validation(
            validator.ValidateComponents(package_path, "^\d{8}$", *extensions))
        if not missing_files_errors:
            self.log("Found no missing component files in {}".format(package_path))
        else:
            for error in missing_files_errors:
                self.log(error.message)
                errors.append(error)
        return errors

    def _check_ocr_utf8(self, package_path) -> typing.List[hathi_result.ResultSummary]:

        def filter_ocr_only(entry: os.DirEntry):
            if not entry.is_file():
                return False

            name, ext = os.path.splitext(entry.name)

            if ext.lower() != ".xml":
                return False

            if name.lower() == "marc":
                return False

            return True

        def find_non_utf8_characters(file_path: str) -> hathi_result.ResultSummary:
            result_builder = hathi_result.SummaryDirector(source=file_path)
            with open(file_path, "rb") as f:

                for line_num, line in enumerate(f):
                    try:
                        line.decode("utf-8", errors="strict")
                    except UnicodeDecodeError as e:
                        result_builder.add_error("Line {} contains illegal characters. Details: {}".format(line_num + 1, e))
            return result_builder.construct()

        errors: typing.List[hathi_result.ResultSummary] = []

        ocr_file: os.DirEntry
        for ocr_file in filter(filter_ocr_only, os.scandir(package_path)):
            self.log("Looking for invalid characters in {}".format(ocr_file.path))

            invalid_characters = find_non_utf8_characters(ocr_file.path)
            if invalid_characters:
                errors += invalid_characters

        return errors
