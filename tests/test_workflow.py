import speedwagon.workflow
import pytest


class TestDropDownSelection:
    def test_serialize_selection(self):
        data = speedwagon.workflow.DropDownSelection("Dummy")
        data.add_selection("Spam")
        assert "Spam" in data.serialize()['selections']


def test_AbsOutputOptionDataType_needs_widget_name():
    with pytest.raises(TypeError):
        class BadClass(speedwagon.workflow.AbsOutputOptionDataType):
            pass
        BadClass(label="Dummy")
