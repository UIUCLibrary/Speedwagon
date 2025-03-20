"""System tasks."""

from __future__ import annotations
import abc
import logging
from typing import Optional, TYPE_CHECKING, Callable

from speedwagon.config.common import DEFAULT_CONFIG_DIRECTORY_NAME

from speedwagon.config.config import (
    CreateBasicMissingConfigFile,
    StandardConfigFileLocator,
    ensure_settings_files,
    SettingsLocations,
)

if TYPE_CHECKING:
    from speedwagon.config.common import FullSettingsData
    from speedwagon.config.config import AbsConfigSettings, AbsSettingLocator

__all__ = ["AbsSystemTask", "EnsureGlobalConfigFiles", "CallbackSystemTask"]


class AbsSystemTask(abc.ABC):
    """Abstract base class for creating system tasks."""

    def __init__(self) -> None:
        """Create a system task object."""
        self._config_backend: Optional[AbsConfigSettings] = None
        self._config_file_locator: Optional[AbsSettingLocator] = None

    @property
    def config(self) -> Optional[FullSettingsData]:
        """Get current configuration."""
        if self._config_backend:
            return self._config_backend.application_settings()
        return None

    def set_config_file_locator(self, value: AbsSettingLocator) -> None:
        """Set the config file locator."""
        self._config_file_locator = value

    def set_config_backend(self, value: AbsConfigSettings) -> None:
        """Set AbsConfigSettings backend used by config attribute."""
        self._config_backend = value

    @abc.abstractmethod
    def run(self) -> None:
        """Run a startup task."""

    @abc.abstractmethod
    def description(self) -> str:
        """Get human-readable information about current task."""

    def __call__(
        self, config: AbsConfigSettings, config_file_locator: AbsSettingLocator
    ) -> None:
        """Run the task."""
        self._config_backend = config
        self._config_file_locator = config_file_locator
        return self.run()


class EnsureGlobalConfigFiles(AbsSystemTask):
    """Task to ensure all global config files are located on system."""

    def __init__(
        self,
        logger: logging.Logger,
        directory_prefix: str = DEFAULT_CONFIG_DIRECTORY_NAME,
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
        self.ensure_settings_files = ensure_settings_files

    def run(self) -> None:
        """Run the ensure settings files task."""
        ensure_settings_files(
            logger=self.logger,
            strategy=CreateBasicMissingConfigFile(
                logger=self.logger,
                config_location_strategy=StandardConfigFileLocator(
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


def resolve_config_file_location(
    locator: AbsSettingLocator,
) -> SettingsLocations:
    """Resolve the location of the configuration files."""
    locations = SettingsLocations(
        app_data_directory=locator.get_app_data_dir(),
        user_data_directory=locator.get_user_data_dir(),
        tab_config_file=locator.get_tabs_file(),
    )
    return locations


class CallbackSystemTask(AbsSystemTask):
    """Task to run a callback."""

    def __init__(
        self,
        callback: Callable[[AbsConfigSettings, SettingsLocations], None],
        description: str = "Callback task",
    ) -> None:
        """Create a new CallbackSystemTask object.

        Args:
            callback: Function to run when task is executed.
            description: Human-readable description of the task.
        """
        super().__init__()
        self.callback = callback
        self._description = description
        self.config_file_locations_resolving_strategy: Callable[
            [AbsSettingLocator], SettingsLocations
        ] = resolve_config_file_location

    def run(self) -> None:
        """Run the callback."""
        if not self._config_backend:
            raise ValueError("No configuration backend set.")
        if not self._config_file_locator:
            raise ValueError("No config_file_locator backend set.")
        self.callback(
            self._config_backend,
            self.config_file_locations_resolving_strategy(
                self._config_file_locator
            ),
        )

    def description(self) -> str:
        """Get human-readable information about current task."""
        return self._description
