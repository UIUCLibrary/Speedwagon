import os

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


def test_assign_values_to_job_options():
    simple_option = TextLineEditData(label="dummy")
    assert simple_option.value is None
    params = utils.assign_values_to_job_options(
        [simple_option],
        dummy="spam"
    )
    assert params[0].value == "spam"
