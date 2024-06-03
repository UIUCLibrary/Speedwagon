"""Commandline interface for interacting to the user."""
from __future__ import annotations

import copy
import dataclasses
import enum
import typing
from typing import (
    Dict,
    Any,
    Optional,
    List,
    Callable,
    Sequence,
    TypeVar,
    Generic,
    Mapping
)

import speedwagon.exceptions
from speedwagon.frontend import interaction
from speedwagon.frontend.interaction import (
    AbstractConfirmFilesystemItemRemoval,
    AbstractTableEditData,
)


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
        self,
        options: Mapping[str, Any],
        pretask_results: List[speedwagon.tasks.Result]
    ) -> Mapping[str, Any]:
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


T = TypeVar("T")
TableReportFormat = TypeVar("TableReportFormat")


def print_table_rows_no_edits(
    data: List[Sequence[T]],
    _: Optional[str] = None
) -> List[Sequence[T]]:
    """Print every row without editing and of the data."""
    for row in data:
        for column in row:
            print(column)
    return data


class CLIEditTable(AbstractTableEditData, Generic[T, TableReportFormat]):
    """Edit tabular data via a cli."""

    def __init__(
        self,
        enter_data: typing.Callable[
            [
                Mapping[str, object],
                List[speedwagon.tasks.Result]
            ],
            List[Sequence[T]]
        ],
        process_data: typing.Callable[
            [List[Sequence[T]]], TableReportFormat
        ],
        edit_data: Callable[
            [
                List[Sequence[T]],
                Optional[str]
            ],
            List[Sequence[T]]
        ] = print_table_rows_no_edits
    ) -> None:
        """Create a new CLIEditTable object.

        Args:
            enter_data: callback function to get data for table
            process_data: callback function to process the raw data into a
                format used by the consumer
            edit_data: callback function that edits the content of the table
        """
        super().__init__(enter_data, process_data)
        self.edit_strategy = edit_data

    def get_user_response(
        self,
        options: Mapping[str, Any],
        pretask_results: List[speedwagon.tasks.Result]
    ) -> Mapping[str, Any]:
        """Get user response."""
        selections = self.gather_data(options, pretask_results)
        return self.process_data_callback(self.edit_data(selections))

    def edit_data(self, data: List[Sequence[T]]) -> List[Sequence[T]]:
        """Edit data and return replacement."""
        return self.edit_strategy(data, self.title)


class TableInputSelectEditor:
    """Table input select widget editor."""

    @dataclasses.dataclass
    class ValidResponse:
        """Data for valid responses for user input."""

        key_display: str
        description: str
        func: Callable[[], typing.Optional[str]]

    def edit(
        self,
        data: List[Sequence[interaction.DataItem]],
        title: Optional[str]
    ) -> List[Sequence[interaction.DataItem]]:
        """Edit data in for a table."""
        updated_data = []
        self.display_header(title)
        for row in data:
            self.display_row(row)
            updated_data.append(self.select_row_data(row))

        return updated_data

    def display_row(self, row: Sequence[interaction.DataItem]) -> None:
        """Display the content of a row and edit if needed."""
        line_data: List[str] = []
        for column in row:
            line_data.append(f"{column.name}: {column.value}")
        line_text = " | ".join(line_data)
        line_length = (len(line_text) if len(line_text) < 80 else 80)

        # print a nice box
        print(f"\n| {'=' * line_length} | ")
        print(f"| {line_text} | ")
        print(f"| {'-' * line_length} | ")

    def get_selection(self) -> str:
        """Prompt user to input data."""
        return input("Select one of the options: ")

    def select_row_data(
        self,
        row: Sequence[interaction.DataItem]
    ) -> Sequence[interaction.DataItem]:
        """Ask user to choose the right value for the data in a given row."""
        new_row = list(copy.deepcopy(row))

        for column_number, column in enumerate(row):
            if column.editable is False:
                continue
            print(f"   {column.name} = [{column.value}]")
            print("\n")

            possible_user_responses = self._get_possible_responses(
                column.value,
                column.possible_values
            )

            while True:
                for k in sorted(possible_user_responses):
                    v = possible_user_responses[k]
                    print(f"    {v.key_display}: {v.description}")
                response_key = self.get_selection()
                if response_key not in possible_user_responses:
                    valid_responses = list(possible_user_responses.keys())
                    message = f"Invalid response, '{response_key}'. " \
                              f"Valid responses are {valid_responses}"
                    print(message)
                    continue
                break
            response = possible_user_responses[response_key]
            new_value = response.func()
            column.value = new_value
            new_row[column_number] = column
        return tuple(new_row)

    @staticmethod
    def _get_possible_responses(
        starting_value: Optional[str],
        possible_values: List[str]
    ) -> Dict[str, TableInputSelectEditor.ValidResponse]:
        def abort() -> None:
            raise speedwagon.exceptions.JobCancelled()

        def _generate_option(
                key_display: str,
                value: Optional[str]
        ) -> TableInputSelectEditor.ValidResponse:
            return TableInputSelectEditor.ValidResponse(
                key_display=key_display,
                description=f'"{value}"',
                func=lambda: value
            )

        skip_response = _generate_option(
            key_display="Enter",
            value=starting_value
        )
        skip_response.description = "Skip"

        responses: Dict[str, TableInputSelectEditor.ValidResponse] = {
            "q": TableInputSelectEditor.ValidResponse(
                key_display="q",
                description="Quit",
                func=abort
            ),
            "": skip_response
        }

        for i, possible_value in enumerate(possible_values):
            menu_selection = str(i + 1)
            responses[menu_selection] = _generate_option(
                key_display=menu_selection,
                value=possible_value
            )
        return responses

    def display_header(self, title: Optional[str]) -> None:
        """Display header to user if given a title."""
        if title:
            line_length = min(len(title), 80)
            line_sep = "*" * line_length
            banner = "\n".join(
                [
                    f"\n{line_sep}",
                    title,
                    f"\n{line_sep}"
                ]
            )
            print(banner)


class CLIFactory(interaction.UserRequestFactory):
    """Command line interface factory."""

    def __init__(self) -> None:
        """Generate a cli interface factory."""
        super().__init__()
        self.table_editor = TableInputSelectEditor()

    def confirm_removal(self) -> AbstractConfirmFilesystemItemRemoval:
        """Create a new cli confirm object."""
        return CLIConfirmFilesystemItemRemoval()

    def table_data_editor(
        self,
        enter_data: typing.Callable[
            [
                Mapping[str, object],
                List[speedwagon.tasks.Result]
            ],
            List[Sequence[interaction.DataItem]]
        ],
        process_data: Callable[
            [
                List[Sequence[interaction.DataItem]]
            ],
            TableReportFormat
        ]
    ) -> AbstractTableEditData:
        """Create a new cli table edit object.

        Args:
            enter_data: table data retrieval callback function.
            process_data: processing data callback function for final report.

        Returns: Table edit widget

        """

        def edit(
            data: List[Sequence[interaction.DataItem]],
            title: Optional[str]
        ) -> List[Sequence[interaction.DataItem]]:
            return self.table_editor.edit(data, title)

        return CLIEditTable[interaction.DataItem, TableReportFormat](
            enter_data,
            process_data, edit_data=edit
        )
