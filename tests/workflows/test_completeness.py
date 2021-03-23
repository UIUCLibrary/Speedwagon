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

