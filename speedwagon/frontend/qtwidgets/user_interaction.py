from typing import Dict, Any, Optional
from speedwagon.frontend import interaction
from speedwagon.workflows.title_page_selection import PackageBrowser


class QtWidgetFactory(interaction.UserRequestFactory):

    def __init__(self, parent) -> None:
        super().__init__()
        self.parent = parent

    def package_browser(self) -> interaction.AbstractPackageBrowser:
        return QtWidgetPackageBrowserWidget(self.parent)


class QtWidgetPackageBrowserWidget(interaction.AbstractPackageBrowser):

    def __init__(self, parent) -> None:
        super().__init__()
        self.parent = parent

    def get_user_response(
            self,
            options: dict,
            pretask_results: list
    ) -> Dict[str, Any]:
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
        browser = PackageBrowser(
            self.get_packages(root_dir, image_type),
            self.parent
        )
        browser.exec()
        return browser.data()
