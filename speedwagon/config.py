"""Load and save user configurations."""
from __future__ import annotations
import argparse
import configparser
import contextlib
import logging
import os
import pathlib
import subprocess
import sys
import typing
from pathlib import Path
import abc
import collections.abc
from typing import Optional, Dict, Type, Set, Iterator, Iterable, Union, \
    List, Callable, NamedTuple
from types import TracebackType
import platform
import io
import yaml
import yaml.emitter


import speedwagon
from speedwagon.exceptions import TabLoadFailure


try:  # pragma: no cover
    from importlib import metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore


WORKFLOWS_SETTINGS_YML_FILE_NAME = "workflows_settings.yml"

__all__ = [
    "AbsConfig",
    "AbsConfigSettings",
    "AbsTabsConfigDataManagement",
    "ConfigManager",
    "CustomTabsYamlConfig",
    "generate_default",
    "get_platform_settings",
    "SettingsData",
    "SettingsDataType",
]

SettingsDataType = typing.Union[str, bool, int]
SettingsData = Dict[str, SettingsDataType]
PluginDataType = Dict[str, Dict[str, bool]]
FullSettingsData = Dict[str, SettingsData]


class AbsConfig(collections.abc.Mapping):
    """Abstract class for defining where speedwagon should find data files."""

    def __init__(self) -> None:
        """Populate the base structure of a config class."""
        super().__init__()
        self._data: SettingsData = {}

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

    def __getitem__(self, k: str) -> Union[str, bool, int]:
        """Get configuration value from a key."""
        if k == "user_data_directory":
            return self.get_user_data_directory()

        if k == "app_data_directory":
            return self.get_app_data_directory()

        return self._data[k]


class NixConfig(AbsConfig):

    def get_user_data_directory(self) -> str:
        return os.path.join(self._get_app_dir(), "data")

    def get_app_data_directory(self) -> str:
        return self._get_app_dir()

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
        """Clean up."""
        return None

    @property
    def global_settings(self) -> SettingsData:
        """Global settings."""
        if self.cfg_parser is None:
            return {}

        global_settings: SettingsData = {}
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

    @property
    def plugins(self) -> Dict[str, Dict[str, bool]]:
        """Get plugin information from the config file."""
        if self.cfg_parser is None:
            return {}
        plugins = {}

        plugin_prefix = 'PLUGINS.'
        for section in self.cfg_parser.sections():
            if not section.startswith(plugin_prefix):
                continue
            plugins[section.replace(plugin_prefix, '')] = {
                entry: self.cfg_parser[section].getboolean(entry)
                for entry in self.cfg_parser[section].keys()
            }
        return plugins


def generate_default(config_file: str) -> None:
    """Generate config file with default settings."""
    base_directory = os.path.dirname(config_file)
    if base_directory and not os.path.exists(base_directory):
        os.makedirs(base_directory)

    platform_settings = get_platform_settings()
    data_dir: Optional[str] = platform_settings.get("user_data_directory")
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


class AbsSetting(metaclass=abc.ABCMeta):  # pylint: disable=R0903

    def update(
            self,
            settings: Optional[FullSettingsData] = None
    ) -> FullSettingsData:
        if settings is None:
            return {}
        return settings


class DefaultsSetter(AbsSetting):  # pylint: disable=R0903
    def update(
            self,
            settings: Optional[FullSettingsData] = None
    ) -> FullSettingsData:
        new_settings = super().update(settings)
        if "GLOBAL" not in new_settings:
            new_settings["GLOBAL"] = {}
        global_settings = new_settings["GLOBAL"]
        global_settings["debug"] = False
        return new_settings


class ConfigFileSetter(AbsSetting):  # pylint: disable=R0903
    friendly_name = "Config file settings"

    def __init__(self, config_file: str):
        """Create a new config file setter."""
        self.config_file = config_file
        self.boolean_settings: List[str] = [
            "debug"
        ]
        self.int_settings: List[str] = []

    @staticmethod
    def read_config_data(config_file: str) -> str:
        with open(config_file, encoding="utf-8") as file_handle:
            return file_handle.read()

    def update(
            self,
            settings: Optional[FullSettingsData] = None
    ) -> FullSettingsData:
        """Update setting configuration."""
        new_settings = super().update(settings)
        cfg_parser = configparser.ConfigParser()
        cfg_parser.read_string(self.read_config_data(self.config_file))
        settings_data = {
            section_name: self.process_section(cfg_parser[section_name])
            for section_name in cfg_parser.sections()
        }
        new_settings.update(settings_data)
        return new_settings

    def process_section(
            self,
            section: configparser.SectionProxy
    ) -> SettingsData:
        processed_section: SettingsData = {}

        for key, value in section.items():
            if key in self.boolean_settings:
                processed_section[key] = section.getboolean(key)
            elif key in self.int_settings:
                processed_section[key] = section.getint(key)
            else:
                processed_section[key] = value
        return processed_section


class CliArgsSetter(AbsSetting):

    def __init__(self, args: Optional[typing.List[str]] = None) -> None:
        super().__init__()
        self.args = args if args is not None else sys.argv[1:]

    def update(
            self,
            settings: Optional[FullSettingsData] = None
    ) -> FullSettingsData:
        new_settings = super().update(settings)
        if "GLOBAL" not in new_settings:
            new_settings["GLOBAL"] = {}
        global_settings = new_settings['GLOBAL']
        args = self._parse_args(self.args)

        starting_tab: Optional[str] = args.start_tab
        if starting_tab is not None:
            global_settings["starting-tab"] = starting_tab

        debug: bool = args.debug
        if debug:
            global_settings["debug"] = debug

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


def read_settings_file_plugins(
        settings_file: str
) -> PluginDataType:
    with speedwagon.config.ConfigManager(settings_file) as config:
        return config.plugins


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
            logger: Optional[logging.Logger] = None
    ) -> None:
        super().__init__(logger)
        self.config_strategy = StandardConfigFileLocator()

    def ensure_config_file(self, file_path: Optional[str] = None) -> None:

        file_path = file_path or self.config_strategy.get_config_file()
        if not os.path.exists(file_path):
            generate_default(file_path)

            self.logger.debug("No config file found. Generated %s", file_path)
        else:
            self.logger.debug("Found existing config file %s", file_path)

    def ensure_tabs_file(self, file_path: Optional[str] = None) -> None:

        file_path = file_path or self.config_strategy.get_tabs_file()
        if not os.path.exists(file_path):
            pathlib.Path(file_path).touch()

            self.logger.debug(
                "No tabs.yml file found. Generated %s", file_path
            )
        else:
            self.logger.debug(
                "Found existing tabs file %s", file_path)

    def ensure_user_data_dir(self, directory: Optional[str] = None) -> None:
        directory = directory or self.config_strategy.get_user_data_dir()
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            self.logger.debug("Created directory %s", directory)

        else:
            self.logger.debug(
                "Found existing user data directory %s",
                directory
            )

    def ensure_app_data_dir(self, directory: Optional[str] = None) -> None:
        directory = directory or self.config_strategy.get_app_data_dir()
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
        logger: Optional[logging.Logger] = None,
        strategy: Optional[AbsEnsureConfigFile] = None
) -> None:

    logger = logger or logging.getLogger(__package__)
    strategy = strategy or CreateBasicMissingConfigFile(
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
        subprocess.call(["/usr/bin/open", settings_directory])


class WindowsOpenSettings(AbsOpenSettings):

    def system_open_directory(self, settings_directory: str) -> None:
        # pylint: disable=no-member
        os.startfile(settings_directory)  # type: ignore[attr-defined]


class OpenSettingsDirectory:

    def __init__(self, strategy: AbsOpenSettings) -> None:
        self.strategy = strategy

    def system_open_directory(self, settings_directory: str) -> None:
        self.strategy.system_open_directory(settings_directory)

    def open(self) -> None:
        self.strategy.open()


def get_whitelisted_plugins() -> Set[typing.Tuple[str, str]]:
    config_strategy = speedwagon.config.StandardConfigFileLocator()
    plugin_settings = \
        read_settings_file_plugins(config_strategy.get_config_file())

    white_listed_plugins = set()
    for module, entry_points in plugin_settings.items():
        for entry_point in entry_points:
            white_listed_plugins.add((module, entry_point))
    return white_listed_plugins


class AbsSettingLocator(abc.ABC):
    @abc.abstractmethod
    def get_user_data_dir(self) -> str:
        """Get user data directory."""

    @abc.abstractmethod
    def get_app_data_dir(self) -> str:
        """Get app data directory."""

    @abc.abstractmethod
    def get_config_file(self) -> str:
        """Get config file used."""

    @abc.abstractmethod
    def get_tabs_file(self) -> str:
        """Get tabs settings file used."""


class StandardConfigFileLocator(AbsSettingLocator):
    def __init__(self) -> None:
        self._platform_settings = get_platform_settings()

    def get_user_data_dir(self) -> str:
        return typing.cast(
            str,
            self._platform_settings.get("user_data_directory")
        )

    def get_config_file(self) -> str:
        return os.path.join(
            self._platform_settings.get_app_data_directory(),
            speedwagon.startup.CONFIG_INI_FILE_NAME
        )

    def get_app_data_dir(self) -> str:
        return typing.cast(str, self._platform_settings["app_data_directory"])

    def get_tabs_file(self) -> str:
        return os.path.join(
            self._platform_settings.get_app_data_directory(),
            speedwagon.startup.TABS_YML_FILE_NAME
        )


class AbsConfigSettings(abc.ABC):  # pylint: disable=R0903
    """Abstract base class for getting settings."""

    @abc.abstractmethod
    def settings(self) -> FullSettingsData:
        """Get the current app settings."""


class StandardConfig(AbsConfigSettings):
    def __init__(self) -> None:
        super().__init__()
        self.config_loader_strategy: Optional[AbsConfigLoader] = None

    def settings(self) -> FullSettingsData:
        return self.resolve_settings()

    def resolve_settings(self) -> FullSettingsData:
        if self.config_loader_strategy is not None:
            return self.config_loader_strategy.get_settings()

        file_locator = StandardConfigFileLocator()
        loader = MixedConfigLoader()
        loader.resolution_strategy_order = [
            DefaultsSetter(),
            ConfigFileSetter(file_locator.get_config_file()),
            CliArgsSetter(),
        ]
        return loader.get_settings()


class AbsTabsConfigDataManagement(abc.ABC):
    """Abstract base model for managing saving and loading serialized data."""

    @abc.abstractmethod
    def data(self) -> List[CustomTabData]:
        """Get the data for custom tabs."""

    @abc.abstractmethod
    def save(self, tabs: List[CustomTabData]):
        """Get the data for custom tabs."""


class CustomTabData(NamedTuple):
    tab_name: str
    workflow_names: List[str]


class AbsTabsYamlFileReader(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def read_file(yaml_file: str) -> str:
        """Read file and return a string."""

    @abc.abstractmethod
    def decode_tab_settings_yml_data(self, data: str) -> Dict[str,  List[str]]:
        """Decode data."""


class TabsYamlFileReader(AbsTabsYamlFileReader):
    @staticmethod
    def read_file(yaml_file: str) -> str:
        with open(yaml_file, encoding="utf-8") as file_handler:
            return file_handler.read()

    def decode_tab_settings_yml_data(self, data: str) -> Dict[str,  List[str]]:
        tabs_config_data = yaml.load(data, Loader=yaml.SafeLoader)
        if not isinstance(tabs_config_data, dict):
            raise speedwagon.exceptions.FileFormatError("Failed to parse file")
        return tabs_config_data


class CustomTabsYamlConfig(AbsTabsConfigDataManagement):
    """YAML config file manager."""

    def __init__(self, yaml_file: str) -> None:
        """Create a new yaml config object.

        Args:
            yaml_file: path to a yaml file to use to read or save to.

        """
        self.yaml_file = yaml_file
        self.file_reader_strategy: AbsTabsYamlFileReader = TabsYamlFileReader()
        self.file_writer_strategy: AbsTabWriter = TabsYamlWriter()
        self.data_reader: Optional[Callable[[], str]] = None

    def decode_data(self, data: str) -> Dict[str,  List[str]]:
        """Decode a YAML string to a dictionary."""
        return self.file_reader_strategy.decode_tab_settings_yml_data(data)

    def data(self) -> List[CustomTabData]:
        """Get Yaml file data."""
        try:
            if self.data_reader is not None:
                data = self.data_reader()
            else:
                data = self.file_reader_strategy.read_file(self.yaml_file)
            yml_data = \
                self.file_reader_strategy.decode_tab_settings_yml_data(data)
        except yaml.YAMLError as error:
            raise TabLoadFailure(
                f"{self.yaml_file} file failed to load."
            ) from error
        except FileNotFoundError as error:
            raise TabLoadFailure(
                f"Custom tabs file {self.yaml_file} not found"
            ) from error
        except (TypeError, speedwagon.exceptions.FileFormatError) as error:
            raise TabLoadFailure() from error
        return [
            CustomTabData(tab_name, workflow_names)
            for tab_name, workflow_names in yml_data.items()
        ]

    def save(self, tabs: List[CustomTabData]):
        """Write tabs to a yaml file."""
        self.file_writer_strategy.save(self.yaml_file, tabs)


class AbsTabWriter(abc.ABC):  # pylint: disable=R0903
    def save(self, file_name: str, tabs: List[CustomTabData]) -> None:
        """Save tabs data to a file format."""


class TabsYamlWriter(AbsTabWriter):
    def save(self, file_name: str, tabs: List[CustomTabData]) -> None:
        data = self.serialize(tabs)
        self.write_data(file_name, data)

    @staticmethod
    def write_data(file_name, data):
        with open(file_name, "w", encoding="utf-8") as file_handle:
            file_handle.write(data)

    @staticmethod
    def serialize(tabs: List[CustomTabData]) -> str:
        tabs_data = {
            tab_name: list(tab_workflows) for tab_name, tab_workflows in tabs
        }
        with io.StringIO() as file_handle:
            yaml.dump(tabs_data, file_handle, default_flow_style=False)
            value = file_handle.getvalue()
        return value


class AbsGlobalConfigDataManagement(abc.ABC):
    @abc.abstractmethod
    def save(self, data: FullSettingsData) -> None:
        """Save data."""

    @abc.abstractmethod
    def data(self) -> FullSettingsData:
        """Get data."""


class AbsConfigSaver(abc.ABC):  # pylint: disable=R0903
    @abc.abstractmethod
    def save(self, file_name: str, data: FullSettingsData):
        """Save data to a file."""


class IniConfigManager(AbsGlobalConfigDataManagement):

    def __init__(self, ini_file: Optional[str] = None) -> None:
        self.config_file: Optional[str] = ini_file
        self.loader: Optional[AbsConfigLoader] = None
        self.saver: Optional[AbsConfigSaver] = None
        self.config_resolution_order: Optional[List[AbsSetting]] = None

    def get_resolution_order(self) -> List[AbsSetting]:
        if self.config_resolution_order is not None:
            return self.config_resolution_order

        config_file = \
            self.config_file or \
            StandardConfigFileLocator().get_config_file()
        resolution_order: List[AbsSetting] = [
            DefaultsSetter(),
        ]
        if self.config_file:
            resolution_order.append(ConfigFileSetter(config_file))
        resolution_order.append(speedwagon.config.CliArgsSetter())
        return resolution_order

    def loader_strategy(self) -> AbsConfigLoader:
        if self.loader:
            return self.loader
        strategy = MixedConfigLoader()
        strategy.resolution_strategy_order = self.get_resolution_order()
        return strategy

    def save_strategy(self) -> AbsConfigSaver:
        if self.saver:
            return self.saver
        return IniConfigSaver()

    def data(self) -> FullSettingsData:
        return self.loader_strategy().get_settings()

    def save(self, data: FullSettingsData) -> None:
        if self.config_file is None:
            return
        self.save_strategy().save(self.config_file, data)


class IniConfigSaver(AbsConfigSaver):

    def save(self, file_name: str, data: FullSettingsData):
        serialized_data = self.serialize(data)
        self.write_data_to_file(
            file_name,
            serialized_data=serialized_data
        )

    def serialize(self, data: FullSettingsData) -> str:
        config_data = configparser.ConfigParser()
        for heading, item_data in data.items():
            config_data[heading] = {
                key: str(value)
                for key, value in item_data.items()
            }

        with io.StringIO() as string_writer:
            config_data.write(string_writer)
            return string_writer.getvalue()

    def write_data_to_file(self, file_name: str, serialized_data: str) -> None:
        with open(file_name, "w", encoding="utf-8") as file_handler:
            file_handler.write(serialized_data)


class AbsConfigLoader(abc.ABC):  # pylint: disable=R0903

    @abc.abstractmethod
    def get_settings(self) -> FullSettingsData:
        """Get the settings data."""


class MixedConfigLoader(AbsConfigLoader):  # pylint: disable=R0903

    def __init__(self) -> None:
        super().__init__()
        self.resolution_strategy_order: List[AbsSetting] = [
            speedwagon.config.DefaultsSetter()
        ]
        self.platform_settings = get_platform_settings()

    @staticmethod
    def _resolve(
            resolution_strategy_order: Iterable[AbsSetting]
    ) -> FullSettingsData:
        settings: FullSettingsData = {}
        for settings_strategy in resolution_strategy_order:
            settings = settings_strategy.update(settings)
        return settings

    def get_settings(self) -> FullSettingsData:
        return self._resolve(self.resolution_strategy_order)


class AbsWorkflowSettingsManager(abc.ABC):

    @abc.abstractmethod
    def get_workflow_settings(
            self,
            workflow: speedwagon.Workflow
    ) -> SettingsData:
        """Get settings for a workflow configured through the application."""

    @abc.abstractmethod
    def save_workflow_settings(
            self,
            workflow: speedwagon.Workflow,
            settings: SettingsData
    ) -> None:
        """Save workflow settings."""


class IndentingEmitter(yaml.emitter.Emitter):
    def increase_indent(self, flow=False, indentless=False):
        """Ensure that lists items are always indented."""
        return super().increase_indent(
            flow=False,
            indentless=False,
        )


class IndentedYAMLDumper(yaml.Dumper):  # pylint: disable=R0903

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


class AbsWorkflowSettingsExporter(abc.ABC):  # pylint: disable=R0903
    @abc.abstractmethod
    def save(
            self,
            workflow:
            speedwagon.Workflow,
            settings: SettingsData
    ) -> None:
        """Save settings."""


class AbsYamlConfigFileManager(abc.ABC):  # pylint: disable=R0903
    def __init__(self, yaml_file) -> None:
        super().__init__()
        self.yaml_file = yaml_file


class WorkflowSettingsYamlExporter(
    AbsYamlConfigFileManager,
    AbsWorkflowSettingsExporter
):

    @staticmethod
    def write_data_to_file(data: str, file_name: str) -> None:
        with open(file_name, "w", encoding="utf-8") as file_handle:
            file_handle.write(data)

    def get_existing_data(self):
        if os.path.exists(self.yaml_file):
            with open(self.yaml_file, "r", encoding="utf-8") as handle:
                return yaml.load(handle, Loader=yaml.SafeLoader)
        return {}

    def serialize_settings_data(
            self,
            workflow: speedwagon.Workflow,
            settings: SettingsData
    ) -> str:
        data = self.get_existing_data()
        if workflow.name in data:
            del data[workflow.name]
        data[workflow.name] = [
                {"name": key, "value": value}
                for key, value in settings.items()
            ]
        with io.StringIO() as file_handle:
            yaml.dump(
                dict(sorted(data.items())),
                file_handle,
                Dumper=IndentedYAMLDumper
            )
            return file_handle.getvalue()

    def save(
            self,
            workflow: speedwagon.Workflow,
            settings: SettingsData
    ) -> None:
        self.write_data_to_file(
            data=self.serialize_settings_data(workflow, settings),
            file_name=self.yaml_file
        )


class AbsWorkflowSettingsResolver(abc.ABC):  # pylint: disable=R0903
    @abc.abstractmethod
    def get_response(self, workflow: speedwagon.Workflow) -> SettingsData:
        """Get settings data from workflow."""


class WorkflowSettingsYAMLResolver(
    AbsYamlConfigFileManager,
    AbsWorkflowSettingsResolver
):

    @staticmethod
    def read_file(file_name: str) -> str:
        with open(file_name, "r", encoding="utf-8") as file_handle:
            return file_handle.read()

    def get_config_data(self):
        config_file = self.yaml_file
        return (
            yaml.load(self.read_file(config_file), Loader=yaml.SafeLoader)
            if os.path.exists(config_file)
            else {}
        )

    def get_response(self, workflow: speedwagon.Workflow) -> SettingsData:
        config_data = self.get_config_data()
        if workflow.name not in config_data:
            return {}
        valid_options = [
            i.setting_name if i.setting_name is not None else i.label
            for i in workflow.configuration_options()
        ]
        return {
            item['name']: item['value']
            for item in config_data[workflow.name]
            if item['name'] in valid_options
        }


class WorkflowSettingsManager(AbsWorkflowSettingsManager):
    def __init__(
            self,
            getter_strategy: Optional[AbsWorkflowSettingsResolver] = None,
            setter_strategy: Optional[AbsWorkflowSettingsExporter] = None
    ) -> None:

        super().__init__()
        self.settings_getter_strategy: AbsWorkflowSettingsResolver = \
            getter_strategy or \
            WorkflowSettingsYAMLResolver(self._get_yaml_file())

        self.settings_saver_strategy: AbsWorkflowSettingsExporter = \
            setter_strategy or \
            WorkflowSettingsYamlExporter(self._get_yaml_file())

    @staticmethod
    def _get_yaml_file() -> str:
        strategy = StandardConfigFileLocator()
        return os.path.join(
            strategy.get_app_data_dir(),
            WORKFLOWS_SETTINGS_YML_FILE_NAME
        )

    def get_workflow_settings(
            self,
            workflow: speedwagon.Workflow
    ) -> SettingsData:
        return \
            self.settings_getter_strategy.get_response(workflow)

    def save_workflow_settings(
            self,
            workflow: speedwagon.Workflow,
            settings: SettingsData
    ) -> None:
        self.settings_saver_strategy.save(workflow, settings)


class AbsWorkflowBackend(abc.ABC):  # pylint: disable=R0903
    @abc.abstractmethod
    def get(self, key: str) -> Optional[SettingsDataType]:
        """Get data for some key"""


class YAMLWorkflowConfigBackend(AbsWorkflowBackend):

    def __init__(self) -> None:
        super().__init__()
        self.yaml_file: Optional[str] = None
        self.workflow: Optional[speedwagon.Workflow] = None
        self.settings_resolver: Optional[AbsWorkflowSettingsResolver] = None

    def get_yaml_strategy(self):
        if self.settings_resolver is not None:
            return self.settings_resolver
        if self.yaml_file is None:
            raise AttributeError("yaml_file not set")
        return speedwagon.config.WorkflowSettingsYAMLResolver(self.yaml_file)

    def get(self, key: str) -> Optional[SettingsDataType]:
        if any(
                [
                    self.yaml_file is None,
                    self.workflow is None
                ]
        ):
            return None
        resolver = self.get_yaml_strategy()
        response = resolver.get_response(self.workflow)
        return response.get(key)
