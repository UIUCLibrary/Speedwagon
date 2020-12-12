import os
from unittest.mock import MagicMock, Mock

import requests

from speedwagon.workflows import workflow_get_marc
import pytest

from speedwagon.workflows.workflow_get_marc import MarcGenerator2Task


@pytest.fixture
def unconfigured_workflow():
    workflow = workflow_get_marc.GenerateMarcXMLFilesWorkflow()
    user_options = {i.label_text: i.data for i in workflow.user_options()}
    return workflow, user_options


def test_input_dir_is_valid(tmp_path, unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    test_pkg = tmp_path / "4717"
    test_pkg.mkdir()

    user_options["Input"] = str(test_pkg.resolve())
    user_options["Identifier type"] = "MMS ID"
    workflow.validate_user_options(**user_options)


def test_invalid_input_dir_raises(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    with pytest.raises(ValueError):
        workflow.validate_user_options(Input="Invalid path")


def test_discover_metadata(unconfigured_workflow, monkeypatch):

    workflow, user_options = unconfigured_workflow
    user_options["Identifier type"] = "MMS ID"
    workflow.filter_bib_id_folders = Mock(return_value=True)

    def get_data(*args, **kwargs):
        # name attribute can't be mocked in the constructor for Mock
        first = Mock(path="/fakepath/99101026212205899")
        first.name = "99101026212205899"

        second = Mock(path="/fakepath/99954806053105899")
        second.name = "99954806053105899"

        return [first, second]


    monkeypatch.setattr(os, 'scandir', get_data)
    workflow.global_settings["getmarc_server_url"] = "http://fake.com"
    user_options["Input"] = "/fakepath"
    jobs = workflow.discover_task_metadata([], None, **user_options)
    assert len(jobs) == 2
    assert jobs[0]['path'] == "/fakepath/99101026212205899"
    assert jobs[0]['identifier']['value'] == "99101026212205899"


identifiers = [
    ("MMS ID", "99954806053105899"),
    ("MMS ID", "99101026212205899"),
    ("Bibid", "100")
]


@pytest.mark.parametrize("identifier_type,identifier", identifiers)
def test_task_creates_file(tmp_path, monkeypatch,identifier_type, identifier):
    expected_file = tmp_path / "MARC.XML"

    task = MarcGenerator2Task(
        identifier=identifier,
        identifier_type=identifier_type,
        output_name=expected_file,
        server_url="fake.com"

    )

    def mock_get(*args, **kwargs):
        result = Mock(text=f"/fakepath/{identifier}")
        result.raise_for_status = MagicMock(return_value=None)
        return result
    monkeypatch.setattr(requests, 'get', mock_get)
    task.reflow_xml = Mock(return_value="")
    task.work()
    assert os.path.exists(task.results["output"]) is True


