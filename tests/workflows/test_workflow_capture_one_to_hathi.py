import warnings
from unittest.mock import Mock, MagicMock

import pytest
from speedwagon.workflows import workflow_capture_one_to_hathi
from speedwagon import models


class TestCaptureOneToHathiTiffPackageWorkflow:
    @pytest.fixture
    def workflow(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return \
                workflow_capture_one_to_hathi.CaptureOneToHathiTiffPackageWorkflow()

    @pytest.fixture
    def default_options(self, workflow):
        return models.ToolOptionsModel3(
            workflow.user_options()
        ).get()

    def test_discover_task_metadata(
            self,
            monkeypatch,
            workflow,
            default_options
    ):
        import os
        user_args = default_options.copy()
        user_args["Input"] = os.path.join("some", "source")
        user_args["Output"] = os.path.join("some", "output")

        initial_results = []
        additional_data = {}

        def locate_packages(_, path):
            packages = [
                Mock()
            ]
            return packages

        monkeypatch.setattr(
            workflow_capture_one_to_hathi.packager.PackageFactory,
            "locate_packages",
            locate_packages
        )

        task_metadata = \
            workflow.discover_task_metadata(
                initial_results=initial_results,
                additional_data=additional_data,
                **user_args
            )

        assert len(task_metadata) == 1 and \
               task_metadata[0]['output'] == user_args["Output"] and \
               task_metadata[0]['source_path'] == user_args["Input"]

    def test_create_new_task(self, workflow, monkeypatch):
        import os
        job_args = {
            'package': MagicMock(),
            "source_path": os.path.join("some", "source", "path"),
            "output": os.path.join("some", "destination", "path"),
        }
        task_builder = Mock()
        PackageConverter = Mock()
        PackageConverter.name = "PackageConverter"
        monkeypatch.setattr(
            workflow_capture_one_to_hathi,
            "PackageConverter",
            PackageConverter
        )

        workflow.create_new_task(task_builder, **job_args)

        assert task_builder.add_subtask.called is True
        assert PackageConverter.called is True


class TestPackageConverter:
    def test_work(self, monkeypatch):
        source_path = ""
        packaging_id = ""
        existing_package = Mock()
        new_package_root = ""
        task = workflow_capture_one_to_hathi.PackageConverter(
            source_path=source_path,
            packaging_id=packaging_id,
            existing_package=existing_package,
            new_package_root=new_package_root

        )
        transform = Mock()
        monkeypatch.setattr(
            workflow_capture_one_to_hathi.packager.PackageFactory,
            "transform",
            transform
        )

        assert task.work() is True
        assert transform.called is True


def test_tasks_have_description():
    task = workflow_capture_one_to_hathi.PackageConverter(
        source_path="some_source_path",
        packaging_id="123",
        existing_package=Mock(),
        new_package_root="some_root",
    )
    assert task.task_description() is not None
