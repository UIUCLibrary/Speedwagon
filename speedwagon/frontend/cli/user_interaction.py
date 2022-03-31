import os
import sys
from typing import Dict, Any, Optional, List, Callable

from uiucprescon.packager.packages import collection

import speedwagon
from speedwagon.frontend import interaction


class CLIPackageBrowserWidget(interaction.AbstractPackageBrowser):

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
        packages = []
        for package in self.get_packages(root_dir, image_type):
            files: List[str] = self.get_package_files(package)
            files.sort()

            object_id = package.component_metadata[collection.Metadata.ID]
            print(f"\nSelect title page for {object_id}")
            title_page = self.ask_user_to_select_title_page(files)
            print(f'Using "{title_page}" as the title page')
            package.component_metadata[collection.Metadata.TITLE_PAGE] = \
                title_page
            packages.append(package)

        return {
            "packages": packages
        }

    @staticmethod
    def ask_user_to_select_title_page(
            files: List[str],
            strategy: Optional[
                Callable[[None], int]
            ] = None
    ) -> str:
        while True:
            for i, file_name in enumerate(files):
                print(f"{i + 1}) {file_name}")
            try:
                search_method = strategy or (
                    lambda: int(input("Select title page: "))
                )
                selected_index = search_method()
                if selected_index <= 0 or selected_index > len(files):
                    raise ValueError

                # Index is "one off" so that the user doesn't have to start at
                # 0. Simply subtracting one make picks the correct index again
                return files[selected_index - 1]
            except ValueError:
                print("Not a valid selection, try again", file=sys.stderr)
                continue
            except KeyboardInterrupt as escape_exception:
                raise speedwagon.JobCancelled from escape_exception

    @staticmethod
    def get_package_files(package):
        files: List[str] = []
        for i in package:
            for instance in i.instantiations.values():
                files += [os.path.basename(f) for f in instance.files]
        return files


class CLIFactory(interaction.UserRequestFactory):
    def package_browser(self) -> interaction.AbstractPackageBrowser:
        return CLIPackageBrowserWidget()
