"""Workflow for validating package completeness for HathiTrust."""

import logging
import os
import re
import sys
import typing
from typing import Mapping, Any, Dict, List, Type, Union, Optional, \
    Iterator, Tuple
import itertools

import hathi_validate
from hathi_validate import manifest as validate_manifest
from hathi_validate import report as hathi_reporter
from hathi_validate import result as hathi_result
from hathi_validate import process as validate_process
from hathi_validate import validator

import speedwagon
import speedwagon.tasks.tasks

__all__ = ['CompletenessWorkflow']

from speedwagon import workflow, utils


class CompletenessWorkflow(speedwagon.job.Workflow):
    """Workflow for testing package completeness."""

    name = "Verify HathiTrust Package Completeness"
    description = "This workflow takes as its input a directory of " \
                  "HathiTrust packages. It evaluates each subfolder as a " \
                  "HathiTrust package, and verifies its structural " \
                  "completeness (that it contains correctly named " \
                  "marc.xml, meta.yml, and checksum.md5 files); that its " \
                  "page files (image files, OCR, and optional OCR XML) are " \
                  "formatted as required (named according to HathiTrust’s " \
                  "convention, and an equal number of each); and that its " \
                  "XML, YML, and TIFF or JP2 files are well-formed and " \
                  "valid. (This workflow provides console feedback, but " \
                  "doesn’t write new files as output)."

    def job_options(self) -> List[workflow.AbsOutputOptionDataType]:
        """Request user settings for which checks to be performed."""
        source = workflow.DirectorySelect("Source")

        check_page_data_option = \
            workflow.BooleanSelect("Check for page_data in meta.yml")
        check_page_data_option.value = False

        check_ocr_option = workflow.BooleanSelect("Check ALTO OCR xml files")
        check_ocr_option.value = True

        check_ocr_utf8_option = \
            workflow.BooleanSelect('Check OCR xml files are utf-8')
        check_ocr_utf8_option.value = False

        return [
            source,
            check_page_data_option,
            check_ocr_option,
            check_ocr_utf8_option
        ]

    def discover_task_metadata(self, initial_results: List[
        speedwagon.tasks.tasks.Result],
                               additional_data: Mapping[str, str],
                               **user_args: Union[str, bool]
                               ) -> List[Dict[str, Union[str, bool]]]:
        """Create task metadata based on user settings."""
        jobs = []

        def directory_only_filter(item: 'os.DirEntry[str]') -> bool:
            if not item.is_dir():
                return False

            if not os.access(item.path, os.F_OK):
                return False

            if not os.access(item.path, os.R_OK):
                return False

            return True

        for dir_path in filter(directory_only_filter,
                               os.scandir(user_args['Source'])):
            jobs.append(
                {
                    "package_path":
                        dir_path.path,
                    "check_page_data":
                        user_args["Check for page_data in meta.yml"],
                    "check_ocr_data":
                        user_args["Check ALTO OCR xml files"],
                    "_check_ocr_utf8":
                        user_args['Check OCR xml files are utf-8'],
                }
            )
        return jobs

    def create_new_task(self,
                        task_builder: "speedwagon.tasks.tasks.TaskBuilder",
                        **job_args: Union[str, bool]) -> None:
        """Create validation tasks based on user settings."""
        package_path = \
            os.path.normcase(typing.cast(str, job_args['package_path']))

        request_ocr_validation = \
            typing.cast(bool, job_args['check_ocr_data'])

        request_ocr_utf8_validation = \
            typing.cast(bool, job_args['_check_ocr_utf8'])

        task_builder.add_subtask(
            subtask=PackageNamingConventionTask(package_path))

        task_builder.add_subtask(
            subtask=HathiCheckMissingPackageFilesTask(package_path))
        task_builder.add_subtask(
            subtask=HathiCheckMissingComponentsTask(request_ocr_validation,
                                                    package_path))
        task_builder.add_subtask(
            subtask=ValidateExtraSubdirectoriesTask(package_path))

        task_builder.add_subtask(subtask=ValidateChecksumsTask(package_path))
        task_builder.add_subtask(subtask=ValidateMarcTask(package_path))
        task_builder.add_subtask(subtask=ValidateYMLTask(package_path))

        if request_ocr_validation:
            task_builder.add_subtask(
                subtask=ValidateOCRFilesTask(package_path)
            )

        if request_ocr_utf8_validation:
            task_builder.add_subtask(
                subtask=ValidateOCFilesUTF8Task(package_path))

    @classmethod
    def generate_report(cls, results: List[speedwagon.tasks.tasks.Result],
                        **user_args: Union[str, bool]) -> Optional[str]:
        """Generate a completeness report based on results."""
        report_builder = CompletenessReportBuilder()

        results_sorted = sorted(results, key=lambda x: x.source.__name__)
        _result_grouped: Iterator[
            Tuple[Any, Iterator[speedwagon.tasks.tasks.Result]]
        ] = itertools.groupby(results_sorted, lambda x: x.source)
        report_builder.results = {
            key: [i.data for i in group] for key, group in _result_grouped
        }
        return report_builder.build_report()

    def initial_task(self, task_builder: "speedwagon.tasks.tasks.TaskBuilder",
                     **user_args: str) -> None:
        """Create generate manifest task."""
        new_task = HathiManifestGenerationTask(batch_root=user_args['Source'])
        task_builder.add_subtask(subtask=new_task)

    @staticmethod
    def validate_user_options(*args: str, **kwargs: str) -> bool:
        """Verify user option for source is valid."""
        source = kwargs.get("Source")
        if not source:
            raise ValueError("Source is missing a value")
        if not os.path.exists(source) or not os.path.isdir(source):
            raise ValueError("Invalid source")
        return True


class CompletenessSubTask(speedwagon.tasks.Subtask):
    def work(self) -> bool:
        raise NotImplementedError()


class HathiCheckMissingPackageFilesTask(CompletenessSubTask):
    name = "Check for Missing Package Files"

    def __init__(self, package_path: str) -> None:
        super().__init__()
        self.package_path = package_path

    def task_description(self) -> Optional[str]:
        return f"Checking for missing package files in {self.package_path}"

    def work(self) -> bool:
        errors: List[hathi_result.Result] = []
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with utils.log_config(my_logger, self.log):

            missing_files_errors: List[hathi_result.Result] = \
                validate_process.run_validation(
                    validator.ValidateMissingFiles(path=self.package_path)
                )
            if missing_files_errors:
                for error in missing_files_errors:
                    self.log(error.message)
                    errors.append(error)
            self.set_results(errors)
        return True


class HathiCheckMissingComponentsTask(CompletenessSubTask):
    name = "Checking for missing components"

    def __init__(self, check_ocr: bool, package_path: str) -> None:
        super().__init__()
        self.check_ocr = check_ocr
        self.package_path = package_path

    def task_description(self) -> Optional[str]:
        return f"Checking for missing components in {self.package_path}"

    def work(self) -> bool:
        errors: List[hathi_result.Result] = []
        extensions = [".txt", ".jp2"]
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with utils.log_config(my_logger, self.log):
            if self.check_ocr:
                extensions.append(".xml")
            try:
                missing_files_errors: List[hathi_result.Result] = \
                    validate_process.run_validation(
                        validator.ValidateComponents(
                            self.package_path,
                            "^[0-9]{8}$",
                            *extensions
                        )
                )
            except FileNotFoundError:
                report_builder = hathi_result.SummaryDirector(
                   source=self.package_path
                )

                report_builder.add_error(
                    "No files located with expected file naming scheme in path"
                )
                self.set_results(report_builder.construct())
                return False
            except PermissionError as error_message:
                report_builder = hathi_result.SummaryDirector(
                   source=self.package_path
                )
                report_builder.add_error(
                    f'Permission issues. "{error_message}"'
                )
                self.set_results(report_builder.construct())
                return False

            if not missing_files_errors:
                self.log(
                    f"Found no missing component files in {self.package_path}"
                )

            else:
                for error in missing_files_errors:
                    self.log(error.message)
                    errors.append(error)
            self.set_results(errors)
        return True


class ValidateExtraSubdirectoriesTask(CompletenessSubTask):
    name = "Validating for Extra Subdirectories"

    def __init__(self, package_path: str) -> None:
        super().__init__()
        self.package_path = package_path

    def task_description(self) -> Optional[str]:
        return f"Checking for extra directories in {self.package_path}"

    def work(self) -> bool:
        errors: List[hathi_result.Result] = []
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with utils.log_config(my_logger, self.log):
            try:
                extra_subdirectories_errors: List[hathi_result.Result] = \
                    validate_process.run_validation(
                        validator.ValidateExtraSubdirectories(
                            path=self.package_path
                        )
                )
            except PermissionError as permission_error:
                report_builder = hathi_result.SummaryDirector(
                    source=self.package_path)

                report_builder.add_error(
                    f'Permission issues. "{permission_error}"'
                )
                self.set_results(report_builder.construct())
                return False

            if not extra_subdirectories_errors:
                self.log(
                    f"No extra subdirectories found in {self.package_path}"
                )

            else:
                for error in extra_subdirectories_errors:
                    self.log(error.message)
                    errors.append(error)

            self.set_results(errors)
        return True


class ValidateChecksumsTask(CompletenessSubTask):
    name = "Validate Checksums"

    def __init__(self, package_path: str) -> None:
        super().__init__()
        self.package_path = package_path

    def task_description(self) -> Optional[str]:
        return f"Validating Checksums from {self.package_path}"

    def work(self) -> bool:
        errors: List[hathi_result.Result] = []

        checksum_report = os.path.join(self.package_path, "checksum.md5")
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with utils.log_config(my_logger, self.log):
            report_builder = hathi_result.SummaryDirector(
                source=checksum_report
            )

            try:
                files_to_check = [
                    file_name
                    for _, file_name in validate_process.extracts_checksums(
                        checksum_report
                    )
                ]

                self.log(
                    f"Validating checksums of the {len(files_to_check)} files "
                    f"included in {checksum_report}"
                )

                checksum_report_errors: List[hathi_result.Result] = \
                    validate_process.run_validation(
                        validator.ValidateChecksumReport(
                            self.package_path,
                            checksum_report
                        )
                )
                if not checksum_report_errors:
                    self.log(
                        f"All checksums in {checksum_report} successfully "
                        f"validated"
                    )
                else:
                    for error in checksum_report_errors:
                        errors.append(error)
            except FileNotFoundError as file_missing_error:
                report_builder.add_error(
                    "Unable to validate checksums. "
                    f"Reason: {file_missing_error}"
                )
            except PermissionError as permission_error:
                report_builder = hathi_result.SummaryDirector(
                   source=self.package_path
                )
                report_builder.add_error(
                    f'Permission issues. "{permission_error}"'
                )
                self.set_results(report_builder.construct())
                return False

            for error in report_builder.construct():
                errors.append(error)
            self.set_results(errors)
        return True


class ValidateMarcTask(CompletenessSubTask):
    name = "Validating Marc"

    def __init__(self, package_path: str) -> None:
        super().__init__()
        self.package_path = package_path

    def task_description(self) -> Optional[str]:
        return f"Validating Marc in {self.package_path}"

    def work(self) -> bool:
        marc_file = os.path.join(self.package_path, "marc.xml")
        result_builder = hathi_result.SummaryDirector(source=marc_file)
        errors: List[hathi_result.Result] = []

        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with utils.log_config(my_logger, self.log):
            try:
                if not os.path.exists(marc_file):
                    self.log(f"Skipping \'{marc_file}\' due to file not found")

                else:
                    self.log(f"Validating marc.xml in {self.package_path}")

                    marc_errors: List[hathi_result.Result] = \
                        validate_process.run_validation(
                            validator.ValidateMarc(marc_file)
                        )

                    if not marc_errors:
                        self.log(f"{marc_file} successfully validated")
                    else:
                        for error in marc_errors:
                            self.log(error.message)
                            errors.append(error)
            except FileNotFoundError as error:
                result_builder.add_error(
                    f"Unable to Validate Marc. Reason: {error}"
                )
            except PermissionError as error:
                report_builder = hathi_result.SummaryDirector(
                   source=self.package_path
                )
                report_builder.add_error(f"Permission issues. \"{error}\"")
                self.set_results(report_builder.construct())
                return False

            for error_found in result_builder.construct():
                errors.append(error_found)
            self.set_results(errors)
        return True


class ValidateOCRFilesTask(CompletenessSubTask):
    name = "Validating OCR Files"

    def __init__(self, package_path: str) -> None:
        super().__init__()
        self.package_path = package_path

    def task_description(self) -> Optional[str]:
        return f"Validating OCR Files in {self.package_path}"

    def work(self) -> bool:
        errors: List[hathi_result.Result] = []
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with utils.log_config(my_logger, self.log):
            print("Running ocr Validation")
            try:
                ocr_errors = validate_process.run_validation(
                    validator.ValidateOCRFiles(path=self.package_path)
                )

            except PermissionError as permission_error:
                report_builder = hathi_result.SummaryDirector(
                   source=self.package_path
                )
                report_builder.add_error(
                    f'Permission issues. "{permission_error}"'
                )
                self.set_results(report_builder.construct())
                return False

            except Exception as uncaught_error:
                print(uncaught_error)
                raise

            if ocr_errors:
                self.log(f"No validation errors found in {self.package_path}")

                for error in ocr_errors:
                    self.log(error.message)
                    errors.append(error)
            self.set_results(errors)
        return True


class ValidateYMLTask(CompletenessSubTask):
    name = "Validating YML"

    def __init__(self, package_path: str) -> None:
        super().__init__()
        self.package_path = package_path

    def task_description(self) -> Optional[str]:
        return f"Validating YML in {self.package_path}"

    def work(self) -> bool:
        yml_file = os.path.join(self.package_path, "meta.yml")
        errors: List[hathi_result.Result] = []
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with utils.log_config(my_logger, self.log):
            report_builder = hathi_result.SummaryDirector(source=yml_file)

            try:
                if not os.path.exists(yml_file):
                    self.log(f"Skipping '{yml_file}' due to file not found")

                else:
                    self.log(f"Validating meta.yml in {self.package_path}")

                    meta_yml_errors = validate_process.run_validation(
                        validator.ValidateMetaYML(yaml_file=yml_file,
                                                  path=self.package_path,
                                                  required_page_data=True)
                    )

                    if not meta_yml_errors:
                        self.log(f"{yml_file} successfully validated")
                    else:
                        for error in meta_yml_errors:
                            self.log(error.message)
                            errors.append(error)
            except FileNotFoundError as file_not_found_error:
                report_builder.add_error(
                    f"Unable to validate YAML. Reason: {file_not_found_error}"
                )
            for error in report_builder.construct():
                errors.append(error)
            self.set_results(errors)
        return True


class ValidateOCFilesUTF8Task(CompletenessSubTask):
    name = "Validate OCR Files UTF8 Encoding"

    def __init__(self, package_path: str) -> None:
        super().__init__()
        self.package_path = package_path

    def task_description(self) -> Optional[str]:
        return f"Validate OCR Files have UTF8 Encoding in {self.package_path}"

    def work(self) -> bool:
        def filter_ocr_only(entry: 'os.DirEntry[str]') -> bool:
            if not entry.is_file():
                return False

            name, ext = os.path.splitext(entry.name)

            if ext.lower() != ".xml":
                return False

            if name.lower() == "marc":
                return False

            return True

        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with utils.log_config(my_logger, self.log):
            errors: List[hathi_result.Result] = []

            ocr_file: 'os.DirEntry[str]'
            for ocr_file in filter(filter_ocr_only,
                                   os.scandir(self.package_path)):
                self.log(f"Looking for invalid characters in {ocr_file.path}")

                invalid_ocr_character: List[hathi_result.Result] =\
                    validate_process.run_validation(
                    validator.ValidateUTF8Files(ocr_file.path)
                )

                if invalid_ocr_character:
                    errors += invalid_ocr_character

            self.set_results(errors)
        return True


class HathiManifestGenerationTask(CompletenessSubTask):
    name = 'Hathi Manifest Generation'

    def __init__(self, batch_root: str) -> None:
        super().__init__()
        self.batch_root = batch_root

    def task_description(self) -> Optional[str]:
        return f"Generating HathiTrust Manifest for {self.batch_root}"

    def work(self) -> bool:
        batch_root = self.batch_root
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with utils.log_config(my_logger, self.log):

            batch_manifest_builder = \
                validate_manifest.PackageManifestDirector()

            for package_path in filter(lambda i: i.is_dir(),
                                       os.scandir(batch_root)):

                package_builder = batch_manifest_builder.add_package(
                    package_path.path
                )

                for root, _, files in os.walk(package_path.path):
                    for file_ in files:
                        relative = os.path.relpath(root,
                                                   os.path.abspath(batch_root))

                        package_builder.add_file(os.path.join(relative, file_))
            manifest = batch_manifest_builder.build_manifest()

            manifest_report = \
                validate_manifest.get_report_as_str(manifest, width=70)

            self.set_results(manifest_report)
        return True


class PackageNamingConventionTask(CompletenessSubTask):
    name = "Package Naming Convention"
    FILE_NAMING_CONVENTION_REGEX = \
        "^[0-9]*([m|v|i][0-9]{2,})?(_[1-9])?([m|v|i][0-9])?$"

    def __init__(self, package_path: str) -> None:
        super().__init__()
        self.package_path = package_path

        self._validator = re.compile(
            PackageNamingConventionTask.FILE_NAMING_CONVENTION_REGEX)

    def task_description(self) -> Optional[str]:
        return f"Checking Package Naming Convention for {self.package_path}"

    def work(self) -> bool:
        if not os.path.isdir(self.package_path):
            raise FileNotFoundError(
                f"Unable to locate \"{os.path.abspath(self.package_path)}\"."
            )

        warnings: List[hathi_result.Result] = []
        package_name = os.path.split(self.package_path)[-1]

        if not self._validator.match(package_name):
            warnings.append(self._generate_warning(self.package_path))
        if warnings:
            self.set_results(warnings)
        return True

    def _generate_warning(self, package_path: str) -> hathi_result.Result:
        warning_message = f"{package_path} is an invalid naming scheme"

        self.log(f"Warning: {warning_message}")

        result = hathi_result.Result(
            result_type="PackageNamingConventionTask")

        result.source = self.package_path
        result.message = warning_message
        return result


class CompletenessReportBuilder:

    def __init__(self) -> None:
        super().__init__()
        self.line_length = 70

        self.results: Dict[
            Type['CompletenessSubTask'], List[List[hathi_result.Result]]
        ] = {}

        self._tasks_performed: List[Type[CompletenessSubTask]] = [
            HathiCheckMissingPackageFilesTask,
            HathiCheckMissingComponentsTask,
            ValidateExtraSubdirectoriesTask,
            ValidateMarcTask,
            ValidateYMLTask
        ]

    def generate_error_report(self) -> str:
        error_results: List[hathi_result.Result] = []
        for task in self._tasks_performed:
            error_results += self._get_result(self.results, task)

        return hathi_reporter.get_report_as_str(error_results,
                                                self.line_length)

    @classmethod
    def _get_result(cls,
                    results_grouped: Dict[Type["CompletenessSubTask"],
                                          List[List[hathi_result.Result]]],
                    key: Type["CompletenessSubTask"]
                    ) -> List[hathi_result.Result]:

        results: List[hathi_result.Result] = []

        try:
            for result_group in results_grouped[key]:
                for result in result_group:
                    results.append(result)
        except KeyError as error:
            print(F"KeyError: {error}", file=sys.stderr)
        return results

    def build_report(self) -> str:

        # ############################ Errors ############################
        error_report = self.generate_error_report()

        # ########################### Warnings ###########################
        warning_results: List[hathi_result.Result] = []

        warning_results += self._get_result(
            self.results,
            PackageNamingConventionTask
        )

        warning_report = hathi_reporter.get_report_as_str(
            warning_results,
            self.line_length
        )

        report_lines: List[str] = [
            "",
            "Report:",
        ]
        if HathiManifestGenerationTask in self.results:
            report_lines += [
                typing.cast(str, self.results[HathiManifestGenerationTask][0]),
                ""
            ]

        if error_report:
            report_lines += [
                "",
                "Errors:",
                error_report,
                ""
            ]

        if warning_results:
            report_lines += [
                "",
                "Warnings:",
                warning_report,
                ""
            ]
        return "\n".join(report_lines)
