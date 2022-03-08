import pytest
from PySide6 import QtWidgets, QtCore

import speedwagon.widgets
import speedwagon.models


class TestDelegateSelection:
    @pytest.fixture
    def model(self):
        return speedwagon.models.ToolOptionsModel4(data=[
            speedwagon.widgets.FileSelectData('Spam'),
        ])

    def test_returns_a_qt_widget(
            self,
            qtbot,
            model: speedwagon.models.ToolOptionsModel4
    ):
        delegate_widget = speedwagon.widgets.DelegateSelection()
        parent = QtWidgets.QWidget()
        options = QtWidgets.QStyleOptionViewItem()
        index = model.createIndex(0, 0)
        editor_widget = delegate_widget.createEditor(parent, options, index)
        assert isinstance(editor_widget, QtWidgets.QWidget)

