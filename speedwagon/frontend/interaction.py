"""Interacting with the user."""
from __future__ import annotations

import abc
import copy
import typing
from abc import ABC
from typing import Dict, Any, List, Optional
import enum
import uiucprescon.packager.packages
from uiucprescon.packager import PackageFactory

if typing.TYPE_CHECKING:
    from uiucprescon.packager.packages import collection


class SupportedImagePackageFormats(enum.Enum):
    """Supported image file formats."""

    TIFF = 0
    JP2 = 1


class AbsUserWidget(abc.ABC):
    """Base class for creating user widgets."""

    @abc.abstractmethod
    def get_user_response(
        self, options: dict, pretask_results: list
    ) -> Dict[str, Any]:
        """Get response from the user."""


class AbstractConfirmFilesystemItemRemoval(AbsUserWidget, ABC):
    """Base class for creating confirming item removal from the filesystem."""

    NO_FILES_LOCATED_MESSAGE = "No files found based on search criteria"


class AbstractPackageBrowser(AbsUserWidget, ABC):
    """Base class for creating package browsers."""

    @abc.abstractmethod
    def get_user_response(
        self, options: dict, pretask_results: list
    ) -> Dict[str, Any]:
        """Get a response from the user."""

    @classmethod
    def get_packages(
        cls, root_dir: str, image_type: SupportedImagePackageFormats
    ) -> List[collection.Package]:
        """Locate packages at a given directory."""
        image_types = {
            SupportedImagePackageFormats.TIFF:
                uiucprescon.packager.packages.HathiTiff(),
            SupportedImagePackageFormats.JP2:
                uiucprescon.packager.packages.HathiJp2()
        }
        package_factory = PackageFactory(image_types[image_type])
        return [
            cls.sort_package(package)
            for package in package_factory.locate_packages(root_dir)
        ]

    @staticmethod
    def image_str_to_enum(value: str) -> SupportedImagePackageFormats:
        """Convert an image string to an enum value."""
        image_type: Optional[SupportedImagePackageFormats] = {
            "TIFF": SupportedImagePackageFormats.TIFF,
            "JPEG 2000": SupportedImagePackageFormats.JP2,
        }.get(value)

        if image_type is None:
            raise KeyError(f"Unknown value for " f'"Image File Type": {value}')
        return image_type

    @staticmethod
    def sort_package(package: collection.Package) -> collection.Package:
        """Sort package by name alphabetically."""
        sorted_package = copy.copy(package)
        item_name = uiucprescon.packager.Metadata.ITEM_NAME
        sorted_package.items = sorted(
            package.items, key=lambda pack: pack.metadata[item_name]
        )
        return sorted_package


class AbstractPackageTitlePageSelection(AbsUserWidget, ABC):
    """Select title page from a package."""


class UserRequestFactory(abc.ABC):
    """Factory for generate user interaction objects."""

    @abc.abstractmethod
    def package_browser(self) -> AbstractPackageBrowser:
        """Select the title page for packages."""

    @abc.abstractmethod
    def confirm_removal(self) -> AbstractConfirmFilesystemItemRemoval:
        """Get the correct type of removal dialog."""

    def package_title_page_selection(
        self,
    ) -> AbstractPackageTitlePageSelection:
        """Get the title page for the packages."""
