"""Shared data."""

from typing import Union, Dict

SettingsDataType = Union[str, bool, int, None]
SettingsData = Dict[str, SettingsDataType]
FullSettingsData = Dict[str, SettingsData]
