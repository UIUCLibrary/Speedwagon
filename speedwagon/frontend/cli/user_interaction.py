"""Commandline interface for interacting to the user."""
import enum
import os
import sys
from typing import Dict, Any, Optional, List, Callable

from uiucprescon.packager.packages import collection

import speedwagon.exceptions
from speedwagon.frontend import interaction
from speedwagon.frontend.interaction import (
    AbstractConfirmFilesystemItemRemoval,
)


class CLIPackageBrowserWidget(interaction.AbstractPackageBrowser):
    """Commandline interface for selecting package title pages."""

    def get_user_response(
        self, options: dict, pretask_results: list
    ) -> Dict[str, Any]:
        """Get user response of which is the title page for a package."""
        packages = []
        for package in self.get_packages(
            options["input"],
            self.image_str_to_enum(options["Image File Type"]),
        ):
            files: List[str] = self.get_package_files(package)
            files.sort()

            object_id = package.component_metadata[collection.Metadata.ID]
            print(f"\nSelect title page for {object_id}")
            title_page = self.ask_user_to_select_title_page(files)
            print(f'Using "{title_page}" as the title page')
            package.component_metadata[
                collection.Metadata.TITLE_PAGE
            ] = title_page
            packages.append(package)

        return {"packages": packages}

    @staticmethod
    def ask_user_to_select_title_page(
        files: List[str], strategy: Optional[Callable[[], int]] = None
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
                raise speedwagon.exceptions.JobCancelled from escape_exception

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
    """CLI interface for confirming removal of items on the file system."""

    class Confirm(enum.Enum):
        """Confirm options."""

        NO = 0
        YES = 1
        YES_ALL = 2

    def get_user_response(
        self, options: dict, pretask_results: list
    ) -> Dict[str, Any]:
        """Request user input for deletion."""
        data: List[str] = pretask_results[0].data

        if len(data) > 0:
            print("\nFound the following files/folder to delete:")
            for i, item in enumerate(data):
                print(f"   {i + 1}) {item}")
            print()
            items_to_remove = self.user_resolve_items(data)
        else:
            print(CLIConfirmFilesystemItemRemoval.NO_FILES_LOCATED_MESSAGE)
            items_to_remove = []
        return {"items": items_to_remove}

    @staticmethod
    def user_resolve_items(
        items: List[str],
        confirm_strategy: Optional[
            Callable[[str], "CLIConfirmFilesystemItemRemoval.Confirm"]
        ] = None,
    ) -> List[str]:
        """Go through a list of file names and confirm each file or folder.

        The confirm_strategy asks if the user wants to accept one, accept all,
        or reject one file or folder for removal. The files or folders selected
        for removal are returned from this method.

        Notes:
            If the users selects to accept all to any item, every item is
            returned for removal. This includes any files that were originally
            rejected.

        Args:
            items: List of file or directory names, as strings.
            confirm_strategy:
                callback to request verification the removal of a single item.

        Returns:
            Returns the list of files and directories requested to be removed.

        """
        confirm_strategy = confirm_strategy or user_confirm_removal_stdin

        items_to_remove = []

        for item in items:
            response = confirm_strategy(item)
            if response == CLIConfirmFilesystemItemRemoval.Confirm.YES_ALL:
                return items
            if response == CLIConfirmFilesystemItemRemoval.Confirm.NO:
                continue
            if response == CLIConfirmFilesystemItemRemoval.Confirm.YES:
                items_to_remove.append(item)
                continue
            raise TypeError("Unknown response")
        return items_to_remove


def user_confirm_removal_stdin(
    item: str, stdin_request_strategy: Optional[Callable[[], str]] = None
) -> CLIConfirmFilesystemItemRemoval.Confirm:
    """Confirm with stdin."""
    while True:
        prompt_strategy = stdin_request_strategy or (
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
        """Create a new cli confirm object."""
        return CLIConfirmFilesystemItemRemoval()
