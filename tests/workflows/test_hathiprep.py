from unittest.mock import Mock

import pytest
from speedwagon.workflows import workflow_hathiprep


@pytest.mark.parametrize("index,label", [
    (0, "input"),
    (1, "Image File Type"),
])
def test_workflow_options(index, label):
    workflow = workflow_hathiprep.HathiPrepWorkflow()
    user_options = workflow.user_options()
    assert len(user_options) > 0
    assert user_options[index].label_text == label


def test_initial_task_creates_task():
    workflow = workflow_hathiprep.HathiPrepWorkflow()
    user_args = {
        "input": "./some_real_source_folder",
        "Image File Type": "JPEG 2000",
    }

    mock_builder = Mock()
    workflow.initial_task(
        task_builder=mock_builder,
        **user_args
    )
    assert \
        mock_builder.add_subtask.called is True and \
        mock_builder.add_subtask.call_args_list[0][0][0]._root == user_args['input']

