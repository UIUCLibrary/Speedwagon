import os
from unittest.mock import Mock, MagicMock

import pytest

import speedwagon
from speedwagon.frontend import interaction
from speedwagon.workflows import workflow_hathiprep


@pytest.mark.parametrize(
    "index,label",
    [
        (0, "input"),
        (1, "Image File Type"),
    ],
)
def test_workflow_options(index, label):
    workflow = workflow_hathiprep.HathiPrepWorkflow()
    user_options = workflow.job_options()
    assert len(user_options) > 0
    assert user_options[index].label == label


def test_initial_task_creates_task():
    workflow = workflow_hathiprep.HathiPrepWorkflow()
    user_args = {
        "input": "./some_real_source_folder",
        "Image File Type": "JPEG 2000",
    }

    mock_builder = Mock()
    workflow.initial_task(task_builder=mock_builder, **user_args)

    input_arg = user_args["input"]
    assert (
        mock_builder.add_subtask.called is True
        and mock_builder.add_subtask.call_args_list[0][0][0]._root == input_arg
    )


@pytest.fixture
def unconfigured_workflow():
    workflow = workflow_hathiprep.HathiPrepWorkflow()
    user_options = {i.label: i.value for i in workflow.job_options()}

    return workflow, user_options


def test_discover_task_metadata_one_per_package(
    monkeypatch, unconfigured_workflow
):

    workflow, user_options = unconfigured_workflow
    number_of_fake_packages = 10

    initial_results = []
    additional_data = {
        "packages": [MagicMock() for _ in range(number_of_fake_packages)]
    }

    new_task_md = workflow.discover_task_metadata(
        initial_results=initial_results,
        additional_data=additional_data,
        **user_options,
    )
    assert len(new_task_md) == number_of_fake_packages


def test_create_new_task_generates_subtask(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    mock_builder = Mock()
    job_args = {
        "package_id": "12345",
        "source_path": "/some/destination",
        "title_page": "12345-1234.tiff",
    }
    workflow.create_new_task(mock_builder, **job_args)
    assert mock_builder.add_subtask.called is True


def test_generate_report_creates_a_report(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    job_args = {}
    results = [
        speedwagon.tasks.Result(
            speedwagon.tasks.prep.GenerateChecksumTask,
            data={"package_id": "123"},
        ),
        speedwagon.tasks.Result(
            speedwagon.tasks.prep.MakeMetaYamlTask, data={"package_id": "123"}
        ),
    ]
    message = workflow.generate_report(results, **job_args)
    assert "Report" in message


def test_find_packages_task(monkeypatch):
    root_path = "some/sample/root"

    task = workflow_hathiprep.FindHathiPackagesTask(root=root_path)

    task.log = Mock()

    def mock_scandir(path):
        for i_number in range(20):
            file_mock = Mock()
            file_mock.name = f"99423682912205899-{str(i_number).zfill(8)}.xml"
            yield file_mock

    with monkeypatch.context() as mp:
        mp.setattr(os, "scandir", mock_scandir)
        assert task.work() is True
    assert len(task.results) == 20


def test_get_additional_info_packages(monkeypatch):
    workflow = workflow_hathiprep.HathiPrepWorkflow()
    user_args = {
        "input": "./some_real_source_folder",
        "Image File Type": "JPEG 2000",
    }

    def mock_scandir(path):
        for i_number in range(20):
            file_mock = Mock()
            file_mock.is_dir = Mock(return_value=True)
            file_mock.name = f"99423682912205899-{str(i_number).zfill(8)}"
            yield file_mock

    title_page_selection = pytest.importorskip(
        "speedwagon.frontend.qtwidgets.dialog.title_page_selection"
    )

    package_browser = Mock()
    package_browser.result = Mock(
        return_value=title_page_selection.PackageBrowser.Accepted
    )

    package_browser.Accepted = title_page_selection.PackageBrowser.Accepted

    with monkeypatch.context() as mp:
        mp.setattr(os, "scandir", mock_scandir)
        table_data_editor = Mock(name="table_data_editor")

        table_data_editor.get_user_response = Mock(
            return_value={"packages"}
        )

        user_request_factory = Mock(
            spec=interaction.UserRequestFactory,
        )
        user_request_factory.table_data_editor.return_value = (
            table_data_editor
        )

        extra_info = workflow.get_additional_info(
            user_request_factory, options=user_args, pretask_results=["something"]
        )
        assert "packages" in extra_info, '"packages" key not found in extra_info'
