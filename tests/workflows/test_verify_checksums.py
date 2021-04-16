import os
from unittest.mock import Mock

import pytest

from speedwagon import models
from speedwagon.workflows import workflow_verify_checksums


class TestSensitivityComparison:
    def test_sensitive_comparison_valid(self):
        standard_strategy = workflow_verify_checksums.CaseSensitiveComparison()
        assert \
            standard_strategy.compare("asdfasdfasdf", "asdfasdfasdf") is True

    def test_sensitive_comparison_invalid(self):
        standard_strategy = workflow_verify_checksums.CaseSensitiveComparison()
        assert \
            standard_strategy.compare("asdfasdfasdf", "ASDFASDFASDF") is False

    def test_insensitive_comparison_valid(self):
        case_insensitive_strategy = \
            workflow_verify_checksums.CaseInsensitiveComparison()

        assert case_insensitive_strategy.compare("asdfasdfasdf",
                                                 "asdfasdfasdf") is True

    def test_insensitive_comparison_invalid(self):
        case_insensitive_strategy = \
            workflow_verify_checksums.CaseInsensitiveComparison()
        assert case_insensitive_strategy.compare("asdfasdfasdf",
                                                 "ASDFASDFASDF") is True


class TestChecksumWorkflowValidArgs:
    @pytest.fixture
    def workflow(self):
        return workflow_verify_checksums.ChecksumWorkflow()

    @pytest.fixture
    def default_options(self, workflow):
        return models.ToolOptionsModel3(
            workflow.user_options()
        ).get()

    @pytest.mark.parametrize("invalid_input_value", [None, ""])
    def test_empty_input_fails(
            self, invalid_input_value, workflow, default_options):

        options = default_options.copy()
        options['Input'] = invalid_input_value
        with pytest.raises(ValueError):
            workflow.validate_user_options(**options)

    def test_input_not_existing_fails(
            self, workflow, default_options, monkeypatch):

        options = default_options.copy()
        options['Input'] = "some/invalid/path"
        import os
        with monkeypatch.context() as mp:
            mp.setattr(os.path, "exists", lambda path: False)
            with pytest.raises(ValueError):
                workflow.validate_user_options(**options)

    def test_input_not_a_dir_fails(
            self, workflow, default_options, monkeypatch
    ):

        options = default_options.copy()
        options['Input'] = "some/valid/path/dummy.txt"
        import os
        with monkeypatch.context() as mp:
            mp.setattr(os.path, "exists", lambda path: path == options['Input'])
            mp.setattr(os.path, "isdir", lambda path: False)
            with pytest.raises(ValueError):
                workflow.validate_user_options(**options)

    def test_valid(
            self, workflow, default_options, monkeypatch
    ):

        options = default_options.copy()
        options['Input'] = "some/valid/path/"
        import os
        with monkeypatch.context() as mp:
            mp.setattr(os.path, "exists", lambda path: path == options['Input'])
            mp.setattr(os.path, "isdir", lambda path: True)
            assert workflow.validate_user_options(**options) is True


class TestChecksumWorkflowTaskGenerators:
    @pytest.fixture
    def workflow(self):
        return workflow_verify_checksums.ChecksumWorkflow()

    @pytest.fixture
    def default_options(self, workflow):
        return models.ToolOptionsModel3(
            workflow.user_options()
        ).get()

    def test_checksum_workflow_initial_task(
            self,
            workflow,
            default_options,
            monkeypatch
    ):
        user_args = default_options.copy()
        user_args["Input"] = "dummy_path"

        fake_checksum_report_file = \
            os.path.join(user_args["Input"], "checksum.md5")

        workflow._locate_checksum_files = \
            Mock(return_value=[fake_checksum_report_file])

        task_builder = Mock()

        ReadChecksumReportTask = Mock()

        monkeypatch.setattr(
            workflow_verify_checksums,
            "ReadChecksumReportTask",
            ReadChecksumReportTask
        )
        workflow.initial_task(
            task_builder=task_builder,
            **user_args
        )
        assert task_builder.add_subtask.called is True

        ReadChecksumReportTask.assert_called_with(
            checksum_file=fake_checksum_report_file
        )

    def test_create_new_task(self, workflow, monkeypatch):
        task_builder = Mock()
        job_args = {
            'filename': "some_real_file.txt",
            'path': os.path.join("some", "real", "path"),
            'expected_hash': "something",
            'source_report': "something",
        }
        ValidateChecksumTask = Mock()

        monkeypatch.setattr(
            workflow_verify_checksums,
            "ValidateChecksumTask",
            ValidateChecksumTask
        )
        workflow.create_new_task(
            task_builder=task_builder,
            **job_args
        )
        assert task_builder.add_subtask.called is True

        ValidateChecksumTask.assert_called_with(
            file_name=job_args['filename'],
            file_path=job_args['path'],
            expected_hash=job_args['expected_hash'],
            source_report=job_args['source_report']
        )
