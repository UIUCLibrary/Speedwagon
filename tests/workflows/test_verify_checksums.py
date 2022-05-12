import os
from unittest.mock import Mock

import pytest

import speedwagon
# from speedwagon.frontend.qtwidgets import models
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
        return {
            data.label: data.value for data in workflow.get_user_options()
        }

        # models = pytest.importorskip("speedwagon.frontend.qtwidgets.models")
        # return models.ToolOptionsModel4(
        #     workflow.get_user_options()
        # ).get()

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
        input_arg = options['Input']
        with monkeypatch.context() as mp:
            mp.setattr(os.path, "exists", lambda path: path == input_arg)
            mp.setattr(os.path, "isdir", lambda path: False)
            with pytest.raises(ValueError):
                workflow.validate_user_options(**options)

    def test_valid(
            self, workflow, default_options, monkeypatch
    ):

        options = default_options.copy()
        options['Input'] = "some/valid/path/"
        import os
        input_arg = options['Input']
        with monkeypatch.context() as mp:
            mp.setattr(os.path, "exists", lambda path: path == input_arg)
            mp.setattr(os.path, "isdir", lambda path: True)
            assert workflow.validate_user_options(**options) is True


class TestChecksumWorkflowTaskGenerators:
    @pytest.fixture
    def workflow(self):
        return workflow_verify_checksums.ChecksumWorkflow()

    @pytest.fixture
    def default_options(self, workflow):
        return {
            data.label: data.value for data in workflow.get_user_options()
        }

        # models = pytest.importorskip("speedwagon.frontend.qtwidgets.models")
        # return models.ToolOptionsModel4(
        #     workflow.get_user_options()
        # ).get()

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

        workflow.locate_checksum_files = \
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


class TestChecksumWorkflow:
    @pytest.fixture
    def workflow(self):
        return workflow_verify_checksums.ChecksumWorkflow()

    @pytest.fixture
    def default_options(self, workflow):
        return {
            data.label: data.value for data in workflow.get_user_options()
        }

        # models = pytest.importorskip("speedwagon.frontend.qtwidgets.models")
        # return models.ToolOptionsModel4(
        #     workflow.get_user_options()
        # ).get()

    def test_discover_task_metadata(self, workflow, default_options):
        initial_results = [
            speedwagon.tasks.Result(
                source=workflow_verify_checksums.ReadChecksumReportTask,
                data=[
                    {
                        'expected_hash': 'something',
                        'filename': "somefile.txt",
                        'path': os.path.join("some", "path"),
                        'source_report': "checksums.md5"
                    }
                ]
            )

        ]
        additional_data = {}
        user_args = default_options.copy()

        job_metadata = workflow.discover_task_metadata(
            initial_results=initial_results,
            additional_data=additional_data,
            **user_args
        )
        assert len(job_metadata) == 1

    def test_generator_report_failure(self, workflow, default_options):
        result_enums = workflow_verify_checksums.ResultValues
        results = [
            speedwagon.tasks.Result(
                workflow_verify_checksums.ValidateChecksumTask,
                {
                    result_enums.VALID: False,
                    result_enums.CHECKSUM_REPORT_FILE: "SomeFile.md5",
                    result_enums.FILENAME: "somefile.txt"
                }
            )
        ]
        report = workflow.generate_report(results=results)
        assert isinstance(report, str)
        assert "failed checksum validation" in report

    def test_generator_report_success(self, workflow, default_options):
        result_enums = workflow_verify_checksums.ResultValues
        results = [
            speedwagon.tasks.Result(
                workflow_verify_checksums.ValidateChecksumTask,
                {
                    result_enums.VALID: True,
                    result_enums.CHECKSUM_REPORT_FILE: "SomeFile.md5",
                    result_enums.FILENAME: "somefile.txt"

                }
            )
        ]
        report = workflow.generate_report(results=results)
        assert isinstance(report, str)
        assert "passed checksum validation" in report

    def test_locate_checksum_files(self, workflow, monkeypatch):
        def walk(root):
            return [
                ("12345", [], ("12345_1.tif", "12345_2.tif", "checksum.md5"))
            ]

        monkeypatch.setattr(workflow_verify_checksums.os, "walk", walk)
        results = list(workflow.locate_checksum_files("fakepath"))
        assert len(results) == 1


class TestReadChecksumReportTask:
    def test_work(self, monkeypatch):
        task = workflow_verify_checksums.ReadChecksumReportTask(
            checksum_file="somefile.md5"
        )
        import hathi_validate

        def extracts_checksums(checksum_file):
            for h in [
                ("abc1234", "somefile.txt")

            ]:
                yield h

        monkeypatch.setattr(
            hathi_validate.process, "extracts_checksums", extracts_checksums
        )
        assert task.work() is True
        assert len(task.results) == 1 and \
               task.results[0]['filename'] == 'somefile.txt'


class TestValidateChecksumTask:
    @pytest.mark.parametrize(
        "file_name,"
        "file_path,expected_hash,actual_hash,source_report,should_be_valid", [
            (
                    "somefile.txt",
                    os.path.join("some", "path"),
                    "abc123",
                    "abc123",
                    "checksum.md5",
                    True
            ),
            (
                    "somefile.txt",
                    os.path.join("some", "path"),
                    "abc123",
                    "badhash",
                    "checksum.md5",
                    False
            ),
        ]
    )
    def test_work(self,
                  monkeypatch,
                  file_name,
                  file_path,
                  expected_hash,
                  actual_hash,
                  source_report,
                  should_be_valid):

        task = workflow_verify_checksums.ValidateChecksumTask(
            file_name=file_name,
            file_path=file_path,
            expected_hash=expected_hash,
            source_report=source_report
        )
        import hathi_validate
        result_enums = workflow_verify_checksums.ResultValues

        calculate_md5 = Mock(return_value=actual_hash)
        with monkeypatch.context() as mp:
            mp.setattr(hathi_validate.process, "calculate_md5", calculate_md5)
            assert task.work() is True
            assert task.results[result_enums.VALID] is should_be_valid


class TestVerifyChecksumBatchSingleWorkflow:
    @pytest.fixture
    def workflow(self):
        return \
            workflow_verify_checksums.VerifyChecksumBatchSingleWorkflow()

    @pytest.fixture
    def default_options(self, workflow):
        return {
            data.label: data.value for data in workflow.get_user_options()
        }

        # models = pytest.importorskip("speedwagon.frontend.qtwidgets.models")
        # return models.ToolOptionsModel4(workflow.get_user_options()).get()

    def test_discover_task_metadata(self, workflow, default_options,
                                    monkeypatch):

        user_args = default_options.copy()
        UserArgs = workflow_verify_checksums.UserArgs
        user_args[UserArgs.INPUT.value] = os.path.join("some", "path")

        monkeypatch.setattr(
            workflow_verify_checksums.hathi_validate.process,
            "extracts_checksums",
            lambda report: [
                ("42312efb063c44844cd96e47a19e3441", "file.txt")
            ]
        )

        initial_results = []
        additional_data = {}
        tasks_generated = workflow.discover_task_metadata(
            initial_results=initial_results,
            additional_data=additional_data,
            **user_args
        )

        JobValues = workflow_verify_checksums.JobValues

        assert len(tasks_generated) == 1
        task = tasks_generated[0]
        assert task[JobValues.EXPECTED_HASH.value] == \
               "42312efb063c44844cd96e47a19e3441" and \
               task[JobValues.ITEM_FILENAME.value] == "file.txt"

    def test_create_new_task(self, workflow, monkeypatch):
        JobValues = workflow_verify_checksums.JobValues
        job_args = {
            JobValues.EXPECTED_HASH.value: "42312efb063c44844cd96e47a19e3441"
        }
        task_builder = Mock()
        ChecksumTask = Mock()
        ChecksumTask.name = "ChecksumTask"
        monkeypatch.setattr(workflow_verify_checksums, "ChecksumTask",
                            ChecksumTask)
        #
        workflow.create_new_task(task_builder, **job_args)
        assert task_builder.add_subtask.called is True
        assert ChecksumTask.called is True

    def test_generate_report_success(self, workflow, default_options):
        user_args = default_options.copy()
        ResultValues = workflow_verify_checksums.ResultValues
        results = [
            speedwagon.tasks.Result(workflow_verify_checksums.ChecksumTask, {
                ResultValues.CHECKSUM_REPORT_FILE: "checksum.md5",
                ResultValues.FILENAME: "file1.jp2",
                ResultValues.VALID: True,
            }),
            speedwagon.tasks.Result(workflow_verify_checksums.ChecksumTask, {
                ResultValues.CHECKSUM_REPORT_FILE: "checksum.md5",
                ResultValues.FILENAME: "file2.jp2",
                ResultValues.VALID: True,
            }),
        ]
        report = workflow.generate_report(results=results, **user_args)
        assert "All 2 passed checksum validation." in report

    def test_generate_report_failure(self, workflow, default_options):
        user_args = default_options.copy()
        ResultValues = workflow_verify_checksums.ResultValues
        results = [
            speedwagon.tasks.Result(workflow_verify_checksums.ChecksumTask, {
                ResultValues.CHECKSUM_REPORT_FILE: "checksum.md5",
                ResultValues.FILENAME: "file1.jp2",
                ResultValues.VALID: False,
            }),
            speedwagon.tasks.Result(workflow_verify_checksums.ChecksumTask, {
                ResultValues.CHECKSUM_REPORT_FILE: "checksum.md5",
                ResultValues.FILENAME: "file2.jp2",
                ResultValues.VALID: False,
            }),
        ]
        report = workflow.generate_report(results=results, **user_args)
        assert "2 files failed checksum validation." in report


class TestChecksumTask:
    def test_work_matching(self, monkeypatch):
        JobValues = workflow_verify_checksums.JobValues
        job_args = {
            JobValues.ITEM_FILENAME.value: "file.txt",
            JobValues.SOURCE_REPORT.value: "checksum.md5",
            JobValues.EXPECTED_HASH.value: "42312efb063c44844cd96e47a19e3441",
            JobValues.ROOT_PATH.value: os.path.join("some", "path"),
        }

        calculate_md5 = Mock(return_value='42312efb063c44844cd96e47a19e3441')
        monkeypatch.setattr(
            workflow_verify_checksums.hathi_validate.process,
            "calculate_md5",
            calculate_md5
        )

        task = workflow_verify_checksums.ChecksumTask(**job_args)

        ResultValues = workflow_verify_checksums.ResultValues
        assert task.work() is True
        assert task.results[ResultValues.FILENAME] == "file.txt" and \
               task.results[ResultValues.VALID] is True

    def test_work_non_matching(self, monkeypatch):
        JobValues = workflow_verify_checksums.JobValues
        job_args = {
            JobValues.ITEM_FILENAME.value: "file.txt",
            JobValues.SOURCE_REPORT.value: "checksum.md5",
            JobValues.EXPECTED_HASH.value: "42312efb063c44844cd96e47a19e3441",
            JobValues.ROOT_PATH.value: os.path.join("some", "path"),
        }

        calculate_md5 = Mock(return_value='something_else')
        monkeypatch.setattr(
            workflow_verify_checksums.hathi_validate.process,
            "calculate_md5",
            calculate_md5
        )

        task = workflow_verify_checksums.ChecksumTask(**job_args)

        ResultValues = workflow_verify_checksums.ResultValues
        assert task.work() is True
        assert task.results[ResultValues.FILENAME] == "file.txt" and \
               task.results[ResultValues.VALID] is False


@pytest.mark.parametrize(
    "task",
    [
        workflow_verify_checksums.ChecksumTask(
            **{
                workflow_verify_checksums.JobValues.ITEM_FILENAME.value:
                    "file.txt",
                workflow_verify_checksums.JobValues.SOURCE_REPORT.value:
                    "checksum.md5",
                workflow_verify_checksums.JobValues.EXPECTED_HASH.value:
                    "42312efb063c44844cd96e47a19e3441",
                workflow_verify_checksums.JobValues.ROOT_PATH.value:
                    os.path.join("some", "path"),
            }
        ),
        workflow_verify_checksums.ValidateChecksumTask(
            file_name="file_name",
            file_path="file_path",
            expected_hash="42312efb063c44844cd96e47a19e3441",
            source_report="source_report"

        ),
        workflow_verify_checksums.ReadChecksumReportTask(
            checksum_file="checksum_file"
        )
    ]
)
def test_tasks_have_description(task):
    assert task.task_description() is not None
