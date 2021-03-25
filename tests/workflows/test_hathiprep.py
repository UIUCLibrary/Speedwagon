import os
from unittest.mock import Mock, MagicMock

import pytest

from speedwagon import tasks
from speedwagon.workflows import workflow_hathiprep


@pytest.mark.parametrize("index,label", [
    (0, "input"),
    (1, "Image File Type"),
])
def test_workflow_options(index, label):
    workflow = workflow_hathiprep.HathiPrepWorkflow()
    user_options = workflow.user_options()
    assert len(user_options) > 0
    assert user_options[index].label_text == label


def test_initial_task_creates_task():
    workflow = workflow_hathiprep.HathiPrepWorkflow()
    user_args = {
        "input": "./some_real_source_folder",
        "Image File Type": "JPEG 2000",
    }

    mock_builder = Mock()
    workflow.initial_task(
        task_builder=mock_builder,
        **user_args
    )
    assert \
        mock_builder.add_subtask.called is True and \
        mock_builder.add_subtask.call_args_list[0][0][0]._root == user_args['input']


def test_get_additional_info_opens_dialog_box(monkeypatch):
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

    from speedwagon.workflows.title_page_selection import PackageBrowser
    package_browser = Mock()
    package_browser.result = Mock(return_value=PackageBrowser.Accepted)
    package_browser.Accepted = PackageBrowser.Accepted


    def mock_package_browser(packages, parent):
        return package_browser
    with monkeypatch.context() as mp:
        mp.setattr(os, "scandir", mock_scandir)
        mp.setattr(
            workflow_hathiprep,
            "PackageBrowser",
            mock_package_browser
        )

        extra_info = workflow.get_additional_info(
            None,
            options=user_args,
            pretask_results=[]
        )
    assert package_browser.exec.called is True and \
           "packages" in extra_info


@pytest.fixture
def unconfigured_workflow():
    workflow = workflow = workflow_hathiprep.HathiPrepWorkflow()
    user_options = {i.label_text: i.data for i in workflow.user_options()}

    return workflow, user_options


def test_discover_task_metadata_one_per_package(
        monkeypatch, unconfigured_workflow):

    workflow, user_options = unconfigured_workflow
    number_of_fake_packages = 10

    initial_results = []
    additional_data = {
        "packages": [MagicMock() for _ in range(number_of_fake_packages)]
    }

    new_task_md = workflow.discover_task_metadata(
        initial_results=initial_results,
        additional_data=additional_data,
        **user_options
    )
    assert len(new_task_md) == number_of_fake_packages


def test_create_new_task_generates_subtask(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    mock_builder = Mock()
    job_args = {
        'package_id': "12345",
        'source_path': "/some/destination",
        'title_page': '12345-1234.tiff',
    }
    workflow.create_new_task(
        mock_builder,
        **job_args
    )
    assert mock_builder.add_subtask.called is True


def test_generate_report_creates_a_report(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    job_args = {}
    results = [
        tasks.Result(
            workflow_hathiprep.GenerateChecksumTask,
            data={"package_id": "123"}
        ),
        tasks.Result(
            workflow_hathiprep.MakeYamlTask,
            data={"package_id": "123"}
        ),
    ]
    message = workflow.generate_report(results, **job_args)
    assert "Report" in message


def test_find_packages_task(monkeypatch):
    root_path = "some/sample/root"

    task = workflow_hathiprep.FindPackagesTask(root=root_path)

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


def test_make_yaml_task_calls_make_yaml(monkeypatch):
    root_path = "some/sample/root"

    task = workflow_hathiprep.MakeYamlTask(
        package_id="1234",
        source=root_path,
        title_page="1234-0001.tif"
    )

    task.log = Mock()
    mock_package_builder = MagicMock()

    def mock_inplace_package(*args, **kwargs):
        return mock_package_builder

    from pyhathiprep import package_creater
    import shutil
    with monkeypatch.context() as mp:
        mp.setattr(package_creater, "InplacePackage", mock_inplace_package)
        mp.setattr(os, "makedirs", lambda x: None)
        mp.setattr(os.path, "exists", lambda x: True)
        mp.setattr(shutil, "move", lambda source, dest: True)
        assert task.work() is True
    assert mock_package_builder.make_yaml.called is True


def test_generate_checksum_task_task_calls_create_checksum_report(monkeypatch):
    root_path = "some/sample/root"

    task = workflow_hathiprep.GenerateChecksumTask(
        package_id="1234",
        source=root_path,
    )

    task.log = Mock()
    mock_package_builder = MagicMock()

    def mock_inplace_package(*args, **kwargs):
        return mock_package_builder

    from pyhathiprep import package_creater
    import shutil
    with monkeypatch.context() as mp:
        mp.setattr(package_creater, "InplacePackage", mock_inplace_package)
        mp.setattr(os, "makedirs", lambda x: None)
        mp.setattr(os.path, "exists", lambda x: True)
        mp.setattr(shutil, "move", lambda source, dest: True)
        assert task.work() is True
    assert mock_package_builder.create_checksum_report.called is True


def test_prep_task_task_calls_generate_package(monkeypatch):
    root_path = "some/sample/root"

    task = workflow_hathiprep.PrepTask(
        source=root_path,
        title_page="1234-0001.tif"
    )

    task.log = Mock()
    mock_package_builder = MagicMock()

    def mock_inplace_package(*args, **kwargs):
        return mock_package_builder

    from pyhathiprep import package_creater
    with monkeypatch.context() as mp:
        mp.setattr(package_creater, "InplacePackage", mock_inplace_package)
        assert task.work() is True
    assert mock_package_builder.generate_package.called is True
