import logging
import os
from unittest.mock import Mock

import pytest

from speedwagon import utils, validators
from speedwagon.workflow import TextLineEditData
import pathlib


def test_get_desktop_path_finds_valid(monkeypatch):
    fake_home = os.path.join("usr", "home")
    monkeypatch.setattr(
        pathlib.Path, "home", lambda: pathlib.Path(fake_home)
    )

    def exists(path):
        return str(path) == os.path.join(fake_home, "Desktop")

    monkeypatch.setattr(os.path, "exists", exists)
    assert utils.get_desktop_path()


def test_get_desktop_path_not_found_throws(monkeypatch):
    fake_home = os.path.join("usr", "home")

    monkeypatch.setattr(
        pathlib.Path, "home", lambda: pathlib.Path(fake_home)
    )

    monkeypatch.setattr(os.path, "exists", lambda _: False)
    with pytest.raises(FileNotFoundError):
        utils.get_desktop_path()


def test_validate_user_input():
    simple_option = TextLineEditData(label="dummy")
    simple_option.value = "spam"
    simple_option.add_validation(
        validators.CustomValidation(query=lambda _, __: False)
    )
    options = {
        "one": simple_option
    }
    findings = utils.validate_user_input(options)
    assert findings['one'] == ['spam failed validation']


def test_validate_user_input_value_missing():
    simple_option = TextLineEditData(label="dummy")
    simple_option.required = True
    options = {
        "one": simple_option
    }
    findings = utils.validate_user_input(options)
    assert "Required value missing" in findings["one"]


def test_assign_values_to_job_options():
    simple_option = TextLineEditData(label="dummy")
    assert simple_option.value is None
    params = utils.assign_values_to_job_options(
        [simple_option],
        dummy="spam"
    )
    assert params[0].value == "spam"


def test_assign_values_to_job_options_with_setting_name():
    simple_option1 = TextLineEditData(label="dummy1")
    assert simple_option1.value is None
    simple_option1.setting_name = "bacon"
    params = utils.assign_values_to_job_options(
        [simple_option1],
        bacon="spam",
    )
    assert params[0].setting_name == "bacon"



def test_log_config_adds_and_remove_handler():
    logger = Mock(spec_set=logging.Logger)
    with utils.log_config(logger, Mock(name="callback")):
        logger.addHandler.assert_called_once()
        logger.removeHandler.assert_not_called()
    logger.removeHandler.assert_called_once()

class TestCallbackLogHandler:
    def test_logging_calls_callback(self):
        callback = Mock()
        handler = utils.CallbackLogHandler(callback)
        logger = logging.Logger(__name__)
        logger.addHandler(handler)
        logger.info("hello")
        callback.assert_called_once()
