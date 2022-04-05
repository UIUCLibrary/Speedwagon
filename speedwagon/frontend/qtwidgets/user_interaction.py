"""User interaction when using a QtWidget backend."""
import typing
from typing import Dict, Any, Optional, List
from PySide6 import QtWidgets
from uiucprescon.packager.packages import collection
from speedwagon.frontend import interaction
from speedwagon.workflows.title_page_selection import PackageBrowser


class QtWidgetFactory(interaction.UserRequestFactory):
    """Factory for generating Qt Widget."""

    def __init__(self, parent: Optional[QtWidgets.QWidget]) -> None:
        """Create a new QtWidgetFactory factory."""
        super().__init__()
        self.parent = parent

    def package_browser(self) -> interaction.AbstractPackageBrowser:
        """Generate widget for browsing packages."""
        return QtWidgetPackageBrowserWidget(self.parent)


class QtWidgetPackageBrowserWidget(interaction.AbstractPackageBrowser):
    """QtWidget-based widget for selecting packages title pages."""

    def __init__(self, parent: Optional[QtWidgets.QWidget]) -> None:
        """Create a new package browser."""
        super().__init__()
        self.parent = parent

    def get_user_response(
            self,
            options: dict,
            pretask_results: list
    ) -> Dict[str, Any]:
        """Generate the dialog for selecting title pages."""
        return {
            "packages":
                self.get_data_with_dialog_box(
                    options['input'],
                    self.image_str_to_enum(options["Image File Type"])
                )

        }

    def get_data_with_dialog_box(
            self,
            root_dir: str,
            image_type: interaction.SupportedImagePackageFormats,
            dialog_box: typing.Type[PackageBrowser] = PackageBrowser
    ) -> List[collection.Package]:
        """Open a Qt dialog box for selecting package title pages."""
        browser = dialog_box(
            self.get_packages(root_dir, image_type),
            self.parent
        )
        browser.exec()
        return browser.data()
