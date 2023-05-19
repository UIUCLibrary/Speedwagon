"""Loading plugins for speedwagon."""

from __future__ import annotations
import abc
import typing
from typing import Type, Dict, Optional, Tuple, Set, Iterable

import sys
import speedwagon

if sys.version_info < (3, 10):  # pragma: no cover
    import importlib_metadata as metadata
else:  # pragma: no cover
    from importlib import metadata

if typing.TYPE_CHECKING:
    from speedwagon.job import Workflow

__all__ = [
    'find_plugin_workflows'
]


class AbsPluginFinder(abc.ABC):  # pylint: disable=too-few-public-methods
    @abc.abstractmethod
    def locate(self) -> Dict[str, Type[Workflow]]:
        """Locate plugin workflows."""


class EntrypointPluginSearch(AbsPluginFinder, abc.ABC):
    entrypoint_group = "speedwagon.plugins"

    def get_entry_points(self) -> metadata.EntryPoints:
        return metadata.entry_points(group=self.entrypoint_group)

    def load_workflow_from_entry_point(
            self, entry_point: metadata.EntryPoint
    ) -> Optional[Tuple[str, Type[speedwagon.Workflow]]]:
        entry_point_workflow = typing.cast(
            Type[speedwagon.Workflow], entry_point.load()
        )

        if not issubclass(entry_point_workflow, speedwagon.Workflow):
            raise speedwagon.exceptions.InvalidPlugin(
                f"{entry_point.value} is not a Speedwagon Workflow",
                entry_point=entry_point,
            )
        workflow_name: str = entry_point_workflow.name or entry_point.name
        return workflow_name, entry_point_workflow

    @abc.abstractmethod
    def should_entrypoint_load(self, entrypoint: metadata.EntryPoint) -> bool:
        """Get if an entrypoint attempt to be loaded."""

    def locate(self) -> Dict[str, Type[Workflow]]:
        failed_plugins = []
        discovered_plugins = {}
        for entrypoint in self.get_entry_points():
            if not self.should_entrypoint_load(entrypoint):
                continue
            try:
                result = self.load_workflow_from_entry_point(entrypoint)
                if result:
                    workflow_name, entry_point_workflow = result
                    discovered_plugins[workflow_name] = entry_point_workflow
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
