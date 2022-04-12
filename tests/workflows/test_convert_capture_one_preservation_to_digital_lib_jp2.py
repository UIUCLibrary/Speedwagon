from unittest.mock import Mock
import speedwagon
import pytest


from speedwagon.workflows import \
    workflow_convertCaptureOnePreservationToDigitalLibJP2 as \
    capture_one_workflow

from speedwagon.frontend.qtwidgets import models


def test_package_image_task_success(monkeypatch):
    mock_processfile = Mock()
    with monkeypatch.context() as mp:
        import os
        mp.setattr(capture_one_workflow, "ProcessFile", mock_processfile)
        mp.setattr(os, "makedirs", lambda *x: None)
        task = capture_one_workflow.PackageImageConverterTask(
            source_file_path="spam",
            dest_path="eggs"
        )
        assert task.work() is True
    assert mock_processfile.called is True


def test_validate_user_options_valid(monkeypatch):
    user_args = {
        "Input": "./some/path/preservation"
    }
    import os.path
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    monkeypatch.setattr(os.path, "isdir", lambda x: True)
    validator = \
        capture_one_workflow.ConvertTiffPreservationToDLJp2Workflow.validate_user_options
    assert validator(**user_args) is True


def test_validate_user_options_missing_input(monkeypatch):
    user_args = {
        "Input": None
    }
    with pytest.raises(ValueError):
        validator = \
            capture_one_workflow.ConvertTiffPreservationToDLJp2Workflow.validate_user_options
        validator(**user_args)


def test_validate_user_options_input_not_exists(monkeypatch):
    user_args = {
        "Input": "./some/path/that/does/not/exists/preservation"
    }
    import os.path
    monkeypatch.setattr(os.path, "exists", lambda x: False)

    with pytest.raises(ValueError):
        validator = \
            capture_one_workflow.ConvertTiffPreservationToDLJp2Workflow.validate_user_options
        validator(**user_args)


def test_validate_user_options_input_is_file(monkeypatch):
    user_args = {
        "Input": "./some/path/a_file.tif"
    }
    import os.path
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    monkeypatch.setattr(os.path, "isdir", lambda x: False)

    with pytest.raises(ValueError):
        validator = \
            capture_one_workflow.ConvertTiffPreservationToDLJp2Workflow.validate_user_options
        validator(**user_args)


def test_validate_user_options_input_not_pres(monkeypatch):
    user_args = {
        "Input": "./some/path/that/does/not/exists"
    }
    import os.path
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    monkeypatch.setattr(os.path, "isdir", lambda x: True)

    with pytest.raises(ValueError):
        validator = \
            capture_one_workflow.ConvertTiffPreservationToDLJp2Workflow.validate_user_options
        validator(**user_args)


def test_package_image_task_failure(monkeypatch):
    import os
    mock_processfile = Mock()
    mock_processfile.process = Mock(
        side_effect=capture_one_workflow.ProcessingException("failure"))

    def get_mock_processfile(*args):
        return mock_processfile

    with monkeypatch.context() as mp:
        mp.setattr(os, "makedirs", lambda *x: None)
        mp.setattr(capture_one_workflow, "ProcessFile", get_mock_processfile)
        task = capture_one_workflow.PackageImageConverterTask(
            source_file_path="spam",
            dest_path="eggs"
        )
        assert task.work() is False


class TestConvertTiffPreservationToDLJp2Workflow:
    @pytest.fixture
    def workflow(self):
        return \
            capture_one_workflow.ConvertTiffPreservationToDLJp2Workflow()

    @pytest.fixture
    def default_options(self, workflow):
        return models.ToolOptionsModel4(
            workflow.get_user_options()
        ).get()

    def test_validate_user_options_valid(
            self,
            monkeypatch,
            workflow,
            default_options
    ):
        user_args = default_options.copy()
        import os

        user_args["Input"] = os.path.join(
            "some", "valid", "path", "preservation")

        monkeypatch.setattr(
            capture_one_workflow.os.path,
            "exists",
            lambda path: path == user_args["Input"]
        )

        monkeypatch.setattr(
            capture_one_workflow.os.path,
            "isdir",
            lambda path: path == user_args["Input"]
        )

        assert workflow.validate_user_options(**user_args) is True

    def test_discover_task_metadata(
            self,
            monkeypatch,
            workflow,
            default_options
    ):
        import os
        user_args = default_options.copy()
        user_args["Input"] = os.path.join(
            "some", "valid", "path", "preservation")

        initial_results = []
        additional_data = {}

        def scandir(path):
            path_file = Mock(
                path=os.path.join(path, "123.tif"),
            )
            path_file.name = "123.tif"
            return [path_file]

        monkeypatch.setattr(
            capture_one_workflow.os,
            "scandir",
            scandir
        )

        task_metadata = \
            workflow.discover_task_metadata(
                initial_results=initial_results,
                additional_data=additional_data,
                **user_args
            )
        assert len(task_metadata) == 1 and \
               task_metadata[0]['source_file'] == \
               os.path.join(user_args["Input"], "123.tif")

    def test_create_new_task(self, workflow, monkeypatch):
        import os
        job_args = {
            "source_file": os.path.join("some", "source", "preservation"),
            "output_path": os.path.join("some", "source", "access"),
        }
        task_builder = Mock()
        PackageImageConverterTask = Mock()
        PackageImageConverterTask.name = "PackageImageConverterTask"
        monkeypatch.setattr(
            capture_one_workflow,
            "PackageImageConverterTask",
            PackageImageConverterTask
        )

        workflow.create_new_task(task_builder, **job_args)

        assert task_builder.add_subtask.called is True
        PackageImageConverterTask.assert_called_with(
            source_file_path=job_args['source_file'],
            dest_path=job_args['output_path'],
        )

    def test_generate_report_success(self, workflow, default_options):
        user_args = default_options.copy()
        results = [
            speedwagon.tasks.Result(
                capture_one_workflow.PackageImageConverterTask,
                {
                    "success": True,
                    "output_filename": "somefile"
                }
            )
        ]
        report = workflow.generate_report(results, **user_args)
        assert isinstance(report, str)
        assert "Success" in report

    def test_generate_report_failure(self, workflow, default_options):
        user_args = default_options.copy()
        results = [
            speedwagon.tasks.Result(
                capture_one_workflow.PackageImageConverterTask,
                {
                    "success": False,
                    "output_filename": "somefile",
                    "source_filename": "some_source"
                }
            )
        ]
        report = workflow.generate_report(results, **user_args)
        assert isinstance(report, str)
        assert "Failed" in report


class TestPackageImageConverterTask:
    def test_work(self, monkeypatch):
        source_file_path = "source_file"
        dest_path = "output_path"
        tasks = capture_one_workflow.PackageImageConverterTask(
            source_file_path=source_file_path,
            dest_path=dest_path
        )
        makedirs = Mock()
        monkeypatch.setattr(capture_one_workflow.os, "makedirs", makedirs)
        process = Mock()

        monkeypatch.setattr(
            capture_one_workflow.ProcessFile,
            "process",
            process
        )

        assert tasks.work() is True
        assert process.called is True


def test_kdu_non_zero_throws_exception(monkeypatch):
    with pytest.raises(capture_one_workflow.ProcessingException):
        process = capture_one_workflow.ConvertFile()
        monkeypatch.setattr(
            capture_one_workflow.pykdu_compress,
            'kdu_compress_cli2',
            Mock(return_value=2)
        )
        process.process("dummy", "out")


def test_kdu_success(monkeypatch):
    process = capture_one_workflow.ConvertFile()
    monkeypatch.setattr(
        capture_one_workflow.pykdu_compress,
        'kdu_compress_cli2',
        Mock(return_value=0)
    )
    process.process("dummy", "out.jp2")
    assert "Generated out.jp2" in process.status


def test_tasks_have_description():
    task = capture_one_workflow.PackageImageConverterTask(
        source_file_path="some_source_path",
        dest_path="some_dest_path"
    )

    assert task.task_description() is not None
