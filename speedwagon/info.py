"""Info about speedwagon."""
from __future__ import annotations

import importlib.metadata
import json
import platform
import sys
from typing import Sequence, TypeVar, Callable, Union, TypedDict

import speedwagon.exceptions

if sys.version_info < (3, 11):
    from enum import Enum as SpeedwagonEnum
else:
    from enum import StrEnum as SpeedwagonEnum

__all__ = [
    'SystemInfo',
    'convert_package_metadata_to_string',
    'system_info_to_text_formatter',
    'write_system_info_to_file',
    'system_report',
]

_T = TypeVar("_T")


def convert_package_metadata_to_string(
        package_metadata: importlib.metadata.PackageMetadata
) -> str:
    """Generate a string including name and version number of the package."""
    return f"{package_metadata['Name']} {package_metadata['Version']}"


class RuntimeInformation(TypedDict):
    python_version: str


class SystemInfo:
    """System information about the environment running speedwagon."""

    @staticmethod
    def get_installed_packages(
            formatter: Union[
                Callable[[importlib.metadata.PackageMetadata], _T],
                Callable[[importlib.metadata.PackageMetadata], str]
            ] = convert_package_metadata_to_string
    ) -> Sequence[_T | str]:
        """Get list of installed packages."""
        return [
            formatter(x.metadata) for x in sorted(
                importlib.metadata.distributions(),
                key=lambda x: x.metadata["Name"].upper()
            )
        ]

    def get_runtime_information(self) -> RuntimeInformation:
        """Get runtime information about the environment running speedwagon."""
        python_major, python_minor, python_patch_level = (
            platform.python_version_tuple()
        )
        python_version = f"{python_major}.{python_minor}.{python_patch_level}"

        return RuntimeInformation(python_version=python_version)


def write_system_info_to_file(
        system_info: SystemInfo,
        file_name: str,
        formatter: Callable[[SystemInfo], str]
) -> None:
    """Write system data to a file."""
    with open(file_name, "w", encoding="utf-8") as writer:
        writer.write(formatter(system_info))


def system_info_to_json_formatter(system_info: SystemInfo) -> str:
    return json.dumps(
        {
            "installed_packages": system_info.get_installed_packages(),
            "runtime_information": system_info.get_runtime_information(),
        }
    )


def system_info_to_text_formatter(system_info: SystemInfo) -> str:
    """Produce a simple text format of system info."""
    title = "Installed Python Packages:"
    sections = [
        title,
        *[f"  - {entry}" for entry in system_info.get_installed_packages()]

    ]
    report = "\n".join(sections)
    return f"{report}\n"


# This uses "SpeedwagonEnum" so that it can support python 3.10. When Python
# 3.10 support is dropped, set this to StrEnum and remove the conditional
# imports at the top.
class ReportFormats(SpeedwagonEnum):
    PLAIN_TEXT = "plain-text"
    JSON = "json"


REPORT_FORMATTERS = {
    ReportFormats.PLAIN_TEXT: system_info_to_text_formatter,
    ReportFormats.JSON: system_info_to_json_formatter,
}


class InvalidReportType(speedwagon.exceptions.SpeedwagonException):
    """Invalid report type."""


def system_report(
    system_info: SystemInfo, report_format: ReportFormats
) -> str:
    """Produce a report format of system info.

    Args:
        system_info: system info object
        report_format: Serialized report format.

    Returns: String formated report.

    """
    if formatter := REPORT_FORMATTERS.get(report_format):
        return formatter(system_info)
    raise InvalidReportType(f"Unknown report format: {report_format}")
