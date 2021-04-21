from unittest.mock import Mock, MagicMock, ANY, call

import pytest
from speedwagon.workflows import workflow_convertTifftoHathiTrustJP2
from speedwagon import models


class TestConvertTiffToHathiJp2Workflow:
    @pytest.fixture
    def workflow(self):
        return \
            workflow_convertTifftoHathiTrustJP2.ConvertTiffToHathiJp2Workflow()

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
        user_options = default_options.copy()
        user_options["Input"] = os.path.join("some", "input", "path")
        user_options["Output"] = os.path.join("some", "output", "path")
        initial_results = []
        additional_data = {}

        def walk(root):
            return [
                (root, (), ("1222.tif", "111.tif", "extra_file.txt"))
            ]

        monkeypatch.setattr(os, "walk", walk)
        tasks_metadata = workflow.discover_task_metadata(
            initial_results=initial_results,
            additional_data=additional_data,
            **user_options
        )
        assert len(tasks_metadata) == 3

    @pytest.mark.parametrize("task_type, task_class", [
        ("convert", 'ImageConvertTask'),
        ("copy", 'CopyTask')
    ])
    def test_create_new_task(
            self,
            workflow,
            task_type,
            task_class,
            monkeypatch
    ):

        import os
        job_args = {
            "output_root": os.path.join("some", "output", "path"),
            "relative_path_to_root": 'out',
            "source_root": os.path.join("some", "input", "path"),
            "source_file": "some_file.tif",
            "task_type": task_type
        }
        task_builder = Mock()
        ImageTask = Mock()
        ImageTask.name = task_type
        monkeypatch.setattr(
            workflow_convertTifftoHathiTrustJP2,
            task_class,
            ImageTask
        )

        workflow.create_new_task(task_builder, **job_args)

        assert task_builder.add_subtask.called is True
        source_file_path = os.path.join(
            job_args['source_root'],
            job_args['relative_path_to_root'],
            job_args['source_file']
        )

        ImageTask.assert_called_with(
            source_file_path,
            os.path.join(
                job_args["output_root"],
                job_args["relative_path_to_root"]
            )
        )

    def test_create_new_task_invalid_type(self, workflow, monkeypatch):
        import os
        job_args = {
            "output_root": os.path.join("some", "output", "path"),
            "relative_path_to_root": 'out',
            "source_root": os.path.join("some", "input", "path"),
            "source_file": "some_file.tif",
            "task_type": "bad task type"
        }
        task_builder = Mock()
        with pytest.raises(Exception) as e:
            workflow.create_new_task(task_builder, **job_args)
        assert "Don't know what to do for bad task type" in str(e.value)


class TestImageConvertTask:
    def test_work(self, monkeypatch):
        import os
        source_file_path = "source_file.tif"
        output_path = os.path.join("output", "path")

        makedirs = Mock()
        monkeypatch.setattr(
            workflow_convertTifftoHathiTrustJP2.os,
            "makedirs",
            makedirs
        )

        kdu_compress_cli2 = Mock()
        monkeypatch.setattr(
            workflow_convertTifftoHathiTrustJP2.pykdu_compress,
            "kdu_compress_cli2",
            kdu_compress_cli2
        )

        set_dpi = Mock()
        monkeypatch.setattr(
            workflow_convertTifftoHathiTrustJP2,
            "set_dpi",
            set_dpi
        )

        task = workflow_convertTifftoHathiTrustJP2.ImageConvertTask(
            source_file_path=source_file_path,
            output_path=output_path
        )
        assert task.work() is True
        assert makedirs.called is True and \
               kdu_compress_cli2.called is True and \
               set_dpi.called is True
        kdu_compress_cli2.assert_called_with(
            'source_file.tif', ANY, in_args=ANY)


class TestCopyTask:
    def test_work(self, monkeypatch):
        import os
        source_file_path = "source_file.tif"
        output_path = os.path.join("output", "path")

        makedirs = Mock()
        monkeypatch.setattr(
            workflow_convertTifftoHathiTrustJP2.os,
            "makedirs",
            makedirs
        )

        process = Mock()
        monkeypatch.setattr(
            workflow_convertTifftoHathiTrustJP2.ProcessFile,
            "process",
            process
        )
        task = workflow_convertTifftoHathiTrustJP2.CopyTask(
            source_file_path=source_file_path,
            output_path=output_path
        )
        assert task.work() is True
        assert makedirs.called is True and \
               process.called is True
        process.assert_called_with(
            'source_file.tif', ANY)