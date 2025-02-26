"""Loading plugins for speedwagon."""

from __future__ import annotations

import typing
from typing import Callable, Type, Dict, Optional
import importlib
import logging

import pluggy

from speedwagon.config.plugins import get_whitelisted_plugins
from speedwagon import hookspecs, job
from speedwagon.exceptions import SpeedwagonException

__all__ = [
    'get_plugin_manager',
]

logger = logging.getLogger(__name__)


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


def get_workflows_from_plugin(
    entry_point,
    inclusion_filter: Optional[Callable[[Type[job.Workflow]], bool]] = None
) -> Dict[str, Type[job.Workflow]]:
    workflows: Dict[str, Type[job.Workflow]] = {}
    try:
        plugin = entry_point.load()
        try:
            registered_workflows = \
                typing.cast(
                    Dict[str, Type[job.Workflow]],
                    plugin.registered_workflows()
                )
        except AttributeError as error:
            raise SpeedwagonException(
                f"Plugin missing required property: {error.name}"
            ) from error
        if len(registered_workflows) == 0:
            logger.warning("No workflows were registered in %s", entry_point)

        for workflow_name, workflow_klass in registered_workflows.items():
            if (
                    inclusion_filter is not None and
                    inclusion_filter(workflow_klass) is False
            ):
                continue
            workflows[workflow_name] = workflow_klass
    except (ImportError, AttributeError, SpeedwagonException) as error:
        raise SpeedwagonException(
            f"Unable to load plugin {entry_point}"
        ) from error
    return workflows
