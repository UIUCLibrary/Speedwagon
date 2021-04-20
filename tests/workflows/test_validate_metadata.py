import pytest
from speedwagon.workflows import workflow_validate_metadata
from speedwagon import models
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


class TestValidateMetadataWorkflow:
    @pytest.fixture
    def workflow(self):
        return workflow_validate_metadata.ValidateMetadataWorkflow()

    @pytest.fixture
    def default_options(self, workflow):
        return models.ToolOptionsModel3(
            workflow.user_options()
        ).get()

    def test_validate_user_options_valid(
            self,
            monkeypatch,
            workflow,
            default_options
    ):
        user_options = default_options.copy()
        import os
        user_options['Input'] = os.path.join("some", "valid", "path")

        with monkeypatch.context() as mp:
            mp.setattr(os.path, "exists", lambda x: x == user_options['Input'])
            mp.setattr(os.path, "isdir", lambda x: x == user_options['Input'])
            assert workflow.validate_user_options(**user_options) is True

    @pytest.mark.parametrize("exists,is_dir",[
        (False, False),
        (True, False),
        (False, True),
    ])
    def test_validate_user_options_invalid(
            self,
            monkeypatch,
            workflow,
            default_options,
            exists,
            is_dir
    ):
        user_options = default_options.copy()
        import os
        user_options['Input'] = os.path.join("some", "valid", "path")

        with monkeypatch.context() as mp:
            mp.setattr(os.path, "exists", lambda x: exists)
            mp.setattr(os.path, "isdir", lambda x: is_dir)
            with pytest.raises(ValueError) as e:
                assert workflow.validate_user_options(**user_options) is True
