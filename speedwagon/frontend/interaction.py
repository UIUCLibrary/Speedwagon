"""Interacting with the user."""

import abc
from typing import Dict, Any, List, Optional
import enum
import uiucprescon.packager.packages
from uiucprescon.packager import PackageFactory
from uiucprescon.packager.packages import collection


class SupportedImagePackageFormats(enum.Enum):
    """Supported image file formats."""

    TIFF = 0
    JP2 = 1


class AbstractConfirmFilesystemItemRemoval(abc.ABC):
    @abc.abstractmethod
    def get_user_response(
            self,
            options: dict,
            pretask_results: list
    ) -> Dict[str, Any]:
        """Get a response from the user."""


class AbstractPackageBrowser(abc.ABC):
    """Base class for creating package browsers."""

    @abc.abstractmethod
    def get_user_response(
            self,
            options: dict,
            pretask_results: list
    ) -> Dict[str, Any]:
        """Get a response from the user."""

    @staticmethod
    def get_packages(
            root_dir: str,
            image_type: SupportedImagePackageFormats
    ) -> List[collection.Package]:
        """Locate packages at a given directory."""
        image_types = {
            SupportedImagePackageFormats.TIFF:
                uiucprescon.packager.packages.HathiTiff(),
            SupportedImagePackageFormats.JP2:
                uiucprescon.packager.packages.HathiJp2()
        }
        package_factory = PackageFactory(
            image_types[image_type]
        )
        return list(package_factory.locate_packages(root_dir))

    @staticmethod
    def image_str_to_enum(value: str) -> SupportedImagePackageFormats:
        """Convert an image string to an enum value."""
        image_type: Optional[SupportedImagePackageFormats] = {
            "TIFF": SupportedImagePackageFormats.TIFF,
            'JPEG 2000': SupportedImagePackageFormats.JP2
        }.get(value)

        if image_type is None:
            raise KeyError(
                f'Unknown value for '
                f'"Image File Type": {value}'
            )
        return image_type


class UserRequestFactory(abc.ABC):
    """Factory for generate user interaction objects."""

    @abc.abstractmethod
    def package_browser(self) -> AbstractPackageBrowser:
        """Select the title page for packages."""

    @abc.abstractmethod
    def confirm_removal(self) -> AbstractConfirmFilesystemItemRemoval:
        """Get the correct type of removal dialog"""
