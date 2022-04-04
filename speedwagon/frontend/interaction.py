"""Interacting with the user."""

import abc
from typing import Dict, Any
import enum
import uiucprescon.packager.packages
from uiucprescon.packager import PackageFactory


class SupportedImagePackageFormats(enum.Enum):
    """Supported image file formats."""

    TIFF = 0
    JP2 = 1


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
    def get_packages(root_dir, image_type: SupportedImagePackageFormats):
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


class UserRequestFactory(abc.ABC):
    """Factory for generate user interaction objects."""

    @abc.abstractmethod
    def package_browser(self) -> AbstractPackageBrowser:
        """Select the title page for packages."""
