from unittest.mock import Mock

import pytest

from speedwagon.workflows import \
    workflow_convertCaptureOnePreservationToDigitalLibJP2 as \
        capture_one_workflow


def test_package_image_task_success(monkeypatch):
    mock_processfile = Mock()
    with monkeypatch.context() as mp:
        import os
        mp.setattr(capture_one_workflow, "ProcessFile", mock_processfile)
        mp.setattr(os, "makedirs", lambda *x: None)
        task = capture_one_workflow.PackageImageConverterTask(
            source_file_path="spam",
            dest_path="eggs"
        )
        assert task.work() is True
    assert mock_processfile.called is True


def test_validate_user_options_valid(monkeypatch):
    user_args = {
        "Input": "./some/path/preservation"
    }
    import os.path
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    monkeypatch.setattr(os.path, "isdir", lambda x: True)
    validator = \
        capture_one_workflow. \
            ConvertTiffPreservationToDLJp2Workflow. \
            validate_user_options
    assert validator(**user_args) is True


def test_validate_user_options_missing_input(monkeypatch):
    user_args = {
        "Input": None
    }
    import os.path
    # monkeypatch.setattr(os.path, "exists", lambda x: True)
    # monkeypatch.setattr(os.path, "isdir", lambda x: True)
    with pytest.raises(ValueError) as e:
        validator = \
            capture_one_workflow. \
                ConvertTiffPreservationToDLJp2Workflow. \
                validate_user_options
        validator(**user_args)


def test_validate_user_options_input_not_exists(monkeypatch):
    user_args = {
        "Input": "./some/path/that/does/not/exists/preservation"
    }
    import os.path
    monkeypatch.setattr(os.path, "exists", lambda x: False)

    with pytest.raises(ValueError) as e:
        validator = \
            capture_one_workflow. \
                ConvertTiffPreservationToDLJp2Workflow. \
                validate_user_options
        validator(**user_args)


def test_validate_user_options_input_is_file(monkeypatch):
    user_args = {
        "Input": "./some/path/a_file.tif"
    }
    import os.path
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    monkeypatch.setattr(os.path, "isdir", lambda x: False)

    with pytest.raises(ValueError) as e:
        validator = \
            capture_one_workflow. \
                ConvertTiffPreservationToDLJp2Workflow. \
                validate_user_options
        validator(**user_args)


def test_validate_user_options_input_not_pres(monkeypatch):
    user_args = {
        "Input": "./some/path/that/does/not/exists"
    }
    import os.path
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    monkeypatch.setattr(os.path, "isdir", lambda x: True)

    with pytest.raises(ValueError) as e:
        validator = \
            capture_one_workflow. \
                ConvertTiffPreservationToDLJp2Workflow. \
                validate_user_options
        validator(**user_args)


def test_package_image_task_failure(monkeypatch):
    import os
    mock_processfile = Mock()
    mock_processfile.process = Mock(
        side_effect=capture_one_workflow.ProcessingException("failure"))

    def get_mock_processfile(*args):
        return mock_processfile

    with monkeypatch.context() as mp:
        mp.setattr(os, "makedirs", lambda *x: None)
        mp.setattr(capture_one_workflow, "ProcessFile", get_mock_processfile)
        task = capture_one_workflow.PackageImageConverterTask(
            source_file_path="spam",
            dest_path="eggs"
        )
        assert task.work() is False
