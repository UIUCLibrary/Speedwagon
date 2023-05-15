import importlib
import sys
if sys.version_info < (3, 10):
    import importlib_metadata as metadata
else:
    from importlib import metadata

import os.path
from typing import Dict, Type
from unittest.mock import Mock, patch, mock_open, call
import json

import pytest

import speedwagon.job
from speedwagon import Workflow


def test_all_required_workflow_keys(monkeypatch):
    def mocked_workflows():
        return {
            "spam": Mock(required_settings_keys={"spam_setting"}),
            "bacon": Mock(required_settings_keys={"bacon_setting"}),
            "eggs": Mock(required_settings_keys=set()),
        }

    monkeypatch.setattr(
        speedwagon.job, "find_builtin_workflows", mocked_workflows
    )

    assert speedwagon.job.all_required_workflow_keys() == {
        "spam_setting", "bacon_setting"
    }


class TestWorkflowFinder:
    def test_no_module_error(self):
        finder = speedwagon.job.WorkflowFinder("fakepath")
        finder.logger.warning = Mock()
        all(finder.load("notavalidmodule"))
        assert finder.logger.warning.called is True
        finder.logger.warning.assert_called_with(
            "Unable to load notavalidmodule. "
            "Reason: No module named 'speedwagon.workflows.notavalidmodule'"
        )


class TestConfigJSONSerialize:
    def test_save_opens_file(self):
        serializer = speedwagon.job.ConfigJSONSerialize()
        file_output = "my_saves.json"
        serializer.file_name = file_output
        with patch('speedwagon.job.open', mock_open()) as file_opener:
            serializer.save(workflow_name="Spam", data={})
        assert \
            call(file_output, "w", encoding="utf-8") in file_opener.mock_calls

    def test_serialize(self):
        serialize_data = speedwagon.job.ConfigJSONSerialize().serialize_data(
            "Spam", data={
                "Input": os.path.join("some", "path")
            }
        )
        assert json.loads(serialize_data) == {
                'Workflow': "Spam",
                'Configuration': {
                    "Input": os.path.join("some", "path")
                }
            }

    @pytest.fixture
    def workflow_json_string(self):
        return \
            """{
                "Workflow": "Spam",
                "Configuration": {
                    "Input": "somepath"
                    }
                }
            """

    def test_open_file(self, workflow_json_string):
        serializer = speedwagon.job.ConfigJSONSerialize()
        serializer.file_name = "my_saves.json"

        with patch(
                'speedwagon.job.open',
                mock_open(read_data=workflow_json_string)
        ) as file_opener:
            file_opener.mock_add_spec("file", "mode")
            serializer.load()

        assert call(
            "my_saves.json",
            "r",
            encoding="utf-8"
        ) in file_opener.mock_calls

    def test_open_file_workflow_name(self, workflow_json_string):
        serializer = speedwagon.job.ConfigJSONSerialize()
        serializer.file_name = "my_saves.json"

        with patch(
                'speedwagon.job.open',
                mock_open(read_data=workflow_json_string)
        ) as file_opener:
            file_opener.mock_add_spec("file", "mode")
            name, data = serializer.load()
            assert name == "Spam"

    def test_save_missing_filename_throws(self):
        serializer = speedwagon.job.ConfigJSONSerialize()

        # NOTICE: no file was added
        # for example: serializer.file_name = "myfile.json"

        with pytest.raises(AssertionError):
            serializer.save("something", {})

    def test_loading_missing_filename_throws(self):
        serializer = speedwagon.job.ConfigJSONSerialize()

        # NOTICE: no file was added
        # for example: serializer.file_name = "myfile.json"

        with pytest.raises(AssertionError):
            serializer.load()


class TestJobConfigSerialization:

    @pytest.fixture()
    def mock_strategy(self):
        return Mock(
            spec=speedwagon.job.AbsJobConfigSerializationStrategy
        )

    def test_save(self, mock_strategy):

        serializer = speedwagon.job.JobConfigSerialization(
            strategy=mock_strategy
        )
        serializer.save("Spam Workflow", {})
        assert mock_strategy.save.called is True

    def test_load(self, mock_strategy):

        serializer = speedwagon.job.JobConfigSerialization(
            strategy=mock_strategy
        )
        serializer.load()
        assert mock_strategy.load.called is True


@pytest.fixture
def sample_plugins(monkeypatch):
    monkeypatch.syspath_prepend(os.path.join(os.path.dirname(__file__), "test_plugins"))
    return {
        'speedwagon-dummy': importlib.import_module('speedwagon_dummy').MyWorkflow
    }


def test_load_plugins(sample_plugins):

    class LoadSamplePlugins(speedwagon.job.AbsPluginFinder):

        def locate(self) -> Dict[str, Type[Workflow]]:
            return {
                sample_plugins['speedwagon-dummy'].name:
                    sample_plugins['speedwagon-dummy']
            }

    workflows = speedwagon.job.find_plugin_workflows(LoadSamplePlugins())
    assert workflows['My Workflow'].name == 'My Workflow'


class TestLoadAllPluginSearch:
    def test_finding_nothing_returns_empty_dict(self, monkeypatch):
        finder = speedwagon.job.LoadAllPluginSearch()
        def get_entry_points(*_):
            return []
        monkeypatch.setattr(finder, "get_entry_points", get_entry_points)
        assert finder.locate() == {}

    def test_finding_dict(self, monkeypatch):
        class FakeWork:
            pass
        finder = speedwagon.job.LoadAllPluginSearch()
        def get_entry_points(*_):
            return [
                Mock(metadata.EntryPoint)
            ]
        monkeypatch.setattr(finder, "get_entry_points", get_entry_points)

        monkeypatch.setattr(
            finder,
            "load_workflow_from_entry_point",
            lambda *_: ("dummy", FakeWork)
        )

        assert finder.locate() == {"dummy": FakeWork}

    def test_failed_throws_exception(self, monkeypatch):
        finder = speedwagon.job.LoadAllPluginSearch()
        def get_entry_points(*_):
            return [
                Mock(metadata.EntryPoint)
            ]
        monkeypatch.setattr(finder, "get_entry_points", get_entry_points)

        def load_workflow_from_entry_point(entry_point):
            entry_point = Mock(metadata.EntryPoint)
            entry_point.name = "foo"
            raise speedwagon.exceptions.InvalidPlugin("nope!", entry_point=entry_point)
            # finder.plugins_failed_to_import.append("spam")

        monkeypatch.setattr(
            finder, "load_workflow_from_entry_point",
            load_workflow_from_entry_point
        )

        with pytest.raises(speedwagon.exceptions.PluginImportError):
            finder.locate()

    def test_load_workflow_from_entry_point(self, monkeypatch):
        finder = speedwagon.job.LoadAllPluginSearch()
        class FakeWorkflow(speedwagon.Workflow):
            name = "dummy"

        entry_point = Mock(metadata.EntryPoint, load=Mock(return_value=FakeWorkflow))
        res = finder.load_workflow_from_entry_point(entry_point)
        assert res[1] == FakeWorkflow

    def test_load_workflow_from_entry_point_bad_data_raises_invalid_plugin_execption(self, monkeypatch):
        finder = speedwagon.job.LoadAllPluginSearch()
        class InvalidWorkflow:
            name = "not subclassed from speedwagon.Workflow"

        entry_point = Mock(
            metadata.EntryPoint,
            value="dummy:badplugin",
            load=Mock(return_value=InvalidWorkflow)
        )
        with pytest.raises(speedwagon.exceptions.InvalidPlugin):
            finder.load_workflow_from_entry_point(entry_point)


class TestLoadActivePluginsOnly:
    def test_only_load_whitelisted(self, monkeypatch):
        class WhitelistedWorkflow(speedwagon.Workflow):
            name = "whitelisted"

        class BlacklistedWorkflow(speedwagon.Workflow):
            name = "blacklisted"

        def get_entry_points(*_):
            white_listed_plugin = Mock(
                metadata.EntryPoint,
                module="myplugins",
                load=Mock(return_value=WhitelistedWorkflow)
            )
            white_listed_plugin.name = "whitelisted_workflow"

            black_listed_plugin = Mock(
                metadata.EntryPoint,
                module="myplugins",
                load=Mock(return_value=BlacklistedWorkflow)
            )
            black_listed_plugin.name = "backlisted"

            return [
                white_listed_plugin,
                black_listed_plugin
            ]

        plugin_loader = speedwagon.job.LoadWhiteListedPluginsOnly()
        monkeypatch.setattr(plugin_loader, "get_entry_points", get_entry_points)

        plugin_loader.whitelisted_entry_points = {
            ('myplugins', 'whitelisted_workflow')
        }

        located = plugin_loader.locate()
        assert all(['whitelisted' in located, 'blacklisted' not in located])


class TestLoadWhiteListedPluginsOnly:
    def test_setting_invalid_whitelist_format_raise_value_error(self):
        plugin_loader = speedwagon.job.LoadWhiteListedPluginsOnly()
        with pytest.raises(TypeError):
            plugin_loader.whitelisted_entry_points = "badvalue"