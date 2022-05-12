"""Load and save user configurations."""
import argparse
import configparser
import contextlib
import logging
import os
import pathlib
import sys
import typing
from pathlib import Path
import abc
import collections.abc
from typing import Optional, Dict, Type, Set, Iterator, Iterable, Union, List
from types import TracebackType
import platform

try:  # pragma: no cover
    from importlib import metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore

import speedwagon

__all__ = [
    "ConfigManager",
    "generate_default",
    "get_platform_settings",
    "AbsConfig"
]


class AbsConfig(collections.abc.Mapping):
    """Abstract class for defining where speedwagon should find data files."""

    def __init__(self) -> None:
        """Populate the base structure of a config class."""
        super().__init__()
        self._data: Dict[str,  Union[str, bool]] = {}

    @abc.abstractmethod
    def get_user_data_directory(self) -> str:
        """Location for user data."""

    @abc.abstractmethod
    def get_app_data_directory(self) -> str:
        """Location to the application data. Such as .ini file."""

    def __len__(self) -> int:
        """Get the size of the configuration."""
        return len(self._data)

    def __iter__(self) -> Iterator[str]:
        """Iterate over the configuration information."""
        return iter(self._data)

    def __contains__(self, x: object) -> bool:
        """Check if configuration key is in configuration."""
        if x == "app_data_directory":
            return True

        if x == "user_data_directory":
            return True

        return x in self._data

    def __getitem__(self, k: str) -> Union[str, bool]:
        """Get configuration value from a key."""
        if k == "user_data_directory":
            return self.get_user_data_directory()

        if k == "app_data_directory":
            return self.get_app_data_directory()

        return self._data[k]


class NixConfig(AbsConfig):

    def get_user_data_directory(self) -> str:
        data_dir = os.path.join(self._get_app_dir(), "data")
        return data_dir

    def get_app_data_directory(self) -> str:
        data_dir = self._get_app_dir()
        return data_dir

    @staticmethod
    def _get_app_dir() -> str:
        return os.path.join(str(Path.home()), ".config", "Speedwagon")


class WindowsConfig(AbsConfig):
    r"""Speedwagon configuration for running on Microsoft Windows machine.

    It uses a subfolder in the user's home directory to store data such as
    tesseract ocr data. For example:
    ``C:\\\\Users\\\\johndoe\\\\Speedwagon\\\\data``

    It uses ``%LocalAppData%`` for app data

    """

    def get_user_data_directory(self) -> str:
        return os.path.join(str(Path.home()), "Speedwagon", "data")

    def get_app_data_directory(self) -> str:
        """Get path the app data for the current system."""
        data_path = os.getenv("LocalAppData")
        if data_path:
            return os.path.join(data_path, "Speedwagon")
        raise FileNotFoundError("Unable to located data_directory")


class ConfigManager(contextlib.AbstractContextManager):
    """Manager for configurations."""

    BOOLEAN_SETTINGS = [
            "debug",
        ]

    def __init__(self, config_file: str):
        """Set up configuration manager."""
        self._config_file = config_file
        self.cfg_parser: Optional['configparser.ConfigParser'] = None

    def __enter__(self) -> "ConfigManager":
        """Open file with parser."""
        self.cfg_parser = configparser.ConfigParser()
        self.cfg_parser.read(self._config_file)
        return self

    def __exit__(self,
                 exctype: Optional[Type[BaseException]],
                 excinst: Optional[BaseException],
                 exctb: Optional[TracebackType]) -> Optional[bool]:
        return None

    @property
    def global_settings(self) -> Dict[str, Union[str, bool]]:
        """Global settings."""
        if self.cfg_parser is None:
            return {}

        global_settings: Dict[str, Union[str, bool]] = {}
        try:
            global_section = self.cfg_parser["GLOBAL"]
            for setting in ConfigManager.BOOLEAN_SETTINGS:
                if setting in global_section:
                    global_settings[setting] = \
                        global_section.getboolean(setting)

            for key, value in global_section.items():
                if key not in ConfigManager.BOOLEAN_SETTINGS:
                    global_settings[key] = value

        except KeyError:
            print("Unable to load global settings.", file=sys.stderr)
        return global_settings


def generate_default(config_file: str) -> None:
    """Generate config file with default settings."""
    base_directory = os.path.dirname(config_file)
    if base_directory and not os.path.exists(base_directory):
        os.makedirs(base_directory)

    platform_settings = get_platform_settings()
    data_dir = platform_settings.get("user_data_directory")
    if data_dir is None:
        raise FileNotFoundError("Unable to locate user data directory")

    tessdata = os.path.join(data_dir, "tessdata")

    config = configparser.ConfigParser(allow_no_value=True)
    config.add_section("GLOBAL")
    config['GLOBAL'] = {
        "tessdata": tessdata,
        "starting-tab": "Tools",
        "debug": "False"
    }

    with open(config_file, "w", encoding="utf-8") as file:
        config.write(file)
    ensure_keys(config_file, speedwagon.job.all_required_workflow_keys())


def get_platform_settings(configuration: Optional[AbsConfig] = None) -> \
        AbsConfig:
    """Load a configuration of config.AbsConfig.

    If no argument is included, it will try to guess the best one.
    """
    configurations: Dict[str, Type[AbsConfig]] = {
        "Windows": WindowsConfig,
        "Darwin": NixConfig,
        "Linux": NixConfig,
    }
    if configuration is None:
        system_config = configurations.get(platform.system())
        if system_config is None:
            raise ValueError(f"Platform {platform.system()} not supported")
        return system_config()
    return configuration


def find_missing_global_entries(
        config_file: str,
        expected_keys: Iterable[str]) -> Optional[Set[str]]:
    """Locate any missing entries from a config file.

    Notes:
        This only checks in the GLOBAL section

    Args:
        config_file: file path to the config ini file
        expected_keys: list of keys (as strings) to check

    Returns:
        Set of keys that are missing, else None is returned.

    """
    config_data = configparser.ConfigParser()
    config_data.read(config_file)
    global_settings = config_data['GLOBAL']
    missing = set()
    for k in expected_keys:
        if k not in global_settings:
            missing.add(k)

    return missing if len(missing) > 0 else None


def ensure_keys(config_file: str, keys: Iterable[str]) -> Optional[Set[str]]:
    """Make sure that the config file contains the following keys.

    If this file is missing the keys, empty keys are added. Existing keys are
    ignored and left untouched.

    Args:
        config_file: file path to the config ini file
        keys: keys to make sure that exists

    Returns:
        Set of keys that were added, else None is returned.

    """
    config_data = configparser.ConfigParser()
    config_data.read(config_file)
    global_settings = config_data['GLOBAL']
    added = set()

    for k in keys:
        if k not in global_settings:
            config_data['GLOBAL'][k] = ""
            added.add(k)

    with open(config_file, "w", encoding="utf-8") as file_pointer:
        config_data.write(file_pointer)

    return added if len(added) > 0 else None


class AbsSetting(metaclass=abc.ABCMeta):

    @property
    @staticmethod
    @abc.abstractmethod
    def friendly_name():
        return NotImplementedError

    def update(  # pylint: disable=R0201
            self,
            settings: Dict[str, Union[str, bool]] = None
    ) -> Dict["str", Union[str, bool]]:
        if settings is None:
            return {}
        return settings


class DefaultsSetter(AbsSetting):
    friendly_name = "Setting defaults"

    def update(
            self,
            settings: Dict[str, Union[str, bool]] = None
    ) -> Dict["str", Union[str, bool]]:
        new_settings = super().update(settings)
        new_settings["debug"] = False
        return new_settings


class ConfigFileSetter(AbsSetting):
    friendly_name = "Config file settings"

    def __init__(self, config_file: str):
        """Create a new config file setter."""
        self.config_file = config_file

    def update(
            self,
            settings: Dict[str, Union[str, bool]] = None
    ) -> Dict["str", Union[str, bool]]:
        """Update setting configuration."""
        new_settings = super().update(settings)
        with speedwagon.config.ConfigManager(self.config_file) as cfg:
            new_settings.update(cfg.global_settings.items())
        return new_settings


class CliArgsSetter(AbsSetting):

    friendly_name = "Command line arguments setting"

    def __init__(self, args: Optional[typing.List[str]] = None) -> None:
        super().__init__()
        self.args = args if args is not None else sys.argv[1:]

    def update(
            self,
            settings: Dict[str, Union[str, bool]] = None
    ) -> Dict["str", Union[str, bool]]:
        new_settings = super().update(settings)

        args = self._parse_args(self.args)
        if args.start_tab is not None:
            new_settings["starting-tab"] = args.start_tab

        if args.debug is True:
            new_settings["debug"] = args.debug

        return new_settings

    @staticmethod
    def get_arg_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        try:
            current_version = metadata.version(__package__)
        except metadata.PackageNotFoundError:
            current_version = "dev"
        parser.add_argument(
            '--version',
            action='version',
            version=current_version
        )

        parser.add_argument(
            "--starting-tab",
            dest="start_tab",
            help="Which tab to have open on start"
        )

        parser.add_argument(
            "--debug",
            dest="debug",
            action='store_true',
            help="Run with debug mode"
        )

        subparsers = parser.add_subparsers(
            dest='command',
            help='sub-command help'
        )

        run_parser = subparsers.add_parser('run', help='run help')

        run_parser.add_argument(
            '--json',
            type=argparse.FileType("r", encoding="utf-8"),
            help='Run job from json file'
        )

        return parser

    @staticmethod
    def _parse_args(args: typing.List[str]) -> argparse.Namespace:
        parser = CliArgsSetter.get_arg_parser()
        return parser.parse_args(args)


class ConfigLoader:

    @staticmethod
    def read_settings_file(settings_file: str) -> Dict[str, Union[str, bool]]:
        with speedwagon.config.ConfigManager(settings_file) as config:
            return config.global_settings

    def __init__(self, config_file: str) -> None:
        super().__init__()
        self.config_file = config_file
        self.resolution_strategy_order: Optional[List[AbsSetting]] = None
        self.platform_settings = get_platform_settings()
        self.logger = logging.getLogger(__package__)
        self.startup_settings: Dict[str, Union[str, bool]] = {}

    @staticmethod
    def _resolve(
            resolution_strategy_order: Iterable[AbsSetting],
            config_file: str,
            starting_settings: Dict[str, Union[str, bool]],
            logger: logging.Logger
    ) -> Dict[str, Union[str, bool]]:

        settings = starting_settings.copy()
        for settings_strategy in resolution_strategy_order:

            logger.debug("Loading settings from %s",
                         settings_strategy.friendly_name)

            try:
                settings = settings_strategy.update(settings)
            except ValueError as error:
                if isinstance(settings_strategy, ConfigFileSetter):
                    logger.warning(
                        "%s contains an invalid setting. Details: %s",
                        config_file,
                        error
                    )

                else:
                    logger.warning("%s is an invalid setting", error)
        return settings

    def get_settings(self) -> Dict[str, Union[str, bool]]:
        self.read_settings_file(self.config_file)
        if self.resolution_strategy_order is None:
            resolution_order = [
                speedwagon.config.DefaultsSetter(),
                ConfigFileSetter(self.config_file),
                speedwagon.config.CliArgsSetter(),
            ]
        else:
            resolution_order = self.resolution_strategy_order

        return self._resolve(
            resolution_order,
            config_file=self.config_file,
            logger=self.logger,
            starting_settings=self.startup_settings
        )


class AbsEnsureConfigFile(abc.ABC):

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        super().__init__()
        self.logger = logger or logging.getLogger(__package__)

    @abc.abstractmethod
    def ensure_config_file(self, file_path: Optional[str] = None) -> None:
        """Ensure the config.ini file."""

    @abc.abstractmethod
    def ensure_user_data_dir(self, directory: Optional[str] = None) -> None:
        """Ensure the user data directory exists."""

    @abc.abstractmethod
    def ensure_tabs_file(self, file_path: Optional[str] = None) -> None:
        """Ensure the tabs.yml file."""

    @abc.abstractmethod
    def ensure_app_data_dir(self, directory: Optional[str] = None) -> None:
        """Ensure the user app directory exists."""


class CreateBasicMissingConfigFile(AbsEnsureConfigFile):
    """Create a missing config file if not already exists."""

    def __init__(
            self,
            app: speedwagon.startup.AbsStarter,
            logger: Optional[logging.Logger] = None
    ) -> None:
        super().__init__(logger)
        self.app = app

    def ensure_config_file(self, file_path: Optional[str] = None) -> None:
        file_path = file_path or self.app.config_file
        if not os.path.exists(file_path):
            generate_default(file_path)

            self.logger.debug("No config file found. Generated %s", file_path)
        else:
            self.logger.debug("Found existing config file %s", file_path)

    def ensure_tabs_file(self, file_path: Optional[str] = None) -> None:
        file_path = file_path or self.app.tabs_file
        if not os.path.exists(file_path):
            pathlib.Path(file_path).touch()

            self.logger.debug(
                "No tabs.yml file found. Generated %s", file_path
            )
        else:
            self.logger.debug(
                "Found existing tabs file %s", file_path)

    def ensure_user_data_dir(self, directory: Optional[str] = None) -> None:
        directory = directory or self.app.user_data_dir
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            self.logger.debug("Created directory %s", directory)

        else:
            self.logger.debug(
                "Found existing user data directory %s",
                directory
            )

    def ensure_app_data_dir(self, directory: Optional[str] = None) -> None:
        directory = directory or self.app.app_data_dir
        if directory is not None and \
                not os.path.exists(directory):

            os.makedirs(directory)
            self.logger.debug("Created %s", directory)
        else:
            self.logger.debug(
                "Found existing app data "
                "directory %s",
                directory
            )


def ensure_settings_files(
        starter: speedwagon.startup.AbsStarter,
        logger: Optional[logging.Logger] = None,
        strategy: Optional[AbsEnsureConfigFile] = None
) -> None:

    logger = logger or logging.getLogger(__package__)
    strategy = strategy or CreateBasicMissingConfigFile(
        app=starter,
        logger=logger
    )
    strategy.ensure_config_file()
    strategy.ensure_tabs_file()
    strategy.ensure_user_data_dir()
    strategy.ensure_app_data_dir()


class AbsOpenSettings(abc.ABC):

    def __init__(self, settings_directory: str) -> None:
        super().__init__()
        self.settings_dir = settings_directory

    @abc.abstractmethod
    def system_open_directory(self, settings_directory: str) -> None:
        """Open the directory in os's file browser.

        Args:
            settings_directory: Path to the directory
        """

    def open(self) -> None:
        self.system_open_directory(self.settings_dir)


class DarwinOpenSettings(AbsOpenSettings):
    def system_open_directory(self, settings_directory: str) -> None:
        os.system(f"open {settings_directory}")


class WindowsOpenSettings(AbsOpenSettings):

    def system_open_directory(self, settings_directory: str) -> None:
        # pylint: disable=no-member
        os.startfile(settings_directory)  # type: ignore


class OpenSettingsDirectory:

    def __init__(self, strategy: AbsOpenSettings) -> None:
        self.strategy = strategy

    def system_open_directory(self, settings_directory: str) -> None:
        self.strategy.system_open_directory(settings_directory)

    def open(self) -> None:
        self.strategy.open()
