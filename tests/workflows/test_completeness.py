import os
from unittest.mock import Mock, MagicMock

import pytest

from speedwagon import tasks
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


def test_create_new_task_generates_subtask(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    mock_builder = Mock()
    job_args = {
        'package_path': "/some/source/package",
        'destination': "/some/destination",
        'check_ocr_data': False,
        '_check_ocr_utf8': False,
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
        tasks.Result(workflow_completeness.HathiCheckMissingPackageFilesTask, data=[]),
        tasks.Result(workflow_completeness.HathiManifestGenerationTask, data="Manifest"),
        tasks.Result(workflow_completeness.HathiCheckMissingComponentsTask, data=[]),
        tasks.Result(workflow_completeness.ValidateChecksumsTask, data=[]),
        tasks.Result(workflow_completeness.ValidateMarcTask, data=[]),
        tasks.Result(workflow_completeness.ValidateYMLTask, data=[]),
        tasks.Result(workflow_completeness.ValidateExtraSubdirectoriesTask, data=[]),
        tasks.Result(workflow_completeness.PackageNamingConventionTask, data=[]),
    ]
    message = workflow.generate_report(results, **job_args)
    assert "Report" in message


def test_missing_package_task_calls_validator(monkeypatch):
    package_path = "./sample_path/package1"

    task = workflow_completeness.HathiCheckMissingPackageFilesTask(
        package_path=package_path)
    task.log = Mock()
    mock_run_validation = MagicMock()
    from hathi_validate import process, validator
    with monkeypatch.context() as mp:
        mp.setattr(process, "run_validation", mock_run_validation)
        assert task.work() is True

    assert mock_run_validation.called is True and \
           mock_run_validation.call_args[0][0].path == package_path and \
           isinstance(mock_run_validation.call_args[0][0],
                      validator.ValidateMissingFiles)

checksum_results = [
    ([], None),
    (MagicMock(), None),
    ([], FileNotFoundError),
    ([], PermissionError),
]
@pytest.mark.parametrize("errors_found,throw_exception", checksum_results)
def test_hathi_missing_checksum_task_calls_validator(
        monkeypatch, errors_found, throw_exception):

    package_path = "./sample_path/package1"
    check_ocr = False
    task = workflow_completeness.HathiCheckMissingComponentsTask(
        check_ocr=check_ocr,
        package_path=package_path
    )

    task.log = Mock()
    mock_run_validation = MagicMock(return_value=errors_found)
    if throw_exception is not None:
        def exception_runner(*args, **kwargs):
            raise throw_exception
        mock_run_validation.side_effect = exception_runner
    from hathi_validate import process, validator
    with monkeypatch.context() as mp:
        mp.setattr(process, "run_validation", mock_run_validation)
        assert task.work() is (throw_exception is None)

    assert mock_run_validation.called is True and \
           mock_run_validation.call_args[0][0].path == package_path and \
           isinstance(mock_run_validation.call_args[0][0],
                      validator.ValidateComponents)
    assert all([a == b for a, b in zip(errors_found, task.results)])
