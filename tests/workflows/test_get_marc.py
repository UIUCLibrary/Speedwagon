import os
from unittest.mock import MagicMock, Mock

import requests

from speedwagon.workflows import workflow_get_marc
from speedwagon import tasks
import pytest
import speedwagon.exceptions
from speedwagon.workflows.workflow_get_marc import MarcGeneratorTask


@pytest.fixture
def unconfigured_workflow():
    workflow = workflow_get_marc.GenerateMarcXMLFilesWorkflow(
        global_settings={
            "getmarc_server_url": "http://fake.com"
        }
    )
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
        workflow.validate_user_options(
            user_options={
                "Input": "Invalid path"
            }
        )


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
def test_task_creates_file(tmp_path, monkeypatch, identifier_type, identifier):
    expected_file = str(tmp_path / "MARC.XML")

    task = MarcGeneratorTask(
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

    def mock_log(message):
        """Empty log"""

    monkeypatch.setattr(task, 'log', mock_log)

    task.reflow_xml = Mock(return_value="")
    task.work()
    assert os.path.exists(task.results["output"]) is True


def test_missing_server_url_fails(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow

    if "getmarc_server_url" in workflow.global_settings:
        del workflow.global_settings["getmarc_server_url"]

    with pytest.raises(speedwagon.exceptions.MissingConfiguration):
        workflow.discover_task_metadata([], None, **user_options)


def test_generate_report_success(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    report = workflow.generate_report(
        results=[
            tasks.Result(None, data={
                "success": True,
                "identifier": "097"
            })
        ]
    )

    assert "Success" in report


def test_generate_report_failure(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    report = workflow.generate_report(
        results=[
            tasks.Result(None, data={
                "success": False,
                "identifier": "097",
                "output": "Something bad happened"
            })
        ]
    )

    assert "Warning" in report


@pytest.mark.parametrize("identifier_type,identifier", identifiers)
def test_task_logging__mentions_identifer(monkeypatch,
                                          identifier_type, identifier):

    task = MarcGeneratorTask(
        identifier=identifier,
        identifier_type=identifier_type,
        output_name="sample_record/MARC.xml",
        server_url="fake.com"

    )

    def mock_get(*args, **kwargs):
        result = Mock(text=f"/fakepath/{identifier}")
        result.raise_for_status = MagicMock(return_value=None)
        return result

    monkeypatch.setattr(requests, 'get', mock_get)

    logs = []

    def mock_log(message):
        logs.append(message)
    monkeypatch.setattr(task, 'log', mock_log)

    def mock_write_file(data):
        """Stub for writing files"""
    monkeypatch.setattr(task, 'write_file', mock_write_file)

    task.reflow_xml = Mock(return_value="")
    task.work()

    for log in logs:
        if identifier in log:
            break
    else:
        assert False, "Expected identifier \"{}\" mentioned in log, " \
                      "found [{}]".format(identifier, "] [".join(logs))


@pytest.mark.parametrize("identifier_type,identifier", identifiers)
def test_create_new_task(unconfigured_workflow, identifier_type, identifier):
    workflow, user_options = unconfigured_workflow
    job_args = {
        'identifier': {
            'value': identifier,
            'type': identifier_type
        },
        'api_server': "https://www.fake.com",
        'path': "/fake/path/to/item"
    }
    mock_task_builder = Mock()
    workflow.create_new_task(
        task_builder=mock_task_builder,
        **job_args
    )
    mock_task_builder.add_subtask.assert_called()
