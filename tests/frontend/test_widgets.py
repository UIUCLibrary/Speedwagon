import os
from typing import Union, Optional, Any, List
from unittest.mock import Mock

import pytest


QtCore = pytest.importorskip("PySide6.QtCore")
from PySide6 import QtWidgets, QtGui

import speedwagon.workflow
import speedwagon.frontend.qtwidgets.widgets
import speedwagon.frontend.qtwidgets.models

class TestDropDownWidget:
    def test_empty_widget_metadata(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.ComboWidget(
            widget_metadata={},
            parent=parent
        )
        qtbot.addWidget(parent)
        assert isinstance(widget, QtWidgets.QWidget)

    def test_data_updating(self, qtbot):

        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        widget = speedwagon.frontend.qtwidgets.widgets.ComboWidget(
            parent=parent,
            widget_metadata={
                "selections": ["spam", "bacon", "eggs"]
            }
        )
        qtbot.addWidget(widget)
        starting_data = widget.data
        widget.combo_box.setCurrentIndex(0)
        first_index_data = widget.data
        assert starting_data is None and first_index_data == "spam"

    def test_placeholder_text(self, qtbot):
        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        widget = speedwagon.frontend.qtwidgets.widgets.ComboWidget(
            parent=parent,
            widget_metadata={
                "selections": ["spam", "bacon", "eggs"],
                "placeholder_text": "Dummy"
            }
        )
        qtbot.addWidget(widget)
        assert widget.combo_box.placeholderText() == "Dummy"


class TestCheckBoxWidget:
    def test_empty_widget_metadata(self, qtbot):
        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        widget = \
            speedwagon.frontend.qtwidgets.widgets.CheckBoxWidget(
                widget_metadata={},
                parent=parent
            )
        qtbot.addWidget(widget)
        assert isinstance(widget, QtWidgets.QWidget)

    def test_checking_changes_value(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.CheckBoxWidget(
            widget_metadata={},
            parent=parent
        )
        assert widget.data is False
        with qtbot.wait_signal(widget.dataChanged):
            widget.check_box.setChecked(True)
        assert widget.data is True


class TestFileSelectWidget:
    def test_empty_widget_metadata(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
                widget_metadata={},
                parent=parent
            )
        qtbot.addWidget(widget)
        assert isinstance(widget, QtWidgets.QWidget)

    def test_browse_dir_valid(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
            widget_metadata={},
            parent=parent
        )
        fake_file_path = "/some/directory/file"
        with qtbot.wait_signal(widget.dataChanged):
            widget.browse_file(get_file_callback=lambda: fake_file_path)
        assert widget.data == fake_file_path

    def test_browse_dir_canceled(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
                widget_metadata={},
                parent=parent
            )
        widget.browse_file(get_file_callback=lambda: None)
        assert widget.data is None

    def test_drop_acceptable_data(self, qtbot, monkeypatch):

        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
                widget_metadata={},
                parent=parent
            )
        mime_data = Mock(
            urls=Mock(
                return_value=[
                    Mock(path=Mock(return_value="fakepath"))
                ]
            )
        )
        monkeypatch.setattr(os.path, "exists", lambda *_: True)
        monkeypatch.setattr(os.path, "isdir", lambda *_: False)
        assert widget.drop_acceptable_data(mime_data) is True

    def test_drop_acceptable_data_no_url(self, qtbot, monkeypatch):

        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
                widget_metadata={},
                parent=parent
            )
        mime_data = Mock(
            hasUrls=Mock(return_value=False),
            urls=Mock(
                return_value=[
                    Mock(path=Mock(return_value="fakepath"))
                ]
            )
        )
        monkeypatch.setattr(os.path, "exists", lambda *_: True)
        monkeypatch.setattr(os.path, "isdir", lambda *_: False)
        assert widget.drop_acceptable_data(mime_data) is False

    def test_drop_acceptable_data_no_multiple_files(self, qtbot, monkeypatch):

        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
                widget_metadata={},
                parent=parent
            )
        mime_data = Mock(
            hasUrls=Mock(return_value=True),
            urls=Mock(
                return_value=[
                    Mock(path=Mock(return_value="fake_file1")),
                    Mock(path=Mock(return_value="fake_file2")),
                ]
            )
        )
        monkeypatch.setattr(os.path, "exists", lambda *_: True)
        monkeypatch.setattr(os.path, "isdir", lambda *_: False)
        assert widget.drop_acceptable_data(mime_data) is False

    def test_extract_path_from_event(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
                widget_metadata={},
                parent=parent
            )
        event = Mock(
            mimeData=Mock(
                return_value=Mock(
                    urls=Mock(
                        return_value=[
                            Mock(path=Mock(return_value="fakepath"))
                        ]
                    )
                )
            )
        )
        assert widget.extract_path_from_event(event) == "fakepath"


class TestDirectorySelectWidget:
    def test_empty_widget_metadata(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
                widget_metadata={},
                parent=parent
            )
        assert isinstance(widget, QtWidgets.QWidget)

    def test_browse_dir_valid(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
                widget_metadata={},
                parent=parent
            )
        fake_directory = "/some/directory"
        with qtbot.wait_signal(widget.dataChanged):
            widget.browse_dir(get_file_callback=lambda: fake_directory)
        assert widget.data == fake_directory

    def test_browse_dir_canceled(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
                widget_metadata={},
                parent=parent
            )
        widget.browse_dir(get_file_callback=lambda: None)
        assert widget.data is None

    def test_drag_drop_success(self, qtbot, monkeypatch):
        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
                widget_metadata={},
                parent=parent
            )

        watched = Mock()
        event = Mock(
            type=Mock(return_value=QtGui.QDropEvent.Type.DragEnter),
            Type=Mock(DragEnter=QtGui.QDropEvent.Type.DragEnter)
        )
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget,
            "drop_acceptable_data",
            lambda *_: True
        )
        widget.eventFilter(watched, event)
        assert event.accept.called is True

    def test_drag_invalid(self, qtbot, monkeypatch):
        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
                widget_metadata={},
                parent=parent
            )

        watched = Mock()
        event = Mock(
            type=Mock(return_value=QtGui.QDropEvent.Type.DragEnter),
            Type=Mock(DragEnter=QtGui.QDropEvent.Type.DragEnter)
        )
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget,
            "drop_acceptable_data",
            lambda *_: False
        )
        widget.eventFilter(watched, event)
        assert event.accept.called is False

    def test_drop(self, qtbot, monkeypatch, mocker):
        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
                widget_metadata={},
                parent=parent
            )
        setText = mocker.spy(widget.edit, "setText")
        watched = Mock()
        event = Mock(
            type=Mock(return_value=QtGui.QDropEvent.Type.Drop),
            Type=Mock(Drop=QtGui.QDropEvent.Type.Drop)
        )
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.widgets.FileSystemItemSelectWidget,
            "extract_path_from_event",
            lambda *_: 'some folder'
        )
        widget.eventFilter(watched, event)
        setText.assert_called_once_with('some folder')

    def test_drop_acceptable_data(self, qtbot, monkeypatch):

        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
                widget_metadata={},
                parent=parent
            )
        mime_data = Mock(
            urls=Mock(
                return_value=[
                    Mock(path=Mock(return_value="fakepath"))
                ]
            )
        )
        monkeypatch.setattr(os.path, "exists", lambda *_: True)
        monkeypatch.setattr(os.path, "isdir", lambda *_: True)
        assert widget.drop_acceptable_data(mime_data) is True

    def test_drop_acceptable_data_has_no_urls(self, qtbot, monkeypatch):

        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
                widget_metadata={},
                parent=parent
            )
        mime_data = Mock(
            hasUrls=Mock(return_value=False),
            urls=Mock(
                return_value=[
                    Mock(path=Mock(return_value="fakepath"))
                ]
            )
        )
        monkeypatch.setattr(os.path, "exists", lambda *_: True)
        monkeypatch.setattr(os.path, "isdir", lambda *_: True)
        assert widget.drop_acceptable_data(mime_data) is False
    def test_drop_acceptable_data_reject_multiple_folders(self, qtbot, monkeypatch):

        parent = QtWidgets.QWidget()
        widget = \
            speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
                widget_metadata={},
                parent=parent
            )
        mime_data = Mock(
            hasUrls=Mock(return_value=True),
            urls=Mock(
                return_value=[
                    Mock(path=Mock(return_value="fakepath1")),
                    Mock(path=Mock(return_value="fakepath2"))
                ]
            )
        )
        monkeypatch.setattr(os.path, "exists", lambda *_: True)
        monkeypatch.setattr(os.path, "isdir", lambda *_: True)
        assert widget.drop_acceptable_data(mime_data) is False

class TestDynamicForm:
    def test_update_model_boolean(self, qtbot):
        form = speedwagon.frontend.qtwidgets.widgets.DynamicForm()
        data = [
            speedwagon.workflow.BooleanSelect("spam"),
            speedwagon.workflow.BooleanSelect("bacon")
        ]
        model = speedwagon.frontend.qtwidgets.models.ToolOptionsModel4(data)
        form.set_model(model)
        checkbox: speedwagon.frontend.qtwidgets.widgets.CheckBoxWidget = form._background.widgets['spam']
        assert form._background.widgets['spam'].data is False
        checkbox.check_box.setChecked(True)
        qtbot.wait_until(lambda : form._background.widgets['spam'].data is True)
        form.update_model()
        assert model.data(model.index(0, 0)) is True
        assert model.data(model.index(1, 0)) is False

    def test_update_model_file_select(self, qtbot):
        form = speedwagon.frontend.qtwidgets.widgets.DynamicForm()
        data = [
            speedwagon.workflow.FileSelectData("input"),
            speedwagon.workflow.FileSelectData("output")
        ]
        model = speedwagon.frontend.qtwidgets.models.ToolOptionsModel4(data)

        form.set_model(model)
        qtbot.keyClicks(form._background.widgets['input'].edit, "/someinput/file.txt")
        qtbot.keyClicks(form._background.widgets['output'].edit, "/output/file.txt")

        form.update_model()
        assert model.data(model.index(0, 0)) == "/someinput/file.txt"
        assert model.data(model.index(1, 0)) == "/output/file.txt"

    def test_update_model_combobox(self, qtbot):
        form = speedwagon.frontend.qtwidgets.widgets.DynamicForm()
        option = speedwagon.workflow.ChoiceSelection('choice 1')
        option.add_selection("spam")
        option.add_selection("bacon")
        data = [
            option
        ]
        model = speedwagon.frontend.qtwidgets.models.ToolOptionsModel4(data)

        form.set_model(model)
        combobox: speedwagon.frontend.qtwidgets.widgets.ComboWidget = form._background.widgets['choice 1']
        combobox.combo_box.setCurrentIndex(1)
        form.update_model()

        assert model.data(model.index(0, 0)) == "bacon"

    def test_paint_event_calls_draw_primitive(self, qtbot, monkeypatch):
        form = speedwagon.frontend.qtwidgets.widgets.InnerForm()
        event = Mock(height=Mock(return_value=10))

        device = Mock(
            name="device",
            height=Mock(return_value=480),
            width=Mock(return_value=640)
        )

        drawPrimitive = Mock()

        monkeypatch.setattr(
            QtWidgets.QStylePainter,
            "device",
            Mock(return_value=device)
        )

        monkeypatch.setattr(
            QtWidgets.QStylePainter,
            "drawPrimitive",
            drawPrimitive
        )

        form.paintEvent(event)
        assert drawPrimitive.called is True
