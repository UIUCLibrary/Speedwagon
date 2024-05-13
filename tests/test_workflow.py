from unittest.mock import Mock

import speedwagon.workflow
from speedwagon import validators
import pytest


class TestDropDownSelection:
    def test_serialize_selection(self):
        data = speedwagon.workflow.ChoiceSelection("Dummy")
        data.add_selection("Spam")
        assert "Spam" in data.serialize()['selections']


def test_AbsOutputOptionDataType_needs_widget_name():
    with pytest.raises(TypeError):
        class BadClass(speedwagon.workflow.AbsOutputOptionDataType):
            pass
        BadClass(label="Dummy")


class TestAbsOutputOptionDataType:
    def test_validation(self):
        name_argument = speedwagon.workflow.TextLineEditData("First Name")
        name_argument.value = "Henry"

        class Spam(validators.AbsOutputValidation):
            def investigate(self, candidate, job_options):
                return []

        validator = Spam()
        name_argument.add_validation(validator)
        assert name_argument.get_findings() == []

    def test_validation_adds_to_findings(self):
        name_argument = speedwagon.workflow.TextLineEditData("First Name")
        name_argument.value = "Henry1"
        name_argument.add_validation(
            validators.CustomValidation[str](
                query=lambda candidate, _: candidate.isalpha(),
                failure_message_function=lambda candidate: (
                    f"{candidate} contains non-alphanumerical characters"
                )
            )
        )
        assert name_argument.get_findings() == [
            'Henry1 contains non-alphanumerical characters'
        ]

    def test_default_condition_validates(self):
        name_argument = speedwagon.workflow.TextLineEditData("First Name")
        name_argument.value = "Henry"
        validation = Mock(findings=[])
        name_argument.add_validation(validation)
        assert name_argument.get_findings() == []
        assert validation.validate.called is True

    def test_false_condition_does_not_validate(self):
        name_argument = speedwagon.workflow.TextLineEditData("First Name")
        name_argument.value = "Henry"
        validation = Mock(findings=[])
        name_argument.add_validation(
            validation,  condition=lambda *_, **__: False
        )
        assert name_argument.get_findings() == []
        assert validation.validate.called is False
