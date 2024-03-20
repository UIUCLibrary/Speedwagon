"""System tasks."""

import abc
import speedwagon.config.config


class AbsSystemTask(abc.ABC):
    """Abstract base class for creating system tasks."""

    @abc.abstractmethod
    def run(self) -> None:
        """Run a startup task."""

    @abc.abstractmethod
    def description(self) -> str:
        """Get human-readable information about current task."""


class EnsureGlobalConfigFiles(AbsSystemTask):
    """Task to ensure all global config files are located on system."""

    def __init__(self, logger) -> None:
        """Create a new EnsureGlobalConfigFiles object.

        Args:
            logger: Used to report files being created.
        """
        super().__init__()
        self.logger = logger

    def run(self) -> None:
        """Run the ensure settings files task."""
        speedwagon.config.config.ensure_settings_files(logger=self.logger)

    def description(self) -> str:
        """Get human-readable information about current task."""
        return (
            "Ensuring global settings files are available and creating "
            "defaults where missing."
        )
