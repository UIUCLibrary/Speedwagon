import logging
from unittest.mock import MagicMock

import pytest

import speedwagon.validators
from speedwagon.workflows import workflow_capture_one_to_dl_compound as ht_wf
import os.path


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


def test_output_must_exist(tmpdir):
    temp_dir = tmpdir / "temp"
    temp_dir.mkdir()
    with pytest.raises(ValueError) as e:
        workflow = ht_wf.CaptureOneToDlCompoundWorkflow()
        workflow.validate_user_options(Input=temp_dir.realpath(),
                                       Output="./invalid_folder/")

    assert "Directory ./invalid_folder/ does not exist" in str(e.value)


def test_input_must_exist(tmpdir):
    temp_dir = tmpdir / "temp"
    temp_dir.mkdir()
    with pytest.raises(ValueError) as e:
        workflow = ht_wf.CaptureOneToDlCompoundWorkflow()
        workflow.validate_user_options(Input="./invalid_folder/",
                                       Output=temp_dir.realpath())
    assert "Directory ./invalid_folder/ does not exist" in str(e.value)


def test_input_and_out_invalid_produces_errors_with_both(tmpdir):
    temp_dir = tmpdir / "temp"
    temp_dir.mkdir()
    with pytest.raises(ValueError) as e:
        workflow = ht_wf.CaptureOneToDlCompoundWorkflow()
        workflow.validate_user_options(Input="./invalid_folder/",
                                       Output="./Other_folder/")
    assert \
        "Directory ./invalid_folder/ does not exist" in str(e.value) and \
        "Directory ./Other_folder/ does not exist" in str(e.value)

# =======

# def test_compound_run(tool_job_manager_spy, monkeypatch, caplog, tmpdir):
#     class MockWorkflow(ht_wf.CaptureOneToDlCompoundWorkflow):
#         pass
#
#     options = {
#         "Input": "/Users/hborcher/PycharmProjects/UIUCLibrary/Speedwagon/sample_data/package test data/package/DS_2021_01_25_dg",
#         "Output": "/Users/hborcher/PycharmProjects/UIUCLibrary/Speedwagon/sample_data/out",
#     }
#     my_logger = logging.getLogger(__file__)
#     tool_job_manager_spy.run(None,
#                              MockWorkflow(),
#                              options=options,
#                              logger=my_logger)
#
