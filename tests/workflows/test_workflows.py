from unittest.mock import Mock, MagicMock

import pytest

from speedwagon import available_workflows


@pytest.mark.parametrize("workflow_type", available_workflows().values())
def test_all_workflow_have_valid_user_options(workflow_type, monkeypatch):
    import speedwagon.workflows.workflow_ocr
    monkeypatch.setattr(
        speedwagon.workflows.workflow_ocr,
        "path_contains_traineddata", lambda path: False
    )

    workflow = workflow_type(global_settings=MagicMock())
    results = workflow.get_user_options()
    assert len(results) > 0
