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
