import pytest
from speedwagon.workflows import workflow_validate_metadata

options = [
    (0, "Input"),
    (1, "Profile")
]


@pytest.mark.parametrize("index,label", options)
def test_validate_metadata_workflow_has_options(index, label):
    workflow = workflow_validate_metadata.ValidateMetadataWorkflow()
    user_options = workflow.user_options()
    assert len(user_options) > 0
    assert user_options[index].label_text == label

