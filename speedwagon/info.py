"""Info about speedwagon."""
from __future__ import annotations
from typing import Sequence, TypeVar, Callable, Union, TypedDict
import platform
import sys
if sys.version_info >= (3, 10):
    from importlib import metadata
else:
    import importlib_metadata as metadata

__all__ = [
    'SystemInfo',
    'convert_package_metadata_to_string',
    'system_info_to_text_formatter',
    'write_system_info_to_file'
]

_T = TypeVar("_T")


def convert_package_metadata_to_string(
        package_metadata: metadata.PackageMetadata
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
                Callable[[metadata.PackageMetadata], _T],
                Callable[[metadata.PackageMetadata], str]
            ] = convert_package_metadata_to_string
    ) -> Sequence[_T | str]:
        """Get list of installed packages."""
        return [
            formatter(x.metadata) for x in sorted(
                metadata.distributions(),
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


def system_info_to_text_formatter(system_info: SystemInfo) -> str:
    """Produce a simple text format of system info."""
    title = "Installed Python Packages:"
    sections = [
        title,
        *[f"  - {entry}" for entry in system_info.get_installed_packages()]

    ]
    report = "\n".join(sections)
    return f"{report}\n"
