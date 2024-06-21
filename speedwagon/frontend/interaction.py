"""Interacting with the user."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
import typing
from abc import ABC
from typing import (
    List,
    Optional,
    TypeVar,
    Generic,
    Callable,
    Sequence,
    Any,
    Mapping, TYPE_CHECKING
)
import enum
if TYPE_CHECKING:
    import speedwagon.tasks

T = TypeVar('T')


class SupportedImagePackageFormats(enum.Enum):
    """Supported image file formats."""

    TIFF = 0
    JP2 = 1


class AbsUserWidget(abc.ABC):
    """Base class for creating user widgets."""

    @abc.abstractmethod
    def get_user_response(
        self,
        options: Mapping[str, Any],
        pretask_results: List[speedwagon.tasks.Result[Any]]
    ) -> Mapping[str, Any]:
        """Get response from the user."""


class AbstractConfirmFilesystemItemRemoval(AbsUserWidget, ABC):
    """Base class for creating confirming item removal from the filesystem."""

    NO_FILES_LOCATED_MESSAGE = "No files found based on search criteria"


@dataclass
class DataItem:
    """Data item with optional values."""

    name: str
    value: Optional[str] = None
    editable: bool = False
    possible_values: List[str] = field(default_factory=list)


TableReportFormat = TypeVar('TableReportFormat')


class AbstractTableEditData(AbsUserWidget, ABC, Generic[T, TableReportFormat]):
    """Base class for generating table data."""

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
            [
                List[Sequence[T]]
            ],
            TableReportFormat
        ]
    ) -> None:
        """Initialize AbstractTableEditData base class variable."""
        super().__init__()
        self.title = ""
        self.column_names: List[str] = []
        self._data_gathering_callback = enter_data
        self.process_data_callback = process_data

    def gather_data(
        self,
        options: Mapping[str, object],
        pretask_results: List[speedwagon.tasks.Result]
    ) -> List[Sequence[T]]:
        """Get data from user using the method provided in the constructor."""
        return self._data_gathering_callback(options, pretask_results)


class UserRequestFactory(abc.ABC):
    """Factory for generate user interaction objects."""

    @abc.abstractmethod
    def confirm_removal(self) -> AbstractConfirmFilesystemItemRemoval:
        """Get the correct type of removal dialog."""

    @abc.abstractmethod
    def table_data_editor(
            self,
            enter_data: typing.Callable[
                [
                    Mapping[str, object],
                    List[speedwagon.tasks.Result]
                ], List[Sequence[DataItem]]
            ],
            process_data: Callable[
                [List[Sequence[DataItem]]], TableReportFormat
            ]
    ) -> AbstractTableEditData:
        """Edit table in a table form."""
