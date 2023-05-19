from __future__ import annotations
from typing import Dict, Type
import typing
import importlib
import os
from unittest.mock import Mock
import sys

if sys.version_info < (3, 10):
    import importlib_metadata as metadata
else:
    from importlib import metadata

import pytest
import speedwagon
import speedwagon.plugins

if typing.TYPE_CHECKING:
    from speedwagon import Workflow


@pytest.fixture
def sample_plugins(monkeypatch):
    monkeypatch.syspath_prepend(
        os.path.join(os.path.dirname(__file__), "test_plugins")
    )
    return {
        "speedwagon-dummy": importlib.import_module(
            "speedwagon_dummy"
        ).MyWorkflow
    }


def test_load_plugins(sample_plugins):
    class LoadSamplePlugins(speedwagon.plugins.AbsPluginFinder):
        def locate(self) -> Dict[str, Type[Workflow]]:
            return {
                sample_plugins["speedwagon-dummy"].name: sample_plugins[
                    "speedwagon-dummy"
                ]
            }

    workflows = speedwagon.plugins.find_plugin_workflows(LoadSamplePlugins())
    assert workflows["My Workflow"].name == "My Workflow"


class TestLoadAllPluginSearch:
    def test_finding_nothing_returns_empty_dict(self, monkeypatch):
        finder = speedwagon.plugins.LoadAllPluginSearch()

        def get_entry_points(*_):
            return []

        monkeypatch.setattr(finder, "get_entry_points", get_entry_points)
        assert finder.locate() == {}

    def test_finding_dict(self, monkeypatch):
        class FakeWork:
            pass

        finder = speedwagon.plugins.LoadAllPluginSearch()

        def get_entry_points(*_):
            return [Mock(metadata.EntryPoint)]

        monkeypatch.setattr(finder, "get_entry_points", get_entry_points)

        monkeypatch.setattr(
            finder,
            "load_workflows_from_entry_point",
            lambda *_: {"dummy": FakeWork},
        )

        assert finder.locate() == {"dummy": FakeWork}

    def test_failed_throws_exception(self, monkeypatch):
        finder = speedwagon.plugins.LoadAllPluginSearch()

        def get_entry_points(*_):
            return [Mock(metadata.EntryPoint)]

        monkeypatch.setattr(finder, "get_entry_points", get_entry_points)

        def load_workflow_from_entry_point(entry_point):
            entry_point = Mock(metadata.EntryPoint)
            entry_point.name = "foo"
            raise speedwagon.exceptions.InvalidPlugin(
                "nope!", entry_point=entry_point
            )
            # finder.plugins_failed_to_import.append("spam")

        monkeypatch.setattr(
            finder,
            "load_workflows_from_entry_point",
            load_workflow_from_entry_point,
        )

        with pytest.raises(speedwagon.exceptions.PluginImportError):
            finder.locate()

    def test_load_workflow_from_entry_point(self, monkeypatch):
        finder = speedwagon.plugins.LoadAllPluginSearch()

        class FakeWorkflow(speedwagon.Workflow):
            name = "dummy"

        plugin = speedwagon.plugins.Plugin()
        plugin.register_workflow(FakeWorkflow)
        entry_point = Mock(
            metadata.EntryPoint, load=Mock(return_value=plugin)
        )
        res = finder.load_workflows_from_entry_point(entry_point)
        assert res['dummy'] == FakeWorkflow

    def test_load_workflow_from_entry_point_bad_data_raises_invalid_plugin_execption(
        self, monkeypatch
    ):
        finder = speedwagon.plugins.LoadAllPluginSearch()

        class InvalidWorkflow:
            name = "not subclassed from speedwagon.Workflow"

        entry_point = Mock(
            metadata.EntryPoint,
            value="dummy:badplugin",
            load=Mock(return_value=InvalidWorkflow),
        )
        with pytest.raises(speedwagon.exceptions.InvalidPlugin):
            finder.load_workflows_from_entry_point(entry_point)


class TestLoadActivePluginsOnly:
    def test_only_load_whitelisted(self, monkeypatch):
        class WhitelistedWorkflow(speedwagon.Workflow):
            name = "whitelisted"

        class BlacklistedWorkflow(speedwagon.Workflow):
            name = "blacklisted"

        def get_entry_points(*_):
            whitelisted_plugin_plugin = speedwagon.plugins.Plugin()
            whitelisted_plugin_plugin.register_workflow(WhitelistedWorkflow)
            white_listed_plugin = Mock(
                metadata.EntryPoint,
                module="myplugins",
                load=Mock(return_value=whitelisted_plugin_plugin),
            )
            white_listed_plugin.name = "whitelisted_workflow"
            blacklisted_plugin_plugin = speedwagon.plugins.Plugin()
            blacklisted_plugin_plugin.register_workflow(BlacklistedWorkflow)
            black_listed_plugin = Mock(
                metadata.EntryPoint,
                module="myplugins",
                load=Mock(return_value=blacklisted_plugin_plugin),
            )
            black_listed_plugin.name = "backlisted"

            return [white_listed_plugin, black_listed_plugin]

        plugin_loader = speedwagon.plugins.LoadWhiteListedPluginsOnly()
        monkeypatch.setattr(
            plugin_loader, "get_entry_points", get_entry_points
        )

        plugin_loader.whitelisted_entry_points = {
            ("myplugins", "whitelisted_workflow")
        }

        located = plugin_loader.locate()
        assert all(["whitelisted" in located, "blacklisted" not in located])


class TestLoadWhiteListedPluginsOnly:
    def test_setting_invalid_whitelist_format_raise_value_error(self):
        plugin_loader = speedwagon.plugins.LoadWhiteListedPluginsOnly()
        with pytest.raises(TypeError):
            plugin_loader.whitelisted_entry_points = "badvalue"
