"""Commandline interface for interacting to the user."""
import enum
import os
import sys
from typing import Dict, Any, Optional, List, Callable

from uiucprescon.packager.packages import collection

import speedwagon
from speedwagon.frontend import interaction
from speedwagon.frontend.interaction import \
    AbstractConfirmFilesystemItemRemoval


class CLIPackageBrowserWidget(interaction.AbstractPackageBrowser):
    """Commandline interface for selecting package title pages."""

    def get_user_response(
            self,
            options: dict,
            pretask_results: list
    ) -> Dict[str, Any]:
        """Get user response of which is the title page for a package."""
        packages = []
        for package in self.get_packages(
                options['input'],
                self.image_str_to_enum(options['Image File Type'])
        ):
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
        """Request user input on which file represents the title page."""
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
    def get_package_files(package) -> List[str]:
        """Locate files in a package."""
        files: List[str] = []
        for i in package:
            for instance in i.instantiations.values():
                files += [os.path.basename(f) for f in instance.files]
        return files


class CLIConfirmFilesystemItemRemoval(
    interaction.AbstractConfirmFilesystemItemRemoval
):
    class Confirm(enum.Enum):
        NO = 0
        YES = 1
        YES_ALL = 2

    def get_user_response(
            self,
            options: dict,
            pretask_results: list
    ) -> Dict[str, Any]:
        data = pretask_results[0].data
        print("\nFound the following files/folder to delete:")
        for i, item in enumerate(data):
            print(f"   {i+1}) {item}")
        print()
        items_to_remove = []
        for item in data:
            response = self.user_confirm_removal(item)
            if response == CLIConfirmFilesystemItemRemoval.Confirm.NO:
                continue
            if response == CLIConfirmFilesystemItemRemoval.Confirm.YES:
                items_to_remove.append(item)
            elif response == CLIConfirmFilesystemItemRemoval.Confirm.YES_ALL:
                return {
                    "items": data
                }
        return {
            "items": items_to_remove
        }

    def user_confirm_removal(
            self,
            item: str,
            strategy: Optional[
                Callable[[None], str]
            ] = None
    ) -> Confirm:
        while True:
            prompt_strategy = strategy or (
                lambda: input(f'Do you want to remove "{item}"? [Y/N/A]: ')
            )

            valid_responses = {
                "Y": CLIConfirmFilesystemItemRemoval.Confirm.YES,
                "N": CLIConfirmFilesystemItemRemoval.Confirm.NO,
                "A": CLIConfirmFilesystemItemRemoval.Confirm.YES_ALL,
            }
            result = valid_responses.get(prompt_strategy().upper())
            if result is not None:
                return result
            print(
                f"Invalid response. "
                f"Expecting: {list(valid_responses.keys())}\n"
            )


class CLIFactory(interaction.UserRequestFactory):
    """Command line interface  factory."""

    def package_browser(self) -> interaction.AbstractPackageBrowser:
        """Command line interface select title pages of for packages."""
        return CLIPackageBrowserWidget()

    def confirm_removal(self) -> AbstractConfirmFilesystemItemRemoval:
        return CLIConfirmFilesystemItemRemoval()
