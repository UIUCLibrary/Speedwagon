import warnings
from unittest.mock import Mock, ANY

import pytest

import speedwagon
from speedwagon.workflows import workflow_make_checksum
from speedwagon import models


class TestZipPackagesWorkflow:
    @pytest.fixture
    def workflow(self):
        return \
            workflow_make_checksum.MakeChecksumBatchMultipleWorkflow()

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

        initial_results = []
        additional_data = {}

        def scandir(root):
            results = [
                Mock(path=os.path.join(root, "something"))
            ]
            return results
        #

        def walk(root):
            results = [
                (root, (), ("some_file.txt", ))
            ]
            for f in results:
                yield f
        monkeypatch.setattr(workflow_make_checksum.os, "scandir", scandir)
        monkeypatch.setattr(workflow_make_checksum.os, "walk", walk)
        task_metadata = \
            workflow.discover_task_metadata(
                initial_results=initial_results,
                additional_data=additional_data,
                **user_args
            )

        assert \
            len(task_metadata) == 1 and \
            task_metadata[0]['source_path'] == os.path.join(
                    user_args["Input"], "something") and \
            task_metadata[0]['filename'] == "some_file.txt" and \
            task_metadata[0]['save_to_filename'] == os.path.join(
                user_args["Input"], "something", "checksum.md5"
            )

    def test_create_new_task(self, workflow, monkeypatch):
        import os
        job_args = {
            "source_path": os.path.join("some", "source", "path"),
            "filename": "some_file.txt",
            'save_to_filename':
                os.path.join(
                    "some",
                    "source",
                    "path",
                    "something",
                    "checksum.md5"
                )
        }
        task_builder = Mock()
        MakeChecksumTask = Mock()
        MakeChecksumTask.name = "MakeChecksumTask"
        monkeypatch.setattr(
            speedwagon.tasks.validation,
            "MakeChecksumTask",
            MakeChecksumTask
        )

        workflow.create_new_task(task_builder, **job_args)

        assert task_builder.add_subtask.called is True
        assert MakeChecksumTask.called is True

        MakeChecksumTask.assert_called_with(
            job_args['source_path'],
            "some_file.txt",
            job_args['save_to_filename']
        )

    def test_generate_report(self, workflow, default_options):
        ResultsValues = workflow_make_checksum.ResultsValues
        user_args = default_options.copy()
        results = [
            speedwagon.tasks.Result(
                speedwagon.tasks.validation.MakeChecksumTask,
                {
                    ResultsValues.CHECKSUM_FILE: "checksum.md5"
                }
            )
        ]
        report = workflow.generate_report(results=results, **user_args)
        assert "Checksum values for" in report

    def test_completion_task(self, workflow, default_options):
        user_args = default_options.copy()
        task_builder = Mock()
        ResultsValues = workflow_make_checksum.ResultsValues
        results = [
            speedwagon.tasks.Result(
                speedwagon.tasks.validation.MakeChecksumTask,
                {
                    ResultsValues.CHECKSUM_FILE: "checksum.md5"
                }
            )
        ]
        workflow.completion_task(task_builder, results, **user_args)
        assert task_builder.add_subtask.called is True


class TestRegenerateChecksumBatchSingleWorkflow:
    @pytest.fixture
    def workflow(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return \
                workflow_make_checksum.RegenerateChecksumBatchSingleWorkflow()

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

        initial_results = []
        additional_data = {}

        def scandir(root):
            results = [
                Mock(path=os.path.join(root, "something"))
            ]
            return results
        #

        def walk(root):
            results = [
                (root, (), ("some_file.txt", ))
            ]
            for f in results:
                yield f
        monkeypatch.setattr(workflow_make_checksum.os, "scandir", scandir)
        monkeypatch.setattr(workflow_make_checksum.os, "walk", walk)

        monkeypatch.setattr(
            workflow_make_checksum.os.path,
            "samefile",
            lambda a, b: False
        )

        task_metadata = \
            workflow.discover_task_metadata(
                initial_results=initial_results,
                additional_data=additional_data,
                **user_args
            )
        assert len(task_metadata) == 1 and \
               task_metadata[0]['source_path'] == "some" and \
               task_metadata[0]['filename'] == "some_file.txt" and \
               task_metadata[0]['save_to_filename'] == os.path.join(
                    "some", "source")

    def test_create_new_task(self, workflow, monkeypatch):
        import os
        job_args = {
            "source_path": os.path.join("some", "source", "path"),
            "filename": "some_file.txt",
            'save_to_filename':
                os.path.join(
                    "some",
                    "source",
                    "path",
                    "something",
                    "checksum.md5"
                )
        }
        task_builder = Mock()
        MakeChecksumTask = Mock()
        MakeChecksumTask.name = "MakeChecksumTask"
        monkeypatch.setattr(
            speedwagon.tasks.validation,
            "MakeChecksumTask",
            MakeChecksumTask
        )

        workflow.create_new_task(task_builder, **job_args)

        assert task_builder.add_subtask.called is True
        assert MakeChecksumTask.called is True

        MakeChecksumTask.assert_called_with(
            job_args['source_path'],
            "some_file.txt",
            job_args['save_to_filename']
        )

    def test_generate_report(self, workflow, default_options):
        ResultsValues = workflow_make_checksum.ResultsValues
        user_args = default_options.copy()
        results = [
            speedwagon.tasks.Result(
                speedwagon.tasks.validation.MakeChecksumTask,
                {
                    ResultsValues.CHECKSUM_FILE: "checksum.md5"
                }
            )
        ]
        report = workflow.generate_report(results=results, **user_args)
        assert "Checksum values for" in report

    def test_completion_task(self, monkeypatch, workflow, default_options):
        user_args = default_options.copy()
        task_builder = Mock()
        ResultsValues = workflow_make_checksum.ResultsValues
        results = [
            speedwagon.tasks.Result(
                speedwagon.tasks.validation.MakeChecksumTask,
                {
                    ResultsValues.CHECKSUM_FILE: "checksum.md5"
                }
            )
        ]

        MakeCheckSumReportTask = Mock()

        monkeypatch.setattr(
            speedwagon.tasks.validation,
            "MakeCheckSumReportTask",
            MakeCheckSumReportTask
        )

        workflow.completion_task(task_builder, results, **user_args)
        assert task_builder.add_subtask.called is True
        assert MakeCheckSumReportTask.called is True

        MakeCheckSumReportTask.assert_called_with("checksum.md5", ANY)


class TestRegenerateChecksumBatchMultipleWorkflow:
    @pytest.fixture
    def workflow(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return \
                workflow_make_checksum.RegenerateChecksumBatchMultipleWorkflow()

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

        initial_results = []
        additional_data = {}

        def scandir(root):
            results = [
                Mock(path=os.path.join(root, "something"))
            ]
            return results
        #

        def walk(root):
            results = [
                (root, (), ("some_file.txt", ))
            ]
            for f in results:
                yield f
        monkeypatch.setattr(workflow_make_checksum.os, "scandir", scandir)
        monkeypatch.setattr(workflow_make_checksum.os, "walk", walk)

        monkeypatch.setattr(
            workflow_make_checksum.os.path,
            "samefile",
            lambda a, b: False
        )

        task_metadata = \
            workflow.discover_task_metadata(
                initial_results=initial_results,
                additional_data=additional_data,
                **user_args
            )
        assert len(task_metadata) == 1 and \
               task_metadata[0]['source_path'] == os.path.join(
                   user_args["Input"], "something") and \
               task_metadata[0]['filename'] == "some_file.txt" and \
               task_metadata[0]['save_to_filename'] == os.path.join(
                    "some", "source", "something", "checksum.md5")

    def test_create_new_task(self, workflow, monkeypatch):
        import os
        job_args = {
            "source_path": os.path.join("some", "source", "path"),
            "filename": "some_file.txt",
            'save_to_filename':
                os.path.join(
                    "some",
                    "source",
                    "path",
                    "something",
                    "checksum.md5"
                )
        }
        task_builder = Mock()
        MakeChecksumTask = Mock()
        MakeChecksumTask.name = "MakeChecksumTask"
        monkeypatch.setattr(
            speedwagon.tasks.validation,
            "MakeChecksumTask",
            MakeChecksumTask
        )

        workflow.create_new_task(task_builder, **job_args)

        assert task_builder.add_subtask.called is True
        assert MakeChecksumTask.called is True

        MakeChecksumTask.assert_called_with(
            job_args['source_path'],
            "some_file.txt",
            job_args['save_to_filename']
        )

    def test_generate_report(self, workflow, default_options):
        ResultsValues = workflow_make_checksum.ResultsValues
        user_args = default_options.copy()
        results = [
            speedwagon.tasks.Result(
                speedwagon.tasks.validation.MakeChecksumTask,
                {
                    ResultsValues.CHECKSUM_FILE: "checksum.md5"
                }
            )
        ]
        report = workflow.generate_report(results=results, **user_args)
        assert "Checksum values for" in report

    def test_completion_task(self, monkeypatch, workflow, default_options):
        user_args = default_options.copy()
        task_builder = Mock()
        ResultsValues = workflow_make_checksum.ResultsValues
        results = [
            speedwagon.tasks.Result(
                speedwagon.tasks.validation.MakeChecksumTask,
                {
                    ResultsValues.CHECKSUM_FILE: "checksum.md5"
                }
            )
        ]

        MakeCheckSumReportTask = Mock()

        monkeypatch.setattr(
            speedwagon.tasks.validation,
            "MakeCheckSumReportTask",
            MakeCheckSumReportTask
        )

        workflow.completion_task(task_builder, results, **user_args)
        assert task_builder.add_subtask.called is True
        assert MakeCheckSumReportTask.called is True

        MakeCheckSumReportTask.assert_called_with("checksum.md5", ANY)
