"""Shared checksum tasks."""
import enum
import os
import typing
from typing import Optional

from pyhathiprep import checksum
from uiucprescon import imagevalidate

import speedwagon
from speedwagon.workflows.checksum_shared import ResultsValues


class MakeChecksumTask(speedwagon.tasks.Subtask):
    """Create a make checksum task."""

    name = "Create Checksum"

    def __init__(
        self, source_path: str, filename: str, checksum_report: str
    ) -> None:
        """Create a make checksum task."""
        super().__init__()
        self._source_path = source_path
        self._filename = filename
        self._checksum_report = checksum_report

    def task_description(self) -> Optional[str]:
        """Get user readable information about what the subtask is doing."""
        return f"Calculating checksum for {self._filename}"

    def work(self) -> bool:
        """Calculate file checksum."""
        item_path = self._source_path
        item_file_name = self._filename
        report_path_to_save_to = self._checksum_report
        self.log(f"Calculated the checksum for {item_file_name}")

        file_to_calculate = os.path.join(item_path, item_file_name)
        result = {
            ResultsValues.SOURCE_FILE: item_file_name,
            ResultsValues.SOURCE_HASH: checksum.calculate_md5_hash(
                file_to_calculate
            ),
            ResultsValues.CHECKSUM_FILE: report_path_to_save_to,
        }
        self.set_results(result)

        return True


class MakeCheckSumReportTask(speedwagon.tasks.Subtask):
    """Generate a checksum report.

    This normally an .md5 file.
    """

    name = "Checksum Report Creation"

    def __init__(
        self,
        output_filename: str,
        checksum_calculations: typing.Iterable[
            typing.Mapping[ResultsValues, str]
        ],
    ) -> None:
        """Create a checksum report task."""
        super().__init__()
        self._output_filename = output_filename
        self._checksum_calculations = checksum_calculations

    def task_description(self) -> Optional[str]:
        """Get user readable information about what the subtask is doing."""
        return f"Writing checksum report: {self._output_filename}"

    def work(self) -> bool:
        """Generate the report file."""
        report_builder = checksum.HathiChecksumReport()
        for item in self._checksum_calculations:
            filename = item[ResultsValues.SOURCE_FILE]
            hash_value = item[ResultsValues.SOURCE_HASH]
            report_builder.add_entry(filename, hash_value)
        report: str = report_builder.build()

        with open(self._output_filename, "w", encoding="utf-8") as write_file:
            write_file.write(report)
        self.log(f"Wrote {self._output_filename}")

        return True


class ValidateImageMetadataTask(speedwagon.tasks.Subtask):
    """Validate the metadata of a image file."""

    name = "Validate Image Metadata"

    class ResultValues(enum.Enum):
        """Result keys used in validation results."""

        VALID = "valid"
        FILENAME = "filename"
        REPORT = "report"

    def __init__(self, filename: str, profile_name: str) -> None:
        """Create an image validation subtask.

        Args:
            filename: path to file
            profile_name: Name of the validation profile to use.
        """
        super().__init__()
        self._filename = filename
        self._profile = typing.cast(
            imagevalidate.profiles.AbsProfile,
            imagevalidate.get_profile(profile_name),
        )

    def task_description(self) -> Optional[str]:
        """Get user readable information about what the subtask is doing."""
        return f"Validating image metadata for {self._filename}"

    def work(self) -> bool:
        """Validate file."""
        self.log(f"Validating {self._filename}")

        profile_validator = imagevalidate.Profile(self._profile)

        try:
            report = profile_validator.validate(self._filename)
            is_valid = report.valid
            report_text = "\n* ".join(report.issues())
        except RuntimeError as error:
            is_valid = False
            report_text = str(error)
        self.log(f"Validating {self._filename} -- {is_valid}")

        result = {
            ValidateImageMetadataTask.ResultValues.FILENAME: self._filename,
            ValidateImageMetadataTask.ResultValues.VALID: is_valid,
            ValidateImageMetadataTask.ResultValues.REPORT: f"* {report_text}",
        }

        self.set_results(result)
        return True
