"""Configuration of plugins."""

import abc
import configparser
import io
import logging
import warnings
from typing import Dict, Set, Tuple, List, Callable, Optional

try:  # pragma: no cover
    from typing import TypedDict
except ImportError:  # pragma: no cover
    from typing_extensions import TypedDict
from configparser import ConfigParser

from speedwagon.config import config, common
from speedwagon.utils import read_file

__all__ = [
    "get_whitelisted_plugins_from_config_file",
    "get_whitelisted_plugins_from_config_data",
    "PluginDataType"
]

PluginDataType = Dict[str, Dict[str, bool]]

logger = logging.getLogger(__name__)


def read_settings_data_plugins(data: str) -> PluginDataType:
    with config.ConfigManager(data) as config_manager:
        return config_manager.plugins


def parse_plugin_config_strategy(config_file: str) -> PluginDataType:
    return read_settings_data_plugins(read_file(config_file))


def get_whitelisted_plugins_from_config_file(
    find_config_file_strategy: Callable[[], str] = (
        lambda: (
            config.StandardConfigFileLocator(
                config_directory_prefix=common.DEFAULT_CONFIG_DIRECTORY_NAME
            ).get_config_file()
        )
    ),
    parse_plugin_strategy: Optional[Callable[[str], PluginDataType]] = None,
) -> Set[Tuple[str, str]]:
    """Get whitelisted plugins."""
    warnings.warn(
        "Deprecated used get_whitelisted_plugins_from_config_data instead",
        DeprecationWarning,
        stacklevel=2
    )
    plugin_settings = (
            parse_plugin_strategy or parse_plugin_config_strategy
    )(find_config_file_strategy())
    return get_whitelisted_plugins_from_config_data(plugin_settings)


def get_whitelisted_plugins_from_config_data(
    plugin_settings: PluginDataType
) -> Set[Tuple[str, str]]:
    """Get whitelisted plugins."""
    white_listed_plugins = set()
    for module, entry_points in plugin_settings.items():
        for entry_point in entry_points:
            white_listed_plugins.add((module, entry_point))
    return white_listed_plugins


class PluginSettingsData(TypedDict):
    enabled_plugins: Dict[str, List[Tuple[str, bool]]]


class AbsSerializer(abc.ABC):  # pylint: disable=R0903
    @abc.abstractmethod
    def serialize(self, data: PluginSettingsData) -> str:
        pass


class IniSerializer(AbsSerializer):  # pylint: disable=R0903
    def __init__(self) -> None:
        self.parser = ConfigParser()

    def serialize(self, data: PluginSettingsData) -> str:
        for plugin_name, workflows in data["enabled_plugins"].items():
            section = f"PLUGINS.{plugin_name}"
            try:
                self.parser.add_section(section)
            except configparser.DuplicateSectionError:
                self.parser.remove_section(section)
                self.parser.add_section(section)
            for workflow, activate in workflows:
                self.parser.set(section, workflow, str(activate))

        with io.StringIO() as string_writer:
            self.parser.write(string_writer)
            return string_writer.getvalue()


def parse_plugin_data(settings: common.FullSettingsData) -> PluginDataType:
    sections = {}
    for setting in settings:
        if not setting.startswith("PLUGINS."):
            continue
        section = {}
        for k, v in settings[setting].items():
            try:
                if not isinstance(v, str):
                    raise ValueError
                if v.upper() not in ["TRUE", "FALSE"]:
                    raise ValueError
            except ValueError:
                logging.warning("Invalid plugin setting value: %s = %s", k, v)
                continue
            section[k] = v.upper() == "TRUE"
        sections[setting.removeprefix("PLUGINS.")] = section
    return sections
