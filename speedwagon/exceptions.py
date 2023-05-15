"""Speedwagon exceptions."""

from typing import Optional


class SpeedwagonException(Exception):
    """The base class for speedwagon exceptions."""

    description: Optional[str] = None  # pylint: disable=unsubscriptable-object


class InvalidConfiguration(SpeedwagonException):
    """Invalid user configuration value."""

    description = "Invalid value is settings"


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


class PluginImportError(Exception):
    """Plugin(s) import failed."""


class InvalidPlugin(Exception):
    """Invalid plugin has been attempted to be instantiated."""

    def __init__(self, *args: object, entry_point) -> None:
        """Create a new InvalidPlugin exception."""
        super().__init__(*args)
        self.entry_point = entry_point


class FileFormatError(SpeedwagonException):
    """Exception is thrown when Something wrong with the contents of a file."""


class TabLoadFailure(SpeedwagonException):
    """Exception is thrown when a tab fails to load."""


class WorkflowLoadFailure(SpeedwagonException):
    """Exception is thrown when a Workflow fails to load."""
