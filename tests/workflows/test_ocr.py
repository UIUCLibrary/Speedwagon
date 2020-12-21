import pytest
import os.path
from speedwagon.workflows import workflow_ocr
from speedwagon.exceptions import MissingConfiguration, SpeedwagonException


def test_no_config():
    with pytest.raises(MissingConfiguration):
        workflow_ocr.OCRWorkflow()


def test_discover_task_metadata_raises_with_no_tessdata(monkeypatch):
    user_options = {"tessdata": "/some/path"}
    monkeypatch.setattr(os.path, "exists", lambda args: True)
    workflow = workflow_ocr.OCRWorkflow(global_settings=user_options)

    monkeypatch.setattr(os.path, "exists", lambda args: False)
    with pytest.raises(SpeedwagonException):
        user_options = {"tessdata": None}
        workflow.discover_task_metadata([], None, **user_options)
