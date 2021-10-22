"""Speedwagon exceptions."""

from typing import Optional


class SpeedwagonException(Exception):
    """The base class for speedwagon exceptions."""

    description: Optional[str] = None  # pylint: disable=unsubscriptable-object


class MissingConfiguration(SpeedwagonException):
    """An expected key was missing from the config."""

    description = "Missing required configuration settings"
