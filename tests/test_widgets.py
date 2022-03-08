import typing
from unittest.mock import Mock

import pytest
from PySide6 import QtWidgets, QtCore

import speedwagon.widgets
import speedwagon.models
import re


class TestWidgets:
    @pytest.fixture
    def widget_label_value(self):
        return "Spam"

    @pytest.fixture
    def text_edit_widget(self, widget_label_value):
        return speedwagon.widgets.TextLineEditWidget(widget_label_value)

    def test_qt_out(self,
                    qtbot,
                    text_edit_widget: speedwagon.widgets.TextLineEditWidget,
                    widget_label_value):
        context_renderer = speedwagon.widgets.QtOptionWidgetBuilder()
        context_renderer.build(text_edit_widget)
        out_widget = context_renderer.get_qt_widget()
        assert isinstance(out_widget, QtWidgets.QWidget)

    def test_qt_out_label(
            self,
            qtbot,
            text_edit_widget: speedwagon.widgets.TextLineEditWidget,
            widget_label_value: str
    ):
        context_renderer = speedwagon.widgets.QtOptionWidgetBuilder()
        context_renderer.build(text_edit_widget)
        out_widget = context_renderer.get_qt_widget()
        assert typing.cast(QtWidgets.QLineEdit, out_widget).text() == \
               widget_label_value

    @pytest.fixture()
    def selection_options(self):
        return [
            "Spam",
            "Bacon",
            "eggs"
        ]

    @pytest.fixture()
    def selection_widget(self, selection_options):
        selection_widget = speedwagon.widgets.DropDownSelection("Order")
        for selection in selection_options:
            selection_widget.add_selection(label=selection)
        return selection_widget

    def test_qt_drop_down_gets_combo_box(self, qtbot, selection_widget):
        context_builder = speedwagon.widgets.QtOptionWidgetBuilder()
        context_builder.build(selection_widget)
        out_widget: QtWidgets.QComboBox = context_builder.get_qt_widget()
        assert isinstance(out_widget, QtWidgets.QComboBox)

    def test_qt_drop_down_gets_options(self, qtbot, selection_widget, selection_options):
        context_builder = speedwagon.widgets.QtOptionWidgetBuilder()
        context_builder.build(selection_widget)
        out_widget: QtWidgets.QComboBox = context_builder.get_qt_widget()
        assert out_widget.count() == len(selection_options)


class TestFileSelectWidget:
    def test_qt(self, qtbot):
        widget = speedwagon.widgets.FileSelectData("Checksum File")
        widget.file_selection_filter = "Checksum files (*.md5)"
        context_builder = speedwagon.widgets.QtOptionWidgetBuilder()
        context_builder.build(widget)
        qt_widget = context_builder.get_qt_widget()
        assert isinstance(qt_widget, QtWidgets.QWidget)


class TestFolderSelectWidget:
    def test_qt(self, qtbot):
        widget = speedwagon.widgets.DirectorySelect("Batch directory")
        context_builder = speedwagon.widgets.QtOptionWidgetBuilder()
        context_builder.build(widget)
        qt_widget = context_builder.get_qt_widget()
        assert isinstance(qt_widget, QtWidgets.QWidget)


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

