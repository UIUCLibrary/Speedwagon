import os
from unittest.mock import Mock

import pytest
from speedwagon.workflows import workflow_completeness


@pytest.mark.parametrize("index,label", [
    (0, "Source"),
    (1, "Check for page_data in meta.yml"),
    (2, "Check ALTO OCR xml files"),
    (3, "Check OCR xml files are utf-8"),
])
def test_completeness_workflow_options(index, label):
    workflow = workflow_completeness.CompletenessWorkflow()
    user_options = workflow.user_options()
    assert len(user_options) > 0
    assert user_options[index].label_text == label


def test_initial_task_creates_task():
    workflow = workflow_completeness.CompletenessWorkflow()
    user_args = {
        "Source": "./some_real_source_folder",
        "Check for page_data in meta.yml": False,
        "Check ALTO OCR xml files": False,
        "Check OCR xml files are utf-8": False
    }

    mock_builder = Mock()
    workflow.initial_task(
        task_builder=mock_builder,
        **user_args
    )
    assert \
        mock_builder.add_subtask.called is True and \
        mock_builder.add_subtask.call_args[1]['subtask'].batch_root == user_args['Source']

@pytest.fixture
def unconfigured_workflow():
    workflow = workflow = workflow_completeness.CompletenessWorkflow()
    user_options = {i.label_text: i.data for i in workflow.user_options()}

    return workflow, user_options


def test_discover_task_metadata_one_per_package(
        monkeypatch, unconfigured_workflow):

    workflow, user_options = unconfigured_workflow
    initial_results = []
    additional_data = {}
    number_of_fake_packages = 10
    def mock_scandir(path):
        for i_number in range(number_of_fake_packages):
            package_mock = Mock()
            package_mock.name = f"99423682{str(i_number).zfill(2)}2205899"
            package_mock.is_dir = Mock(return_value=True)
            yield package_mock

    monkeypatch.setattr(os, "scandir", mock_scandir)
    monkeypatch.setattr(os, "access", lambda *args: True)
    new_task_md = workflow.discover_task_metadata(
        initial_results=initial_results,
        additional_data=additional_data,
        **user_options
    )
    assert len(new_task_md) == number_of_fake_packages
