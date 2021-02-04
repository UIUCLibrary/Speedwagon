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
            workflow = ht_wf.CaptureOneToDlCompoundWorkflow()
            workflow.validate_user_options(**options)
        assert \
            "Directory ./invalid_folder/ does not exist" in str(e.value) and \
            "Directory ./Other_folder/ does not exist" in str(e.value)
