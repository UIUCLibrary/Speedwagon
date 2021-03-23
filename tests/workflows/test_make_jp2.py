import pytest

from speedwagon.workflows import workflow_make_jp2


@pytest.mark.parametrize("index,label", [
    (0, "Input"),
    (1, "Output"),
])
def test_make_jp2_workflow_options(index, label):
    workflow = workflow_make_jp2.MakeJp2Workflow()
    user_options = workflow.user_options()
    assert len(user_options) > 0
    assert user_options[index].label_text == label
