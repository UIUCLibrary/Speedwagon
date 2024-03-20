"""Configuration of plugins."""

import abc
from typing import Dict, Set, Tuple, List

try:  # pragma: no cover
    from typing import TypedDict
except ImportError:  # pragma: no cover
    from typing_extensions import TypedDict
from configparser import ConfigParser
import io

from speedwagon.config import config

__all__ = ["get_whitelisted_plugins"]

PluginDataType = Dict[str, Dict[str, bool]]


def read_settings_file_plugins(settings_file: str) -> PluginDataType:
    with config.ConfigManager(settings_file) as config_manager:
        return config_manager.plugins


def get_whitelisted_plugins() -> Set[Tuple[str, str]]:
    """Get whitelisted plugins."""
    config_strategy = config.StandardConfigFileLocator()
    plugin_settings = read_settings_file_plugins(
        config_strategy.get_config_file()
    )

    white_listed_plugins = set()
    for module, entry_points in plugin_settings.items():
        for entry_point in entry_points:
            white_listed_plugins.add((module, entry_point))
    return white_listed_plugins


class PluginSettingsData(TypedDict):
    enabled_plugins: Dict[str, List[str]]


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
            self.parser.add_section(section)
            for workflow in workflows:
                self.parser.set(section, workflow, "True")

        with io.StringIO() as string_writer:
            self.parser.write(string_writer)
            return string_writer.getvalue()
