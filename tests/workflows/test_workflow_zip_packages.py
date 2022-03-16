from unittest.mock import Mock

import pytest
from speedwagon.workflows import workflow_zip_packages
from speedwagon import models


class TestZipPackagesWorkflow:
    @pytest.fixture
    def workflow(self):
        return \
            workflow_zip_packages.ZipPackagesWorkflow()

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
        user_args['Source'] = os.path.join("some", "source", "path")
        user_args['Output'] = os.path.join("some", "output", "path")

        monkeypatch.setattr(
            workflow_zip_packages.os.path,
            "exists",
            lambda path: path in [user_args['Source'], user_args['Output']]
        )

        monkeypatch.setattr(
            workflow_zip_packages.os.path,
            "isdir",
            lambda path: path in [user_args['Source'], user_args['Output']]
        )

        assert workflow.validate_user_options(**user_args) is True

    @pytest.mark.parametrize("output_exists,output_isdir", [
        (False, False),
        (False, True),
        (True, False),
    ])
    def test_validate_user_options_not_valid(
            self,
            monkeypatch,
            workflow,
            default_options,
            output_exists, output_isdir,
    ):
        user_args = default_options.copy()
        import os
        user_args['Source'] = os.path.join("some", "source", "path")
        user_args['Output'] = os.path.join("some", "output", "path")

        monkeypatch.setattr(
            workflow_zip_packages.os.path,
            "exists",
            lambda path: (path == user_args['Source']) or
                         (path == user_args['Output'] and output_exists)
        )

        monkeypatch.setattr(
            workflow_zip_packages.os.path,
            "isdir",
            lambda path: (path == user_args['Source']) or
                         (path == user_args['Output'] and output_isdir)
        )
        with pytest.raises(ValueError):
            workflow.validate_user_options(**user_args)

    def test_discover_task_metadata(
            self,
            monkeypatch,
            workflow,
            default_options
    ):
        import os
        user_args = default_options.copy()
        user_args["Source"] = os.path.join("some", "source")
        user_args["Output"] = os.path.join("some", "output")

        initial_results = []
        additional_data = {}

        def scandir(root):
            results = [
                Mock(path=os.path.join(root, "something.txt"))
            ]
            return results

        monkeypatch.setattr(workflow_zip_packages.os, "scandir", scandir)
        task_metadata = \
            workflow.discover_task_metadata(
                initial_results=initial_results,
                additional_data=additional_data,
                **user_args
            )

        assert len(task_metadata) == 1 and \
               task_metadata[0]['source_path'] == \
               os.path.join(user_args["Source"], "something.txt")

    def test_create_new_task(self, workflow, monkeypatch):
        import os
        job_args = {
            "source_path": os.path.join("some", "source", "path"),
            "destination_path": os.path.join("some", "destination", "path"),
        }
        task_builder = Mock()
        ZipTask = Mock()
        ZipTask.name = "ZipTask"
        monkeypatch.setattr(
            workflow_zip_packages,
            "ZipTask",
            ZipTask
        )

        workflow.create_new_task(task_builder, **job_args)

        assert task_builder.add_subtask.called is True

        ZipTask.assert_called_with(
            source_path=job_args['source_path'],
            destination_path=job_args['destination_path']
        )

    def test_generate_report(self, workflow, default_options):
        import os
        user_args = default_options.copy()
        user_args["Source"] = os.path.join("some", "source")
        user_args["Output"] = os.path.join("some", "output")
        results = []
        report = workflow.generate_report(results=results, **user_args)
        assert "Zipping complete" in report


class TestZipTask:
    def test_work(self, monkeypatch):
        source_path = "source"
        destination_path = "destination"
        task = workflow_zip_packages.ZipTask(
            source_path=source_path,
            destination_path=destination_path
        )
        compress_folder_inplace = Mock()
        monkeypatch.setattr(
            workflow_zip_packages.hathizip.process,
            "compress_folder_inplace",
            compress_folder_inplace
        )

        assert task.work() is True
        compress_folder_inplace.assert_called_with(
            path=source_path,
            dst=destination_path
        )


def test_tasks_have_description():
    task = workflow_zip_packages.ZipTask(
            source_path="source_path",
            destination_path="destination_path"
        )
    assert task.task_description() is not None
