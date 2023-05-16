from typing import Dict, Set, Tuple
import speedwagon

__all__ = ["get_whitelisted_plugins"]

PluginDataType = Dict[str, Dict[str, bool]]


def read_settings_file_plugins(settings_file: str) -> PluginDataType:
    with speedwagon.config.ConfigManager(settings_file) as config:
        return config.plugins


def get_whitelisted_plugins() -> Set[Tuple[str, str]]:
    config_strategy = speedwagon.config.StandardConfigFileLocator()
    plugin_settings = read_settings_file_plugins(
        config_strategy.get_config_file()
    )

    white_listed_plugins = set()
    for module, entry_points in plugin_settings.items():
        for entry_point in entry_points:
            white_listed_plugins.add((module, entry_point))
    return white_listed_plugins
