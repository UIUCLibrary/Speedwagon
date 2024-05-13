import pytest

from speedwagon import validators


class TestOptionValidator:
    class ValidateNameStartsWithLetter(
        validators.AbsOutputValidation[str, str]
    ):
        def investigate(self, candidate: str, job_options):
            findings = []
            if candidate != "" and not candidate[0].isalpha():
                findings.append("Not an alpha")
            return findings

    def test_investigate_find_nothing(self):
        name_validator = TestOptionValidator.ValidateNameStartsWithLetter()
        assert name_validator.investigate("hello", {}) == []

    def test_investigate_find_something(self):
        name_validator = TestOptionValidator.ValidateNameStartsWithLetter()
        assert name_validator.investigate("0", {}) == ["Not an alpha"]

    @pytest.fixture
    def validate_alpha_invalid(self, ):
        name_validator = TestOptionValidator.ValidateNameStartsWithLetter()
        name_validator.candidate = "0"
        return name_validator

    @pytest.fixture
    def validate_alpha_valid(self, ):
        name_validator = TestOptionValidator.ValidateNameStartsWithLetter()
        name_validator.candidate = "Henry"
        return name_validator

    def test_validate_with_findings(self, validate_alpha_invalid):
        name_validator = validate_alpha_invalid
        name_validator.validate()
        assert len(name_validator.findings) > 0

    def test_validate_with_no_findings(self, validate_alpha_valid):
        name_validator = validate_alpha_valid
        name_validator.validate()
        assert len(validate_alpha_valid.findings) == 0

    def test_reset(self, validate_alpha_invalid):
        name_validator = validate_alpha_invalid
        name_validator.validate()
        number_of_findings_after_validating = len(name_validator.findings)
        name_validator.reset()
        number_of_findings_after_resetting = len(name_validator.findings)
        assert (
            number_of_findings_after_validating > 0 and
            number_of_findings_after_resetting == 0
        ), (f"Expected to start with more than zero finding and end with "
            f"zero findings, got {number_of_findings_after_validating} "
            f"and {number_of_findings_after_resetting}")

    def test_validation_without_running_validate_is_none(
        self,
        validate_alpha_valid
    ):
        assert validate_alpha_valid.is_valid is None

    def test_validation_is_valid_with_valid_results(
        self,
        validate_alpha_valid
    ):
        validate_alpha_valid.validate()
        assert validate_alpha_valid.is_valid is True

    def test_validation_is_valid_with_invalid_results(
        self,
        validate_alpha_invalid
    ):
        validate_alpha_invalid.validate()
        assert validate_alpha_invalid.is_valid is False

    def test_validation_is_valid_is_none_after_reset(
        self,
        validate_alpha_invalid
    ):
        validate_alpha_invalid.validate()
        validate_alpha_invalid.reset()
        assert validate_alpha_invalid.is_valid is None

    def test_validating_with_no_candidate_raises_value_error(self):
        name_validator = TestOptionValidator.ValidateNameStartsWithLetter()
        with pytest.raises(ValueError):
            name_validator.validate()


class TestFileExistsValidation:
    @pytest.fixture()
    def failed_validation(self):
        validator = validators.ExistsOnFileSystem()
        validator.path_exists = lambda *_, **kwargs: False
        validator.candidate = "some_non_existing_file.txt"
        validator.validate()
        return validator

    def test_invalid_file_is_invalid(self, failed_validation):
        assert failed_validation.is_valid is False

    def test_invalid_file_explains_in_findings(self, failed_validation):
        expected_error_message = (
            validators
            .ExistsOnFileSystem
            .default_message_template
            .format("some_non_existing_file.txt")
        )
        assert expected_error_message in failed_validation.findings

    def test_valid_file_existing_validated_true(self):
        validator = validators.ExistsOnFileSystem()
        validator.path_exists = lambda *_, **kwargs: True
        validator.candidate = "some_valid_file.txt"
        validator.validate()
        assert validator.is_valid is True

    def test_fild_exists(self, monkeypatch):
        monkeypatch.setattr(validators.os.path, "exists", lambda *_: True)
        assert validators.ExistsOnFileSystem.path_exists("valid_file") is True


class TestCustomValidation:
    def test_always_invalid(self):
        def candidate_always_invalid(*_, **__):
            return False
        validator = validators.CustomValidation(query=candidate_always_invalid)
        validator.candidate = "dummy"
        validator.validate()
        assert validator.is_valid is False

    def test_always_valid(self):
        def candidate_always_valid(*_, **__):
            return True
        validator = validators.CustomValidation(query=candidate_always_valid)
        validator.candidate = "dummy"
        validator.validate()
        assert validator.is_valid is True

    def test_invalid_uses_custom_message(self):
        def candidate_always_invalid(*_, **__):
            return False

        def generate_finding_from_failure(candidate):
            return f"I do not want {candidate}"

        validator = validators.CustomValidation(query=candidate_always_invalid)
        validator.generate_finding_message = generate_finding_from_failure
        validator.candidate = "spam"
        validator.validate()
        assert "I do not want spam" in validator.findings


class TestIsDirectoryValidation:
    def test_invalid_result_uses_message_template(self):
        validation = validators.IsDirectory()
        validation.candidate = "invalid directory"
        validation.checking_strategy = lambda _: False
        validation.validate()
        assert validation.invalid_input_message_template.format(
            "invalid directory"
        ) in validation.findings

    def test_valid_result_no_findings(self):
        validation = validators.IsDirectory()
        validation.candidate = "valid/directory"
        validation.checking_strategy = lambda _: True
        validation.validate()
        assert validation.findings == []


class TestIsFile:
    def test_invalid_result_uses_message_template(self):
        validation = validators.IsFile()
        validation.candidate = "invalid file"
        validation.is_file = lambda _: False
        validation.validate()
        assert validation.default_message_template.format(
            "invalid file"
        ) in validation.findings

    def test_valid_result_no_findings(self):
        validation = validators.IsFile()
        validation.candidate = "valid/file.txt"
        validation.checking_strategy = lambda _: True
        validation.validate()
        assert validation.findings == []
