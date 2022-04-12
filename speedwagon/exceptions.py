"""Speedwagon exceptions."""

from typing import Optional


class SpeedwagonException(Exception):
    """The base class for speedwagon exceptions."""

    description: Optional[str] = None  # pylint: disable=unsubscriptable-object


class MissingConfiguration(SpeedwagonException):
    """An expected key was missing from the config."""

    description = "Missing required configuration settings"


class JobCancelled(Exception):
    """Job cancelled exception."""

    def __init__(self, *args: object, expected: bool = False) -> None:
        """Indicate a job was cancelled.

        Args:
            *args:
            expected: If the job was cancelled on purpose or not, such as a
                failure.
        """
        super().__init__(*args)
        self.expected = expected
