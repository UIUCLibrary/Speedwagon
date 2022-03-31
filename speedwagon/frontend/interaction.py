import abc
from typing import Dict, Any
import enum
import uiucprescon.packager.packages
from uiucprescon.packager import PackageFactory


class SupportedImagePackageFormats(enum.Enum):
    TIFF = 0
    JP2 = 1


class AbstractPackageBrowser(abc.ABC):

    @abc.abstractmethod
    def get_user_response(
            self,
            options: dict,
            pretask_results: list
    ) -> Dict[str, Any]:
        pass

    @staticmethod
    def get_packages(root_dir, image_type: SupportedImagePackageFormats):
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

    @abc.abstractmethod
    def package_browser(self) -> AbstractPackageBrowser:
        pass
