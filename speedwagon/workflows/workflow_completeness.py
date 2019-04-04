import logging
import os
import re
import sys
import typing

import itertools
from contextlib import contextmanager

import hathi_validate

import speedwagon
from speedwagon.tasks import Subtask
from . import shared_custom_widgets as options
from speedwagon.job import AbsWorkflow
from hathi_validate import manifest as validate_manifest
from hathi_validate import report as hathi_reporter
from hathi_validate import result as hathi_result
from speedwagon.worker import GuiLogHandler
from hathi_validate import process as validate_process
from hathi_validate import validator


class CompletenessWorkflow(AbsWorkflow):
    name = "Verify HathiTrust Package Completeness"
    description = "This workflow takes as its input a directory of " \
                  "HathiTrust packages. It evaluates each subfolder as a " \
                  "HathiTrust package, and verifies its structural " \
                  "completeness (that it contains correctly named marc.xml, " \
                  "meta.yml, and checksum.md5 files); that its page files " \
                  "(image files, OCR, and optional OCR XML) are formatted " \
                  "as required (named according to HathiTrust’s convention, " \
                  "and an equal number of each); and that its XML, YML, and " \
                  "TIFF or JP2 files are well-formed and valid. (This " \
                  "workflow provides console feedback, but doesn’t write " \
                  "new files as output)."

    def user_options(self):
        check_page_data_option = options.UserOptionPythonDataType2(
            "Check for page_data in meta.yml", bool)
        check_page_data_option.data = False
        check_ocr_option = options.UserOptionPythonDataType2(
            "Check ALTO OCR xml files", bool)
        check_ocr_utf8_option = options.UserOptionPythonDataType2(
            'Check OCR xml files are utf-8', bool)
        check_ocr_utf8_option.data = False
        check_ocr_option.data = True
        return [
            options.UserOptionCustomDataType("Source", options.FolderData),
            check_page_data_option,
            check_ocr_option,
            check_ocr_utf8_option
        ]

    def discover_task_metadata(self, initial_results: typing.List[typing.Any],
                               additional_data,
                               **user_args) -> typing.List[dict]:
        jobs = []

        def directory_only_filter(item: os.DirEntry):
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

    def create_new_task(self, task_builder: "speedwagon.tasks.TaskBuilder",
                        **job_args):
        package_path = os.path.normcase(job_args['package_path'])
        request_ocr_validation = job_args['check_ocr_data']
        request_ocr_utf8_validation = job_args['_check_ocr_utf8']

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
    def generate_report(cls, results: typing.List[speedwagon.tasks.Result],
                        **user_args) -> typing.Optional[str]:

        results_sorted = sorted(results, key=lambda x: x.source.__name__)
        _result_grouped = itertools.groupby(results_sorted, lambda x: x.source)
        results_grouped = dict()
        for k, g in _result_grouped:
            results_grouped[k] = [i.data for i in g]

        manifest_report = results_grouped[HathiManifestGenerationTask][0]

        error_results: typing.List[hathi_result.Result] = []

        error_results += cls._get_result(results_grouped,
                                         HathiCheckMissingPackageFilesTask)

        error_results += cls._get_result(results_grouped,
                                         HathiCheckMissingComponentsTask)

        error_results += cls._get_result(results_grouped,
                                         ValidateExtraSubdirectoriesTask)

        error_results += cls._get_result(results_grouped,
                                         ValidateChecksumsTask)

        error_results += cls._get_result(results_grouped,
                                         ValidateMarcTask)

        error_results += cls._get_result(results_grouped,
                                         ValidateYMLTask)
        error_report = hathi_reporter.get_report_as_str(error_results, 70)

        # ########################### Warnings ###########################
        warning_results: typing.List[hathi_result.Result] = []

        warning_results += cls._get_result(results_grouped,
                                           PackageNamingConventionTask)

        warning_report = hathi_reporter.get_report_as_str(warning_results, 70)

        report = f"\n" \
                 f"Report:\n" \
                 f"{manifest_report}\n" \
                 f"\n"

        if error_report:
            report = f"{report}\n" \
                     f"\n" \
                     f"Errors:\n" \
                     f"{error_report}\n"

        if warning_results:
            report = f"{report}\n" \
                     f"\n" \
                     f"Warnings:\n" \
                     f"{warning_report}\n"
        return report

    def initial_task(
            self,
            task_builder: speedwagon.tasks.TaskBuilder,
            **user_args
    ) -> None:

        new_task = HathiManifestGenerationTask(batch_root=user_args['Source'])
        task_builder.add_subtask(subtask=new_task)

    @classmethod
    def _get_result(
            cls,
            results_grouped: typing.Dict[typing.Any, list],
            key
    ) -> typing.List[hathi_result.Result]:

        results: typing.List[hathi_result.Result] = []

        try:
            for result_group in results_grouped[key]:
                for result in result_group:
                    results.append(result)
        except KeyError as e:
            print("KeyError: {}".format(e), file=sys.stderr)
        return results

    @staticmethod
    def validate_user_options(Source, *args, **kwargs):
        src = Source
        if not src:
            raise ValueError("Source is missing a value")
        if not os.path.exists(src) or not os.path.isdir(src):
            raise ValueError("Invalid source")


class CompletenessSubTask(Subtask):
    @contextmanager
    def log_config(self, logger):
        gui_logger = GuiLogHandler(self.log)
        try:
            logger.addHandler(gui_logger)
            yield
        finally:
            logger.removeHandler(gui_logger)


class HathiCheckMissingPackageFilesTask(CompletenessSubTask):

    def __init__(self, package_path):
        super().__init__()
        self.package_path = package_path

    def work(self) -> bool:
        errors: typing.List[hathi_result.Result] = []
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with self.log_config(my_logger):
            missing_files_errors = validate_process.run_validation(
                validator.ValidateMissingFiles(path=self.package_path))
            if missing_files_errors:
                for error in missing_files_errors:
                    self.log(error.message)
                    errors.append(error)
            self.set_results(errors)
        return True


class HathiCheckMissingComponentsTask(CompletenessSubTask):

    def __init__(self, check_ocr, package_path):
        super().__init__()
        self.check_ocr = check_ocr
        self.package_path = package_path

    def work(self) -> bool:
        errors: typing.List[hathi_result.Result] = []
        extensions = [".txt", ".jp2"]
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with self.log_config(my_logger):
            if self.check_ocr:
                extensions.append(".xml")
            try:
                missing_files_errors = validate_process.run_validation(
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
            except PermissionError as e:
                report_builder = hathi_result.SummaryDirector(
                   source=self.package_path
                )
                report_builder.add_error("Permission issues. \"{}\"".format(e))
                self.set_results(report_builder.construct())
                return False

            if not missing_files_errors:
                self.log(
                    "Found no missing component files in {}".format(
                        self.package_path
                    )
                )

            else:
                for error in missing_files_errors:
                    self.log(error.message)
                    errors.append(error)
            self.set_results(errors)
        return True


class ValidateExtraSubdirectoriesTask(CompletenessSubTask):
    def __init__(self, package_path):
        super().__init__()
        self.package_path = package_path

    def work(self) -> bool:
        errors: typing.List[hathi_result.Result] = []
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with self.log_config(my_logger):
            try:
                extra_subdirectories_errors = validate_process.run_validation(
                    validator.ValidateExtraSubdirectories(
                        path=self.package_path)
                )
            except PermissionError as e:
                report_builder = hathi_result.SummaryDirector(
                    source=self.package_path)

                report_builder.add_error("Permission issues. \"{}\"".format(e))
                self.set_results(report_builder.construct())
                return False

            if not extra_subdirectories_errors:
                self.log(
                    "No extra subdirectories found in {}".format(
                        self.package_path
                    )
                )

            else:
                for error in extra_subdirectories_errors:
                    self.log(error.message)
                    errors.append(error)

            self.set_results(errors)
        return True


class ValidateChecksumsTask(CompletenessSubTask):
    def __init__(self, package_path):
        super().__init__()
        self.package_path = package_path

    def work(self) -> bool:
        errors: typing.List[hathi_result.Result] = []

        checksum_report = os.path.join(self.package_path, "checksum.md5")
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with self.log_config(my_logger):
            report_builder = hathi_result.SummaryDirector(
                source=checksum_report
            )

            try:
                files_to_check = []

                for a, file_name in \
                        validate_process.extracts_checksums(checksum_report):
                    files_to_check.append(file_name)

                self.log(
                    "Validating checksums of the {} files "
                    "included in {}".format(
                        len(files_to_check),
                        checksum_report
                    )
                )

                checksum_report_errors = validate_process.run_validation(
                    validator.ValidateChecksumReport(self.package_path,
                                                     checksum_report)
                )
                if not checksum_report_errors:
                    self.log(
                        "All checksums in {} successfully validated".format(
                            checksum_report
                        )
                    )
                else:
                    for error in checksum_report_errors:
                        errors.append(error)
            except FileNotFoundError as e:
                report_builder.add_error(
                    "Unable to validate checksums. Reason: {}".format(e)
                )
            except PermissionError as e:
                report_builder = hathi_result.SummaryDirector(
                   source=self.package_path
                )
                report_builder.add_error("Permission issues. \"{}\"".format(e))
                self.set_results(report_builder.construct())
                return False

            for error in report_builder.construct():
                errors.append(error)
            self.set_results(errors)
        return True


class ValidateMarcTask(CompletenessSubTask):
    def __init__(self, package_path):
        super().__init__()
        self.package_path = package_path

    def work(self) -> bool:
        marc_file = os.path.join(self.package_path, "marc.xml")
        result_builder = hathi_result.SummaryDirector(source=marc_file)
        errors: typing.List[hathi_result.Result] = []

        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with self.log_config(my_logger):
            try:
                if not os.path.exists(marc_file):
                    self.log(
                        "Skipping \'{}\' due to file not found".format(
                            marc_file
                        )
                    )

                else:
                    self.log(
                        "Validating marc.xml in {}".format(self.package_path)
                    )

                    marc_errors = validate_process.run_validation(
                        validator.ValidateMarc(marc_file)
                    )

                    if not marc_errors:
                        self.log("{} successfully validated".format(marc_file))
                    else:
                        for error in marc_errors:
                            self.log(error.message)
                            errors.append(error)
            except FileNotFoundError as e:
                result_builder.add_error(
                    "Unable to Validate Marc. Reason: {}".format(e)
                )
            except PermissionError as e:
                report_builder = hathi_result.SummaryDirector(
                   source=self.package_path
                )
                report_builder.add_error("Permission issues. \"{}\"".format(e))
                self.set_results(report_builder.construct())
                return False

            for error in result_builder.construct():
                errors.append(error)
            self.set_results(errors)
        return True


class ValidateOCRFilesTask(CompletenessSubTask):
    def __init__(self, package_path):
        super().__init__()
        self.package_path = package_path

    def work(self) -> bool:
        errors: typing.List[hathi_result.Result] = []
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with self.log_config(my_logger):
            print("Running ocr Validation")
            try:
                ocr_errors = validate_process.run_validation(
                    validator.ValidateOCRFiles(path=self.package_path)
                )

            except PermissionError as e:
                report_builder = hathi_result.SummaryDirector(
                   source=self.package_path
                )
                report_builder.add_error("Permission issues. \"{}\"".format(e))
                self.set_results(report_builder.construct())
                return False

            except Exception as e:
                print(e)
                raise

            if ocr_errors:
                self.log(
                    "No validation errors found in ".format(self.package_path)
                )

                # else:
                for error in ocr_errors:
                    self.log(error.message)
                    errors.append(error)
            self.set_results(errors)
        return True


class ValidateYMLTask(CompletenessSubTask):
    def __init__(self, package_path):
        super().__init__()
        self.package_path = package_path

    def work(self) -> bool:
        yml_file = os.path.join(self.package_path, "meta.yml")
        errors: typing.List[hathi_result.Result] = []
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with self.log_config(my_logger):
            report_builder = hathi_result.SummaryDirector(source=yml_file)

            try:
                if not os.path.exists(yml_file):
                    self.log(
                        "Skipping \'{}\' due to file not found".format(
                            yml_file
                        )
                    )

                else:
                    self.log(
                        "Validating meta.yml in {}".format(self.package_path)
                    )

                    meta_yml_errors = validate_process.run_validation(
                        validator.ValidateMetaYML(yaml_file=yml_file,
                                                  path=self.package_path,
                                                  required_page_data=True)
                    )

                    if not meta_yml_errors:
                        self.log("{} successfully validated".format(yml_file))
                    else:
                        for error in meta_yml_errors:
                            self.log(error.message)
                            errors.append(error)
                #
            except FileNotFoundError as e:
                report_builder.add_error(
                    report_builder.add_error(
                        "Unable to validate YAML. Reason: {}".format(e)
                    )
                )
            for error in report_builder.construct():
                errors.append(error)
            self.set_results(errors)
        return True


class ValidateOCFilesUTF8Task(CompletenessSubTask):
    def __init__(self, package_path):
        super().__init__()
        self.package_path = package_path

    def work(self) -> bool:
        def filter_ocr_only(entry: os.DirEntry):
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

        with self.log_config(my_logger):
            errors: typing.List[hathi_result.Result] = []

            ocr_file: os.DirEntry
            for ocr_file in filter(filter_ocr_only,
                                   os.scandir(self.package_path)):
                self.log("Looking for invalid characters in {}".format(
                    ocr_file.path)
                )

                invalid_ocr_character = validate_process.run_validation(
                    validator.ValidateUTF8Files(ocr_file.path)
                )

                if invalid_ocr_character:
                    errors += invalid_ocr_character

            self.set_results(errors)
        return True


class HathiManifestGenerationTask(CompletenessSubTask):
    def __init__(self, batch_root):
        super().__init__()
        self.batch_root = batch_root

    def work(self) -> bool:
        batch_root = self.batch_root
        my_logger = logging.getLogger(hathi_validate.__name__)
        my_logger.setLevel(logging.INFO)

        with self.log_config(my_logger):

            batch_manifest_builder = \
                validate_manifest.PackageManifestDirector()

            for package_path in filter(lambda i: i.is_dir(),
                                       os.scandir(batch_root)):

                package_builder = batch_manifest_builder.add_package(
                    package_path.path
                )

                for root, dirs, files in os.walk(package_path.path):
                    for file_ in files:
                        relative = os.path.relpath(root,
                                                   os.path.abspath(batch_root))

                        package_builder.add_file(os.path.join(relative, file_))
            manifest = batch_manifest_builder.build_manifest()

            manifest_report = \
                validate_manifest.get_report_as_str(manifest, width=70)

            self.set_results(manifest_report)
        return True
# TODO Check names so that the match the following regular expression


class PackageNamingConventionTask(CompletenessSubTask):
    FILE_NAMING_CONVENTION_REGEX = \
        "^[0-9]*([m|v|i][0-9]{2,})?(_[1-9])?([m|v|i][0-9])?$"

    def __init__(self, package_path):
        super().__init__()
        self.package_path = package_path

        self._validator = re.compile(
            PackageNamingConventionTask.FILE_NAMING_CONVENTION_REGEX)

    def work(self) -> bool:
        if not os.path.isdir(self.package_path):
            raise FileNotFoundError("Unable to locate \"{}\".".format(
                os.path.abspath(self.package_path)))

        warnings: typing.List[hathi_result.Result] = []
        package_name = os.path.split(self.package_path)[-1]

        if not self._validator.match(package_name):
            warning_message = "{} is an invalid naming scheme".format(
                self.package_path)

            self.log("Warning: {}".format(warning_message))

            result = hathi_result.Result(
                result_type=PackageNamingConventionTask)

            result.source = self.package_path
            result.message = warning_message
            warnings.append(result)

        if warnings:
            self.set_results(warnings)
        # self.set_results
        return True
        # return super().work()
#
