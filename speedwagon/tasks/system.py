"""System tasks."""
from __future__ import annotations
import abc
import logging
from typing import Optional, TYPE_CHECKING
from speedwagon.config.common import DEFAULT_CONFIG_DIRECTORY_NAME

from speedwagon.config import config
if TYPE_CHECKING:
    from speedwagon.config.common import FullSettingsData
    from speedwagon.config.config import AbsConfigSettings


class AbsSystemTask(abc.ABC):
    """Abstract base class for creating system tasks."""

    def __init__(self) -> None:
        """Create a system task object."""
        self._config_backend: Optional[AbsConfigSettings] = None

    @property
    def config(self) -> Optional[FullSettingsData]:
        """Get current configuration."""
        if self._config_backend:
            return self._config_backend.application_settings()
        return None

    def set_config_backend(self, value: AbsConfigSettings) -> None:
        """Set AbsConfigSettings backend used by config attribute."""
        self._config_backend = value

    @abc.abstractmethod
    def run(self) -> None:
        """Run a startup task."""

    @abc.abstractmethod
    def description(self) -> str:
        """Get human-readable information about current task."""


class EnsureGlobalConfigFiles(AbsSystemTask):
    """Task to ensure all global config files are located on system."""

    def __init__(
        self,
        logger: logging.Logger,
        directory_prefix: str = DEFAULT_CONFIG_DIRECTORY_NAME
    ) -> None:
        """Create a new EnsureGlobalConfigFiles object.

        Args:
            logger: Used to report files being created.
            directory_prefix:
                directory used to hold application config file files
        """
        super().__init__()
        self.logger = logger
        self.directory_prefix = directory_prefix

    def run(self) -> None:
        """Run the ensure settings files task."""
        config.ensure_settings_files(
            logger=self.logger,
            strategy=config.CreateBasicMissingConfigFile(
                logger=self.logger,
                config_location_strategy=config.StandardConfigFileLocator(
                    config_directory_prefix=self.directory_prefix
                ),
            ),
        )

    def description(self) -> str:
        """Get human-readable information about current task."""
        return (
            "Ensuring global settings files are available and creating "
            "defaults where missing."
        )
