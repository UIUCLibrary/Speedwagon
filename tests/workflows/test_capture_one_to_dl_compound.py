import warnings
from unittest.mock import MagicMock, Mock

import pytest

import speedwagon
import speedwagon.validators
from speedwagon.workflows import workflow_capture_one_to_dl_compound as ht_wf
import os.path

import uiucprescon.packager.packages


def test_option_validate_output_false(monkeypatch):
    user_data = {
        "Input": "dummy",
        "Output": "spam"
    }
    option_validators = speedwagon.validators.OptionValidator()
    option_validators.register_validator(
        'Output',
        speedwagon.validators.DirectoryValidation(key="Output")
    )
    input_validator = option_validators.get('Output')
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    assert input_validator.is_valid(**user_data) is False


def test_option_validate_output(monkeypatch):
    user_data = {
        "Input": "dummy",
        "Output": "spam"
    }
    option_validators = speedwagon.validators.OptionValidator()
    option_validators.register_validator(
        'Output', speedwagon.validators.DirectoryValidation(key="Output")
    )
    input_validator = option_validators.get('Output')

    monkeypatch.setattr(os.path, "exists", lambda p: True)
    assert input_validator.is_valid(**user_data) is True


def test_valid_option_explanation_is_ok(monkeypatch):
    option_validators = speedwagon.validators.OptionValidator()

    my_validator = \
        speedwagon.validators.DirectoryValidation(key="Output")

    my_validator.is_valid = MagicMock(return_value=True)

    option_validators.register_validator('Output', my_validator)

    input_validator = option_validators.get('Output')
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    assert input_validator.explanation(Input="dummy", Output="spam") == "ok"


def test_output_must_exist(monkeypatch):
    options = {
        "Input": "./valid",
        "Output": "./invalid_folder/"
    }

    def mock_exists(path):
        if path == options["Output"]:
            return False
        else:
            return True
    with monkeypatch.context() as mp:
        mp.setattr(os.path, "exists", mock_exists)
        with pytest.raises(ValueError) as e:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                workflow = ht_wf.CaptureOneToDlCompoundWorkflow()
            workflow.validate_user_options(**options)

            assert "Directory ./invalid_folder/ does not exist" in str(e.value)


def test_input_must_exist(monkeypatch):
    options = {
        "Input": "./invalid_folder",
        "Output": "./valid/"
    }

    def mock_exists(path):
        if path == options["Input"]:
            return False
        else:
            return True
    with monkeypatch.context() as mp:
        mp.setattr(os.path, "exists", mock_exists)
        with pytest.raises(ValueError) as e:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                workflow = ht_wf.CaptureOneToDlCompoundWorkflow()
            workflow.validate_user_options(**options)
            assert "Directory ./invalid_folder/ does not exist" in str(e.value)


def test_input_and_out_invalid_produces_errors_with_both(monkeypatch):
    options = {
        "Input": "./invalid_folder/",
        "Output": "./Other_folder/"
    }

    def mock_exists(path):
        return False

    with monkeypatch.context() as mp:
        mp.setattr(os.path, "exists", mock_exists)
        with pytest.raises(ValueError) as e:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                workflow = ht_wf.CaptureOneToDlCompoundWorkflow()
            workflow.validate_user_options(**options)
        message = str(e.value)
        assert \
            'Directory "./invalid_folder/" does not exist' in message and \
            'Directory "./Other_folder/" does not exist' in message


def test_discover_task_metadata(monkeypatch):
    additional_data = {}
    initial_results = []
    user_args = {
        "Input": "./some_real_source_folder",
        "Output": "./some_real_folder/",
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        workflow = ht_wf.CaptureOneToDlCompoundWorkflow()

    def mock_exists(path):
        if path == user_args["Input"]:
            return True
        else:
            return False

    def mock_scandir(path):
        for i_number in range(20):
            file_mock = MagicMock()
            # file_mock = Mock()
            file_mock.name = f"99423682912205899-{str(i_number).zfill(8)}.tif"
            file_mock.path = path
            # file_mock.is_file.return_value=True
            yield file_mock

    with monkeypatch.context() as mp:
        mp.setattr(os.path, "exists", mock_exists)

        mp.setattr(
            uiucprescon.packager.packages.capture_one_package.os,
            "scandir",
            mock_scandir
        )

        new_task_metadata = workflow.discover_task_metadata(
            initial_results=initial_results,
            additional_data=additional_data,
            **user_args
        )

    assert len(new_task_metadata) == 1
    md = new_task_metadata[0]
    assert \
        md['output'] == user_args['Output'] and \
        md['source_path'] == user_args['Input']


def test_create_new_task_dl(monkeypatch):
    task_builder = speedwagon.tasks.TaskBuilder(
        speedwagon.tasks.MultiStageTaskBuilder("."),
        "."
    )
    mock_package = MagicMock()
    mock_package.metadata = MagicMock()
    job_args = {
        'package': mock_package,
        "output": "./some_real_dl_folder/",
        "source_path": "./some_real_source_folder/",
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        workflow = ht_wf.CaptureOneToDlCompoundWorkflow()
    workflow.create_new_task(task_builder, **job_args)
    task_built = task_builder.build_task()
    assert len(task_built.subtasks) == 1
    assert task_built.subtasks[0].source_path == job_args['source_path']


def test_package_converter(tmpdir):
    output_ht = tmpdir / "ht"
    output_ht.ensure_dir()

    mock_source_package = MagicMock()
    options = {
        "source_path": "./some_real_source_folder",
        "packaging_id": "99423682912205899",
        "existing_package": mock_source_package,
        "new_package_root": "./some_real_folder/",
    }

    new_task = ht_wf.PackageConverter(**options)
    new_task.log = MagicMock()
    new_task.package_factory = MagicMock()
    new_task.package_factory.transform = MagicMock()
    new_task.work()
    new_task.package_factory.transform.assert_called_with(
        mock_source_package,
        dest=options['new_package_root']
    )


def test_tasks_have_description():
    task = ht_wf.PackageConverter(
        source_path="some_source_path",
        packaging_id="123",
        existing_package=Mock(),
        new_package_root="some_root"
    )
    assert task.task_description() is not None
