"""Settings model code."""

from __future__ import annotations

import typing
from collections import namedtuple
from typing import (
    cast,
    Optional,
    List,
    Union,
    Any,
    Dict,
    TYPE_CHECKING,
    Callable,
    TypeVar
)

from PySide6 import QtCore, QtGui
from speedwagon.workflow import AbsOutputOptionDataType
if TYPE_CHECKING:
    from speedwagon.config import SettingsDataType
    from speedwagon.workflow import UserDataType
    from speedwagon.frontend.qtwidgets.widgets import DynamicForm
__all__ = ["ToolOptionsModel4"]

OptionPair = namedtuple("OptionPair", ("label", "data"))

_T = TypeVar("_T")


class ToolOptionsModel4(QtCore.QAbstractListModel):
    """Tool Model Options."""

    JsonDataRole = cast(int, QtCore.Qt.ItemDataRole.UserRole) + 1
    DataRole = JsonDataRole + 1

    def __init__(
        self,
        data: Optional[List[AbsOutputOptionDataType]] = None,
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        """Create a new ToolOptionsModel4 object."""
        super().__init__(parent)
        self._data = data or []

    def __setitem__(
        self, key: str, value: Optional[Union[str, int, bool]]
    ) -> None:
        """Set the [key] operator.

        This allows for looking up the data based on the key.
        """
        if self._data is None:
            raise IndexError("No data")

        for item in self._data:
            if item.label == key:
                item.value = value
                break
        else:
            raise KeyError(f"Key not found: {key}")

    def flags(
        self,
        index: Union[  # pylint: disable=unused-argument
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ],
    ) -> QtCore.Qt.ItemFlag:
        """Get Qt Widget item flags used for an index."""
        return (
            QtCore.Qt.ItemFlag.ItemIsSelectable
            | QtCore.Qt.ItemFlag.ItemIsEnabled
            | QtCore.Qt.ItemFlag.ItemIsEditable
        )

    def rowCount(  # pylint: disable=invalid-name
        self,
        parent: Optional[  # pylint: disable=unused-argument
            Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
        ] = None,
    ) -> int:
        """Get the amount of entries in the model."""
        return len(self._data)

    def headerData(  # pylint: disable=invalid-name
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Get model header data."""
        if (
            orientation == QtCore.Qt.Orientation.Vertical
            and role == QtCore.Qt.ItemDataRole.DisplayRole
        ):
            return self._data[section].label
        return None

    def data(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Optional[Any]:
        """Get data from model."""
        if not index.isValid():
            return None

        formatter = ModelDataFormatter(self)
        return formatter.format(
            setting=self._data[index.row()],
            role=typing.cast(QtCore.Qt.ItemDataRole, role),
        )

    def setData(  # pylint: disable=invalid-name
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        value: Optional[Any],
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        """Set model data.

        Returns:
            True if successful
        """
        if value is None:
            return False

        if role == typing.cast(int, QtCore.Qt.ItemDataRole.EditRole):
            self._data[index.row()].value = value
            self.dataChanged.emit(index, index, [role])  # type: ignore
            return True
        return super().setData(index, value, role)

    def serialize(self) -> Dict[str, UserDataType]:
        """Serialize model data to a dictionary."""
        return {data.label: data.value for data in self._data}

    def get_as(
        self,
        formating_function: Callable[[List[AbsOutputOptionDataType]], _T]
    ) -> _T:
        """Get formated data using a callable function."""
        return formating_function(self._data)

    def get(self) -> Dict[str, UserDataType]:
        """Access the key value settings for all options."""
        return self.serialize()


class ModelDataFormatter:
    def __init__(self, model: ToolOptionsModel4):
        self._model = model

    @classmethod
    def _select_display_role(
        cls, item: AbsOutputOptionDataType
    ) -> Optional[SettingsDataType]:
        if cls._should_use_placeholder_text(item) is True:
            return item.placeholder_text
        if isinstance(item.value, bool):
            return item.value
        if item.value is None:
            return item.value
        return item.value

    @staticmethod
    def _should_use_placeholder_text(item: AbsOutputOptionDataType) -> bool:
        if item.value is not None:
            return False
        if item.placeholder_text is None:
            return False
        return True

    def font_role(
        self, setting: AbsOutputOptionDataType
    ) -> Optional[QtGui.QFont]:
        if self._should_use_placeholder_text(setting) is True:
            font = QtGui.QFont()
            font.setItalic(True)
            return font
        return None

    def display_role(
        self, setting: AbsOutputOptionDataType
    ) -> Optional[SettingsDataType]:
        return self._select_display_role(setting)

    def format(
        self, setting: AbsOutputOptionDataType, role: QtCore.Qt.ItemDataRole
    ) -> Optional[Any]:
        formatter = {
            QtCore.Qt.ItemDataRole.DisplayRole: self.display_role,
            QtCore.Qt.ItemDataRole.EditRole: lambda setting_: setting_.value,
            QtCore.Qt.ItemDataRole.FontRole: self.font_role,
            self._model.JsonDataRole: lambda conf: conf.build_json_data(),
            self._model.DataRole: lambda setting_: setting_,
        }.get(role)

        if formatter is not None:
            return formatter(setting)

        return None


def load_job_settings_model(
    data: Dict[str, UserDataType],
    settings_widget: DynamicForm,
    workflow_options: List[AbsOutputOptionDataType],
) -> None:
    model = ToolOptionsModel4(workflow_options)
    for key, value in data.items():
        for i in range(model.rowCount()):
            index = model.index(i)
            option_data = typing.cast(
                AbsOutputOptionDataType,
                model.data(index, ToolOptionsModel4.DataRole),
            )

            if option_data.label == key:
                model.setData(index, value, QtCore.Qt.ItemDataRole.EditRole)
    settings_widget.set_model(model)
    settings_widget.update_widget()
