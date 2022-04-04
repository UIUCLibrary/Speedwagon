"""User interaction when using a QtWidget backend."""
from typing import Dict, Any, Optional
from speedwagon.frontend import interaction
from speedwagon.workflows.title_page_selection import PackageBrowser


class QtWidgetFactory(interaction.UserRequestFactory):
    """Factory for generating Qt Widget."""

    def __init__(self, parent) -> None:
        """Create a new QtWidgetFactory factory."""
        super().__init__()
        self.parent = parent

    def package_browser(self) -> interaction.AbstractPackageBrowser:
        """Generate widget for browsing packages."""
        return QtWidgetPackageBrowserWidget(self.parent)


class QtWidgetPackageBrowserWidget(interaction.AbstractPackageBrowser):
    """QtWidget-based widget for selecting packages title pages."""

    def __init__(self, parent) -> None:
        """Create a new package browser."""
        super().__init__()
        self.parent = parent

    def get_user_response(
            self,
            options: dict,
            pretask_results: list
    ) -> Dict[str, Any]:
        """Generate the dialog for selecting title pages."""
        root_dir = options['input']

        image_type: Optional[interaction.SupportedImagePackageFormats] = {
            "TIFF": interaction.SupportedImagePackageFormats.TIFF,
            'JPEG 2000': interaction.SupportedImagePackageFormats.JP2
        }.get(options['Image File Type'])

        if image_type is None:
            raise KeyError(
                f'Unknown value for '
                f'"Image File Type": {options["Image File Type"]}'
            )

        return {
            "packages": self.get_data_with_dialog_box(root_dir, image_type)

        }

    def get_data_with_dialog_box(self, root_dir, image_type):
        """Open a Qt dialog box for selecting package title pages."""
        browser = PackageBrowser(
            self.get_packages(root_dir, image_type),
            self.parent
        )
        browser.exec()
        return browser.data()
