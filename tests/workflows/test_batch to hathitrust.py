import sys
from unittest.mock import Mock, MagicMock

import pytest

from speedwagon import tasks
from speedwagon.workflows import workflow_batch_to_HathiTrust_TIFF as wf
from speedwagon.workflows import workflow_get_marc
import os
import speedwagon.workflows.title_page_selection
from uiucprescon.packager.common import Metadata as PackageMetadata

@pytest.mark.parametrize("index,label", [
    (0, "Source"),
    (1, "Destination")
])
def test_hathi_limited_to_dl_compound_has_options(index, label):
    workflow = wf.CaptureOneBatchToHathiComplete()
    user_options = workflow.user_options()
    assert len(user_options) > 0
    assert user_options[index].label_text == label


def test_initial_task_creates_task():
    workflow = wf.CaptureOneBatchToHathiComplete()
    user_args = {
        "Source": "./some_real_source_folder",
        "Destination": "./some_real_folder/",
    }

    mock_builder = Mock()
    workflow.initial_task(
        task_builder=mock_builder,
        **user_args
    )
    assert \
        mock_builder.add_subtask.called is True and \
        mock_builder.add_subtask.call_args[0][0]._root == user_args['Source']


def test_initial_task(monkeypatch):
    workflow = wf.CaptureOneBatchToHathiComplete()
    user_args = {
        "Source": "./some_real_source_folder",
        "Destination": "./some_real_folder/",
    }

    mock_builder = Mock()
    workflow.initial_task(
        task_builder=mock_builder,
        **user_args
    )
    created_task = mock_builder.add_subtask.call_args[0][0]
    created_task.log = Mock()

    number_of_fake_files = 20

    def mock_scandir(path):
        for i_number in range(number_of_fake_files):
            file_mock = Mock()
            file_mock.name = f"99423682912205899_{str(i_number).zfill(8)}.tif"
            yield file_mock

    with monkeypatch.context() as mp:
        mp.setattr(os, "scandir", mock_scandir)
        created_task.work()
    assert len(created_task.results) == 1 and \
           len(created_task.results[0].items) == number_of_fake_files


def test_package_browser(qtbot):
    mock_package = MagicMock()

    def mock_get_item(obj, key):
        return {
            "ID": "99423682912205899",
            "ITEM_NAME": "",
            "TITLE_PAGE": "99423682912205899_0001.tif",
            "PATH": "/some/random/path/"
        }.get(key.name, str(key))

    mock_package.metadata.__getitem__ = mock_get_item
    mock_package.__len__ = lambda x: 1

    widget = speedwagon.workflows.title_page_selection.PackageBrowser([mock_package],
                                                             None)
    with qtbot.waitSignal(widget.finished) as blocker:
        widget.ok_button.click()
    data = widget.data()

    assert data[0].metadata[PackageMetadata.TITLE_PAGE] == \
           "99423682912205899_0001.tif"


def test_get_additional_info(qtbot, monkeypatch):
    workflow = wf.CaptureOneBatchToHathiComplete()
    mock_package = MagicMock()
    mock_data = {
            "ID": "99423682912205899",
            "ITEM_NAME": "",
            "TITLE_PAGE": "99423682912205899_0001.tif",
            "PATH": "/some/random/path/"
            }
    def mock_get_item(obj, key):
        return mock_data.get(key.name, str(key))

    mock_package.metadata.__getitem__ = mock_get_item
    mock_package.__len__ = lambda x: 1

    pretask_result = tasks.Result(
        source=wf.FindPackageTask,
        data=[mock_package]
    )

    def patched_package_browser(packages, parent):
        patched_browser = speedwagon.workflows.title_page_selection.PackageBrowser(packages, parent)
        patched_browser.exec = Mock()
        patched_browser.result = Mock(return_value=patched_browser.Accepted)
        data = MagicMock()
        data.metadata = MagicMock()

        data.metadata.__getitem__ = \
            lambda _, k: mock_data.get(k.name, str(k))

        patched_browser.data = Mock(return_value=[data])
        return patched_browser

    with monkeypatch.context() as mp:
        mp.setattr(wf, "PackageBrowser", patched_package_browser)

        extra_data = workflow.get_additional_info(
            parent=None,
            options={},
            pretask_results=[pretask_result]
        )

    assert extra_data['title_pages']['99423682912205899'] == "99423682912205899_0001.tif"
    assert isinstance(extra_data, dict)

@pytest.fixture
def unconfigured_workflow():
    workflow = wf.CaptureOneBatchToHathiComplete(
        global_settings={
            "getmarc_server_url": "http://fake.com"
        }
    )
    user_options = {i.label_text: i.data for i in workflow.user_options()}

    return workflow, user_options


def test_discover_task_metadata(monkeypatch, unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    additional_data = {
        'title_pages': {
            '99423682912205899': "99423682912205899_0001.tif"
        }
    }
    initial_results = [
        tasks.Result(
            wf.FindPackageTask,
            data=[
                Mock(
                    metadata={
                        PackageMetadata.ID: "99423682912205899",
                    }
                )
            ]
        )
    ]
    user_args = {
        "Source": "./some_real_source_folder",
        "Destination": "./some_real_folder/",
    }

    with monkeypatch.context() as mp:
        new_task_metadata = workflow.discover_task_metadata(
            initial_results=initial_results,
            additional_data=additional_data,
            **user_args
        )

    assert \
        len(new_task_metadata) == 1 and \
        new_task_metadata[0]['title_page'] == "99423682912205899_0001.tif" and \
        new_task_metadata[0]['server_url'] == "http://fake.com"


def test_create_new_task(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    mock_builder = Mock()
    job_args = {
        'package': Mock(metadata={PackageMetadata.ID: "99423682912205899"}),
        'destination': "/some/destination",
        'title_page': "99423682912205899_0001.tif",
        'server_url': "http://fake.com"
    }
    workflow.create_new_task(
        mock_builder,
        **job_args
    )
    assert mock_builder.add_subtask.called is True and \
           mock_builder.add_subtask.call_count == 4

    assert \
        isinstance(
            mock_builder.add_subtask.mock_calls[0][2]['subtask'],
            wf.TransformPackageTask
        ) and \
        isinstance(
            mock_builder.add_subtask.mock_calls[1][2]['subtask'],
            workflow_get_marc.MarcGeneratorTask
        ) and \
        isinstance(
            mock_builder.add_subtask.mock_calls[2][2]['subtask'],
            wf.MakeYamlTask
        ) and \
        isinstance(
            mock_builder.add_subtask.mock_calls[3][2]['subtask'],
            wf.GenerateChecksumTask
        )


def test_create_new_task_marc(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    mock_builder = Mock()
    job_args = {
        'package': Mock(metadata={PackageMetadata.ID: "99423682912205899"}),
        'destination': os.path.join("some", "destination"),
        'title_page': "99423682912205899_0001.tif",
        "server_url": "http://fake.com"
    }
    workflow.create_new_task(
        mock_builder,
        **job_args
    )

    marc_task = mock_builder.add_subtask.mock_calls[1][2]['subtask']
    assert isinstance(marc_task, workflow_get_marc.MarcGeneratorTask) and \
           marc_task._identifier == '99423682912205899' and \
           marc_task._output_name == os.path.join("some", "destination", "99423682912205899", "MARC.xml") and \
           marc_task._server_url == "http://fake.com"

           # marc_task._output_name == os.path.join("/some/destination/99423682912205899/MARC.xml") and \
