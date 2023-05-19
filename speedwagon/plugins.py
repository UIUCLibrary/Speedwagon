"""Loading plugins for speedwagon."""

from __future__ import annotations
import abc
import typing
from typing import Type, Dict, Tuple, Set, Iterable, List

import sys
import speedwagon

if sys.version_info < (3, 10):  # pragma: no cover
    import importlib_metadata as metadata
else:  # pragma: no cover
    from importlib import metadata

if typing.TYPE_CHECKING:
    from speedwagon.job import Workflow

__all__ = [
    'find_plugin_workflows',
    'Plugin'
]


class AbsPluginFinder(abc.ABC):  # pylint: disable=too-few-public-methods
    @abc.abstractmethod
    def locate(self) -> Dict[str, Type[Workflow]]:
        """Locate plugin workflows."""


class EntrypointPluginSearch(AbsPluginFinder, abc.ABC):
    entrypoint_group = "speedwagon.plugins"

    def get_entry_points(self) -> metadata.EntryPoints:
        return metadata.entry_points(group=self.entrypoint_group)

    def load_workflows_from_entry_point(
            self, entry_point: metadata.EntryPoint
    ) -> Dict[str, Type[speedwagon.Workflow]]:
        entry_point_plugin = typing.cast(
            Type[speedwagon.Workflow], entry_point.load()
        )

        if not isinstance(entry_point_plugin, speedwagon.plugins.Plugin):
            raise speedwagon.exceptions.InvalidPlugin(
                f"{entry_point.value} is not a Speedwagon Plugin",
                entry_point=entry_point,
            )
        workflows: Dict[str, Type[Workflow]] = {
            workflow.name if workflow.name is not None else '': workflow
            for workflow in entry_point_plugin.workflows
        }
        return workflows

    @abc.abstractmethod
    def should_entrypoint_load(self, entrypoint: metadata.EntryPoint) -> bool:
        """Get if an entrypoint attempt to be loaded."""

    def locate(self) -> Dict[str, Type[Workflow]]:
        failed_plugins: List[str] = []
        discovered_plugins: Dict[str, Type[Workflow]] = {}
        for entrypoint in self.get_entry_points():
            if not self.should_entrypoint_load(entrypoint):
                continue
            try:
                result = self.load_workflows_from_entry_point(entrypoint)
                if result:
                    discovered_plugins = {**discovered_plugins, **result}
            except speedwagon.exceptions.InvalidPlugin as error:
                failed_plugins.append(error.entry_point.name)
        if failed_plugins:
            failed_plugins_string = ",".join(failed_plugins)
            message = f"{failed_plugins_string} failed to load"
            raise speedwagon.exceptions.PluginImportError(message)
        return discovered_plugins


class LoadAllPluginSearch(EntrypointPluginSearch):
    def should_entrypoint_load(self, entrypoint: metadata.EntryPoint) -> bool:
        return True


class LoadWhiteListedPluginsOnly(EntrypointPluginSearch):
    def __init__(self) -> None:
        self._whitelisted_entry_points: Set[Tuple[str, str]] = set()

    @property
    def whitelisted_entry_points(self) -> Set[Tuple[str, str]]:
        return self._whitelisted_entry_points

    @whitelisted_entry_points.setter
    def whitelisted_entry_points(
            self, value: Iterable[Tuple[str, str]]
    ) -> None:
        for item in value:
            if len(item) != 2:
                raise TypeError(
                    "whitelisted_entry_points include 2 parts: module & name"
                )
        self._whitelisted_entry_points = set(value)

    def should_entrypoint_load(self, entrypoint: metadata.EntryPoint) -> bool:
        return (
            entrypoint.module,
            entrypoint.name,
        ) in self.whitelisted_entry_points


def find_plugin_workflows(
        strategy: AbsPluginFinder = LoadAllPluginSearch(),
) -> Dict[str, Type[Workflow]]:
    """Locate all the plugin workflows."""
    return strategy.locate()


class Plugin:
    """Plugin class for registering components.

    This class is intended to be used by other packages.
    """

    def __init__(self) -> None:
        """Generate a new plugin object."""
        self._workflows: List[Type[Workflow]] = []

    def register_workflow(self, workflow_klass: Type[Workflow]) -> None:
        """Register a workflow to the plugin."""
        self._workflows.append(workflow_klass)

    @property
    def workflows(self) -> List[Type[Workflow]]:
        """Get workflows registered to this plugin."""
        return self._workflows
