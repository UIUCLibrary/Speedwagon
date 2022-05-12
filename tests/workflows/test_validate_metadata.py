from unittest.mock import Mock

import pytest

import speedwagon
import speedwagon.tasks.validation
from speedwagon.workflows import workflow_validate_metadata

import os

options = [
    (0, "Input"),
    (1, "Profile")
]


@pytest.mark.parametrize("index,label", options)
def test_validate_metadata_workflow_has_options(index, label):
    workflow = workflow_validate_metadata.ValidateMetadataWorkflow()
    user_options = workflow.get_user_options()
    assert len(user_options) > 0
    assert user_options[index].label == label


class TestValidateMetadataWorkflow:
    @pytest.fixture
    def workflow(self):
        return workflow_validate_metadata.ValidateMetadataWorkflow()

    @pytest.fixture
    def default_options(self, workflow):
        return {
            data.label: data.value for data in workflow.get_user_options()
        }


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

    @pytest.mark.parametrize("input_data,exists,is_dir", [
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
            with pytest.raises(ValueError):
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
            speedwagon.tasks.Result(
                workflow_validate_metadata.LocateImagesTask, [
                    "spam.jp2"
                ]
            )
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
            speedwagon.tasks.validation,
            "ValidateImageMetadataTask",
            ValidateImageMetadataTask
        )

        workflow.create_new_task(task_builder, **job_args)

        assert task_builder.add_subtask.called is True
        ValidateImageMetadataTask.assert_called_with(
            job_args['filename'],
            job_args['profile_name']
        )

    def test_generate_report_on_success(self, workflow, default_options):
        user_options = default_options.copy()
        user_options["Input"] = os.path.join("some", "valid", "path")
        user_options['Profile'] = 'HathiTrust JPEG 2000'

        ResultValues = \
            speedwagon.tasks.validation.ValidateImageMetadataTask.ResultValues

        results = [
            speedwagon.tasks.Result(
                speedwagon.tasks.validation.ValidateImageMetadataTask,
                {
                    ResultValues.VALID: True
                }
            )
        ]
        report = workflow.generate_report(results, **user_options)
        assert isinstance(report, str)
        assert "Total files checked: 1" in report

    def test_generate_report_on_failure(self, workflow, default_options):
        user_options = default_options.copy()
        user_options["Input"] = os.path.join("some", "valid", "path")
        user_options['Profile'] = 'HathiTrust JPEG 2000'
        ResultValues = \
            speedwagon.tasks.validation.ValidateImageMetadataTask.ResultValues
        results = [
            speedwagon.tasks.Result(
                speedwagon.tasks.validation.ValidateImageMetadataTask,
                {
                    ResultValues.VALID: False,
                    ResultValues.FILENAME: "MyFailingFile.jp2",
                    ResultValues.REPORT: "spam.txt"
                }
            )
        ]
        report = workflow.generate_report(results, **user_options)
        assert isinstance(report, str)
        assert "MyFailingFile.jp2" in report


class TestLocateImagesTask:
    def test_work(self, monkeypatch):
        root_path = os.path.join("some", "path")
        profile_name = "HathiTrust JPEG 2000"
        task = workflow_validate_metadata.LocateImagesTask(
            root=root_path,
            profile_name=profile_name
        )

        def walk(root):
            files = [
                (root, (), ("1222.jp2", "111.jp2"))
            ]
            for item in files:
                yield item
        monkeypatch.setattr(os, "walk", walk)
        assert \
            task.work() is True and \
            len(task.results) == 2


class TestValidateImageMetadataTask:
    def test_work(self, monkeypatch):
        from uiucprescon import imagevalidate

        ResultValues = \
            speedwagon.tasks.validation.ValidateImageMetadataTask.ResultValues

        filename = "asdasd"
        profile_name = "HathiTrust JPEG 2000"
        task = speedwagon.tasks.validation.ValidateImageMetadataTask(
            filename=filename,
            profile_name=profile_name
        )

        def validate(_, file_name):
            report = imagevalidate.Report()
            report.filename = file_name
            return report

        monkeypatch.setattr(imagevalidate.Profile, "validate", validate)
        assert \
            task.work() is True and \
            task.results == {
                ResultValues.FILENAME: filename,
                ResultValues.VALID: True,
                ResultValues.REPORT: "* "
            }


@pytest.mark.parametrize(
    "task",
    [
        speedwagon.tasks.validation.ValidateImageMetadataTask(
            filename="filename",
            profile_name='HathiTrust JPEG 2000'
        ),
        workflow_validate_metadata.LocateImagesTask(
            root="root",
            profile_name='HathiTrust JPEG 2000'
        )
    ]
)
def test_tasks_have_description(task):
    assert task.task_description() is not None
