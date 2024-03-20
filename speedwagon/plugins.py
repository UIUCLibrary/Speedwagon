"""Loading plugins for speedwagon."""

from __future__ import annotations
from typing import Callable
import importlib
import pluggy

from speedwagon.config.plugins import get_whitelisted_plugins
from speedwagon import hookspecs

__all__ = [
    'get_plugin_manager',
]


def register_all_plugins(plugin_manager: pluggy.PluginManager) -> None:
    builtin_workflows = importlib.import_module('speedwagon.workflows.builtin')
    plugin_manager.register(builtin_workflows)
    plugin_manager.load_setuptools_entrypoints('speedwagon.plugins')


def register_whitelisted_plugins(plugin_manager: pluggy.PluginManager) -> None:
    register_all_plugins(plugin_manager)
    whitelisted_plugin_names = [
        plugin[-1] for plugin in get_whitelisted_plugins()
    ]
    for plugin_name, _ in plugin_manager.list_name_plugin():
        if plugin_name == "speedwagon.workflows.builtin":
            continue
        if plugin_name not in whitelisted_plugin_names:
            plugin_manager.unregister(name=plugin_name)


def get_plugin_manager(
        register_strategy: Callable[
            [pluggy.PluginManager], None
        ] = register_all_plugins
) -> pluggy.PluginManager:
    """Get plugin manager."""
    plugin_manager = pluggy.PluginManager('speedwagon')
    plugin_manager.add_hookspecs(hookspecs)
    register_strategy(plugin_manager)
    return plugin_manager
