from unittest.mock import Mock

import pytest
from speedwagon.workflows import workflow_validate_metadata
from speedwagon import models, tasks
import os

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

    @pytest.mark.parametrize("input_data,exists,is_dir",[
        (os.path.join("some", "valid", "path"), False, False),
        (os.path.join("some", "valid", "path"), True, False),
        (os.path.join("some", "valid", "path"), False, True),
    ])
    def test_validate_user_options_invalid(
            self,
            monkeypatch,
            workflow,
            default_options,
            input_data,
            exists,
            is_dir
    ):
        user_options = default_options.copy()
        user_options['Input'] = input_data

        with monkeypatch.context() as mp:
            mp.setattr(os.path, "exists", lambda x: exists)
            mp.setattr(os.path, "isdir", lambda x: is_dir)
            with pytest.raises(ValueError) as e:
                assert workflow.validate_user_options(**user_options) is True

    def test_initial_task(self, monkeypatch, workflow, default_options):
        user_args = default_options.copy()
        user_args["Input"] = os.path.join("some", "valid", "path")
        user_args['Profile'] = 'HathiTrust JPEG 2000'

        task_builder = Mock()
        LocateImagesTask = Mock()
        monkeypatch.setattr(
            workflow_validate_metadata,
            "LocateImagesTask",
            LocateImagesTask
        )
        workflow.initial_task(
            task_builder=task_builder,
            **user_args
        )

        assert task_builder.add_subtask.called is True

        LocateImagesTask.assert_called_with(
            user_args['Input'],
            user_args['Profile']
        )

    def test_discover_task_metadata(self, workflow, default_options):
        user_options = default_options.copy()
        user_options["Input"] = os.path.join("some", "valid", "path")
        user_options['Profile'] = 'HathiTrust JPEG 2000'

        initial_results = [
            tasks.Result(workflow_validate_metadata.LocateImagesTask, [
                "spam.jp2"
            ])
        ]
        additional_data = {}
        tasks_generated = workflow.discover_task_metadata(
            initial_results=initial_results,
            additional_data=additional_data,
            **user_options
        )
        JobValues = workflow_validate_metadata.JobValues
        assert len(tasks_generated) == 1
        assert tasks_generated[0] == {
            JobValues.ITEM_FILENAME.value: "spam.jp2",
            JobValues.PROFILE_NAME.value: user_options["Profile"]
        }

    def test_create_new_task(self, monkeypatch, workflow):
        job_args = {
            "filename": "somefile.jp2",
            "profile_name": 'HathiTrust JPEG 2000'
        }
        task_builder = Mock()
        ValidateImageMetadataTask = Mock()
        monkeypatch.setattr(
            workflow_validate_metadata,
            "ValidateImageMetadataTask",
            ValidateImageMetadataTask
        )

        workflow.create_new_task(task_builder, **job_args)

        assert task_builder.add_subtask.called is True
        ValidateImageMetadataTask.assert_called_with(
            job_args['filename'],
            job_args['profile_name']
        )