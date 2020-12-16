from typing import Optional


class SpeedwagonException(Exception):
    """The base class for speedwagon exceptions"""
    description: Optional[str] = None  # pylint: disable=unsubscriptable-object


class MissingConfiguration(SpeedwagonException):
    description = "Missing required configuration settings"
