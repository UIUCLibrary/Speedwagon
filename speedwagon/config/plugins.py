"""Configuration of plugins."""

import abc
import configparser
from typing import Dict, Set, Tuple, List, Callable

try:  # pragma: no cover
    from typing import TypedDict
except ImportError:  # pragma: no cover
    from typing_extensions import TypedDict
from configparser import ConfigParser
import io

from speedwagon.config import config, common

__all__ = ["get_whitelisted_plugins"]

PluginDataType = Dict[str, Dict[str, bool]]


def read_settings_file_plugins(settings_file: str) -> PluginDataType:
    with config.ConfigManager(settings_file) as config_manager:
        return config_manager.plugins


def get_whitelisted_plugins(
    config_file_strategy: Callable[[], str] =
        lambda: config.StandardConfigFileLocator(
            config_directory_prefix=common.DEFAULT_CONFIG_DIRECTORY_NAME
        ).get_config_file()
) -> Set[Tuple[str, str]]:
    """Get whitelisted plugins."""
    plugin_settings = read_settings_file_plugins(config_file_strategy())

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
