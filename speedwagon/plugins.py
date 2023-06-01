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
    from speedwagon.tasks.system import AbsSystemTask

__all__ = [
    'find_plugin_workflows',
    'Plugin'
]


class AbsPluginFinder(abc.ABC):  # pylint: disable=too-few-public-methods
    @abc.abstractmethod
    def locate(self) -> Iterable[Plugin]:
        """Locate the plugins."""


class EntrypointPluginSearch(AbsPluginFinder, abc.ABC):
    entrypoint_group = "speedwagon.plugins"

    def get_entry_points(self) -> metadata.EntryPoints:
        return metadata.entry_points(group=self.entrypoint_group)

    @staticmethod
    def get_workflows_from_plugin(plugin: Plugin) -> Dict[str, Type[Workflow]]:
        workflows: Dict[str, Type[Workflow]] = {
            workflow.name if workflow.name is not None else '': workflow
            for workflow in plugin.workflows
        }
        return workflows

    @staticmethod
    def get_plugin_from_entry_point(
            entry_point: metadata.EntryPoint
    ) -> Plugin:
        entry_point_plugin = typing.cast(
            Type[speedwagon.plugins.Plugin], entry_point.load()
        )
        if not isinstance(entry_point_plugin, speedwagon.plugins.Plugin):
            raise speedwagon.exceptions.InvalidPlugin(
                f"{entry_point.value} is not a Speedwagon Plugin",
                entry_point=entry_point,
            )
        return entry_point_plugin

    def load_workflows_from_entry_point(
            self, entry_point: metadata.EntryPoint
    ) -> Dict[str, Type[speedwagon.Workflow]]:
        entry_point_plugin = self.get_plugin_from_entry_point(entry_point)
        return self.get_workflows_from_plugin(entry_point_plugin)

    @abc.abstractmethod
    def should_entrypoint_load(self, entrypoint: metadata.EntryPoint) -> bool:
        """Get if an entrypoint attempt to be loaded."""

    def _iter_entry_points(self) -> Iterable[metadata.EntryPoint]:
        return [
            entrypoint
            for entrypoint in self.get_entry_points()
            if self.should_entrypoint_load(entrypoint)
        ]

    def locate(self) -> Iterable[Plugin]:
        plugins: List[Plugin] = []
        failed: List[str] = []
        for entrypoint in self._iter_entry_points():
            try:
                plugins.append(self.get_plugin_from_entry_point(entrypoint))
            except speedwagon.exceptions.InvalidPlugin:
                failed.append(entrypoint.value)
        if failed:
            raise speedwagon.exceptions.PluginImportError
        return plugins


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
    workflows: Dict[str, Type[Workflow]] = {}
    for plugin in strategy.locate():
        for workflow in plugin.workflows:
            plugin_name = workflow.name if workflow.name is not None else ''
            workflows[plugin_name] = workflow
    return workflows


class Plugin:
    """Plugin class for registering components.

    This class is intended to be used by other packages.
    """

    def __init__(self) -> None:
        """Generate a new plugin object."""
        self._workflows: List[Type[Workflow]] = []
        self._init_steps: List[AbsSystemTask] = []

    def register_workflow(self, workflow_klass: Type[Workflow]) -> None:
        """Register a workflow to the plugin."""
        self._workflows.append(workflow_klass)

    def register_plugin_startup_task(self, task: AbsSystemTask) -> None:
        """Register a task to run during the plugin's initialization."""
        self._init_steps.append(task)

    @property
    def workflows(self) -> List[Type[Workflow]]:
        """Get workflows registered to this plugin."""
        return self._workflows

    @property
    def plugin_init_tasks(self) -> List[AbsSystemTask]:
        """Get initializing tasks registered to this plugin."""
        return self._init_steps
