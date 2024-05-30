"""Shared checksum tasks."""
import abc
from collections import namedtuple
import hashlib
import os
import typing
from typing import Optional

import speedwagon
from speedwagon.workflows.checksum_shared import ResultsValues

CHUNK_SIZE = 2 ** 20


def calculate_md5_hash(file_path: str) -> str:
    """Calculate the md5 hash value of a file.

    Args:
        file_path: Path to a file

    Returns: Hash value as a string

    """
    if not os.path.isfile(file_path):
        raise ValueError(f"Not a valid file: '{file_path}'")

    md5_hash = hashlib.md5()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(CHUNK_SIZE), b""):
            md5_hash.update(chunk)
    hash_value = md5_hash.hexdigest()
    return hash_value


MakeChecksumTaskResult = typing.TypedDict(
    "MakeChecksumTaskResult",
    {
        "source_filename": str,
        "checksum_hash": str,
        "checksum_file": str
    }
)


class MakeChecksumTask(speedwagon.tasks.Subtask[MakeChecksumTaskResult]):
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
        result: MakeChecksumTaskResult = {
            "source_filename": item_file_name,
            "checksum_hash": calculate_md5_hash(file_to_calculate),
            "checksum_file": report_path_to_save_to,
        }
        self.set_results(result)

        return True


HashValue = namedtuple("HashValue", ("filename", "hash"))


class AbsChecksumBuilder(metaclass=abc.ABCMeta):
    """Abstract base class for generating checksums."""

    def __init__(self) -> None:
        """Create a new builder object."""
        self._files: typing.List[HashValue] = []

    def add_entry(self, filename: str, hash_value: str) -> None:
        """Add Additional file to for a checksum to be calculated.

        Args:
            filename: file name to added to report
            hash_value: hash value of file

        """
        self._files.append(HashValue(filename=filename, hash=hash_value))

    @abc.abstractmethod
    def build(self) -> str:
        """Construct a new report as a string."""


class ChecksumReport(AbsChecksumBuilder):
    """Generate a new Checksum report for Hathi."""

    @staticmethod
    def _format_entry(filename: str, hash_value: str) -> str:
        return f"{hash_value} *{filename}"

    def build(self) -> str:
        """Construct a new report as a string."""
        lines = []
        for entry in sorted(self._files, key=lambda x: x.filename):

            lines.append(self._format_entry(
                filename=entry.filename, hash_value=entry.hash)
            )

        return "{}\n".format("\n".join(lines))


class MakeCheckSumReportTask(speedwagon.tasks.Subtask[str]):
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
        report_builder = ChecksumReport()
        for item in self._checksum_calculations:
            filename = item[ResultsValues.SOURCE_FILE]
            hash_value = item[ResultsValues.SOURCE_HASH]
            report_builder.add_entry(filename, hash_value)
        report: str = report_builder.build()

        with open(self._output_filename, "w", encoding="utf-8") as write_file:
            write_file.write(report)
        self.log(f"Wrote {self._output_filename}")

        return True
