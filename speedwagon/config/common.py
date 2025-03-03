"""Shared data."""

from typing import Union, Dict
try:
    from typing import Final
except ImportError:  # pragma: no cover
    from typing_extensions import Final  # type: ignore


SettingsDataType = Union[str, bool, int, None]
SettingsData = Dict[str, SettingsDataType]
FullSettingsData = Dict[str, SettingsData]

DEFAULT_CONFIG_DIRECTORY_NAME: Final[str] = "Speedwagon"
