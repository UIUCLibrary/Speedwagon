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
