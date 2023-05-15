from unittest.mock import Mock

import pytest
from speedwagon.workflows import workflow_validate_hathi_metadata


class TestValidateImageMetadataWorkflow:
    @pytest.fixture
    def workflow(self):
        return \
            workflow_validate_hathi_metadata.ValidateImageMetadataWorkflow()

    @pytest.fixture
    def default_options(self, workflow):
        return {
            data.label: data.value for data in workflow.job_options()
        }

        # models = pytest.importorskip('speedwagon.frontend.qtwidgets.models')
        # return models.ToolOptionsModel4(
        #     workflow.get_user_options()
        # ).get()

    def test_validate_user_options_valid(
            self,
            monkeypatch,
            workflow,
            default_options
    ):
        user_args = default_options.copy()
        user_args['Input'] = "some_file.tif"

        monkeypatch.setattr(
            workflow_validate_hathi_metadata.os.path,
            "exists",
            lambda path: path == user_args['Input']
        )

        monkeypatch.setattr(
            workflow_validate_hathi_metadata.os.path,
            "isfile",
            lambda path: path == user_args['Input']
        )

        assert workflow.validate_user_options(**user_args) is True

    @pytest.mark.parametrize("input_value,exists, isfile", [
        (None, False, False),
        ("some_file.tif", False, False),
        ("some_file.tif", True, False),
        ("some_file.tif", False, True),
    ])
    def test_validate_user_options_not_valid(
            self,
            monkeypatch,
            workflow,
            default_options,
            input_value,
            exists,
            isfile
    ):
        user_args = default_options.copy()
        user_args['Input'] = input_value

        monkeypatch.setattr(
            workflow_validate_hathi_metadata.os.path,
            "exists",
            lambda _: exists
        )

        monkeypatch.setattr(
            workflow_validate_hathi_metadata.os.path,
            "isfile",
            lambda _: isfile
        )
        with pytest.raises(ValueError):
            workflow.validate_user_options(**user_args)

    def test_discover_task_metadata(
                self,
                monkeypatch,
                workflow,
                default_options
    ):
        user_args = default_options.copy()
        initial_results = []
        additional_data = {}
        task_metadata = \
            workflow.discover_task_metadata(
                initial_results=initial_results,
                additional_data=additional_data,
                **user_args
            )

        assert len(task_metadata) == 1 and \
               task_metadata[0]['source_file'] == user_args["Input"]

    def test_create_new_task(
            self,
            workflow,
            monkeypatch
    ):
        job_args = {
            "source_file": "some_file.tif",
        }
        task_builder = Mock()
        MetadataValidatorTask = Mock()
        MetadataValidatorTask.name = "MetadataValidatorTask"
        monkeypatch.setattr(
            workflow_validate_hathi_metadata,
            "MetadataValidatorTask",
            MetadataValidatorTask
        )

        workflow.create_new_task(task_builder, **job_args)

        assert task_builder.add_subtask.called is True
        MetadataValidatorTask.assert_called_with(job_args['source_file'])


class TestMetadataValidatorTask:
    def test_work(self, monkeypatch):
        source_file = "some_file.tif"
        task = workflow_validate_hathi_metadata.MetadataValidatorTask(
            source_file
        )
        validate = Mock()
        #
        monkeypatch.setattr(
            workflow_validate_hathi_metadata.imagevalidate.Profile,
            "validate",
            validate
        )
        assert task.work() is True
        validate.assert_called_with(source_file)


def test_tasks_have_description():
    task = workflow_validate_hathi_metadata.MetadataValidatorTask(
        source_file="source_file"
    )
    assert task.task_description() is not None
