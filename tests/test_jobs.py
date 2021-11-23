import os.path
from unittest.mock import Mock, patch, mock_open, call
import json

import pytest

import speedwagon.job


def test_all_required_workflow_keys(monkeypatch):
    def mocked_workflows():
        return {
            "spam": Mock(required_settings_keys={"spam_setting"}),
            "bacon": Mock(required_settings_keys={"bacon_setting"}),
            "eggs": Mock(required_settings_keys=set()),
        }

    monkeypatch.setattr(
        speedwagon.job, "available_workflows", mocked_workflows
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
        assert call(file_output, "w") in file_opener.mock_calls

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

        assert call("my_saves.json", "r") in file_opener.mock_calls

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

