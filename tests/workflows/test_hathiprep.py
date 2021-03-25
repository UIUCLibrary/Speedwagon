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

