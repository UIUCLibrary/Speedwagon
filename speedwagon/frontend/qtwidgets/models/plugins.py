"""Plugin model code."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast, Optional, List, Union, Any
import sys

from PySide6 import QtCore

if sys.version_info < (3, 10):  # pragma: no cover
    import importlib_metadata as metadata
else:  # pragma: no cover
    from importlib import metadata

__all__ = ["PluginActivationModel"]


@dataclass
class PluginModelItem:
    entrypoint: metadata.EntryPoint
    enabled: bool


class PluginActivationModel(QtCore.QAbstractListModel):
    """Plugin activation model.

    For setting what plugins are active and which are not.
    """

    ModuleRole = cast(int, QtCore.Qt.ItemDataRole.UserRole) + 1

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        """Create a new plugin model.

        Args:
            parent: Parent widget to control widget lifespan
        """
        super().__init__(parent)
        self.data_modified = False
        self._starting_data: List[PluginModelItem] = []
        self._data: List[PluginModelItem] = []
        self.dataChanged.connect(self._update_modified)

    def _update_modified(self) -> None:
        for original, current in zip(self._starting_data, self._data):
            if original.enabled != current.enabled:
                self.data_modified = True
                return
        self.data_modified = False

    def rowCount(  # pylint: disable=invalid-name
        self,
        parent: Union[  # pylint: disable=unused-argument
            QtCore.QModelIndex, QtCore.QPersistentModelIndex, None
        ] = None,
    ) -> int:
        """Get the number of plugins available."""
        return len(self._data)

    def add_entry_point(
        self, entry_point: metadata.EntryPoint, enabled: bool = False
    ) -> None:
        """Add an entry point to the model."""
        self._starting_data.append(PluginModelItem(entry_point, enabled))
        self._data.append(PluginModelItem(entry_point, enabled))

    def flags(
        self, index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.Qt.ItemFlag:
        """Item flags.

        Should be user checkable, enabled, and selectable.
        """
        if index.isValid():
            return (
                QtCore.Qt.ItemFlag.ItemIsUserCheckable
                | QtCore.Qt.ItemFlag.ItemIsSelectable
                | QtCore.Qt.ItemFlag.ItemIsEnabled
            )
        return super().flags(index)

    def data(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Get the data from the model."""
        if role == QtCore.Qt.ItemDataRole.CheckStateRole:
            return (
                QtCore.Qt.CheckState.Checked
                if self._data[index.row()].enabled
                else QtCore.Qt.CheckState.Unchecked
            )

        if role == self.ModuleRole:
            return self._data[index.row()].entrypoint.module

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._data[index.row()].entrypoint.name
        return None

    def setData(  # pylint: disable=invalid-name
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        value: Any,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        """Set the data for the model."""
        if role == QtCore.Qt.ItemDataRole.CheckStateRole:
            self._data[index.row()].enabled = (
                value == QtCore.Qt.CheckState.Checked.value
            )
            self.dataChanged.emit(index, index, (role,))
            return True

        return super().setData(index, value, role)
