import os
from typing import Union, Optional, Any, List

import pytest


QtCore = pytest.importorskip("PySide6.QtCore")
from PySide6 import QtWidgets

import speedwagon.workflow
import speedwagon.frontend.qtwidgets.widgets
import speedwagon.frontend.qtwidgets.models

class TestDropDownWidget:
    def test_empty_widget_metadata(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.ComboWidget(parent=parent)
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
            speedwagon.frontend.qtwidgets.widgets.CheckBoxWidget(parent=parent)
        qtbot.addWidget(widget)
        assert isinstance(widget, QtWidgets.QWidget)

    def test_checking_changes_value(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.CheckBoxWidget(parent)
        assert widget.data is False
        with qtbot.wait_signal(widget.dataChanged):
            widget.check_box.setChecked(True)
        assert widget.data is True


class TestFileSelectWidget:
    def test_empty_widget_metadata(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(parent=parent)
        qtbot.addWidget(widget)
        assert isinstance(widget, QtWidgets.QWidget)

    def test_browse_dir_valid(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(parent=parent)
        fake_file_path = "/some/directory/file"
        with qtbot.wait_signal(widget.dataChanged):
            widget.browse_file(get_file_callback=lambda: fake_file_path)
        assert widget.data == fake_file_path

    def test_browse_dir_canceled(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(parent=parent)
        widget.browse_file(get_file_callback=lambda: None)
        assert widget.data is None


class TestDirectorySelectWidget:
    def test_empty_widget_metadata(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(parent=parent)
        assert isinstance(widget, QtWidgets.QWidget)

    def test_browse_dir_valid(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(parent=parent)
        fake_directory = "/some/directory"
        with qtbot.wait_signal(widget.dataChanged):
            widget.browse_dir(get_file_callback=lambda: fake_directory)
        assert widget.data == fake_directory

    def test_browse_dir_canceled(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(parent=parent)
        widget.browse_dir(get_file_callback=lambda: None)
        assert widget.data is None

# def test_clicking_outside(qtbot, mocker):
#     # window = QtWidgets.QMainWindow()
#     parent = QtWidgets.QWidget()
#     # window.setCentralWidget(parent)
#     layout = QtWidgets.QVBoxLayout()
#     parent.setLayout(layout)
#     widget = speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget()
#     text_box = QtWidgets.QLineEdit()
#     text_box2 = QtWidgets.QLineEdit()
#     layout.addWidget(text_box)
#     layout.addWidget(text_box2)
#     layout.addWidget(widget)
#
#     # spy = mocker.spy(widget.edit, "closeEvent")
#     # widget.setFocus()
#     # text_box.setFocus()
#     # assert spy.call_count == 1
#
#     # with qtbot.wait_signal(table.editorOpened, raising=False) as blocker:
#     # qtbot.staticmouseDClick(widget, QtCore.Qt.MouseButton.LeftButton)
#     # qtbot.mouseClick(widget, QtCore.Qt.MouseButton.LeftButton)
#     # qtbot.mouseClick(widget, QtCore.Qt.MouseButton.LeftButton)
#     # qtbot.wait_until(lambda: widget.hasFocus())
#     # assert widget.hasFocus()
#
#     w = QtWidgets.QDialog()
#     w.setFixedWidth(300)
#     w.setFixedHeight(300)
#     w.setLayout(QtWidgets.QVBoxLayout())
#     w.layout().addWidget(parent)
#     w.exec()
#
#     # w.setLayout(layout)
#     # path = qtbot.screenshot(window)
#     # os.system(f"open {path}")
#     # print(path)


# def test_clicking_outside_table_closes_editor(qtbot):
#     layout = QtWidgets.QVBoxLayout()
#     pushButton = QtWidgets.QPushButton('outside of table')
#     layout.addWidget(pushButton)
#     data = [
#         speedwagon.workflow.FileSelectData("input"),
#         speedwagon.workflow.FileSelectData("output")
#     ]
#     model = speedwagon.frontend.qtwidgets.models.ToolOptionsModel4(data)
#     table = speedwagon.frontend.qtwidgets.widgets.EditSettingsTable()
#     layout.addWidget(table)
#     table.setModel(model)
#
#     with qtbot.wait_signal(table.editorOpened, raising=False) as blocker:
#         index = model.index(0,0)
#         assert index.isValid()
#         rect = table.visualRect(index)
#         qtbot.mouseClick(table.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=rect.center())
#         qtbot.mouseClick(table.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=rect.center())
#     assert blocker.signal_triggered, "table delegate editor never opened"
#
#     with qtbot.wait_signal(table._delegate.closed, raising=False) as blocker:
#         pushButton.setFocus()
#         # qtbot.mouseClick(pushButton, QtCore.Qt.MouseButton.LeftButton)
#     assert blocker.signal_triggered, "table delegate editor never closed"

    # w = QtWidgets.QDialog()
    # w.setFixedWidth(300)
    # w.setFixedHeight(300)
    # w.setLayout(layout)
    # # path = qtbot.screenshot(table)
    # # print(path)
    # w.exec()
#
# #
# def test_init(qtbot):
#     dialog_box = QtWidgets.QDialog()
#     table = QtWidgets.QTableView(parent=dialog_box)
#     table.setEditTriggers(table.AllEditTriggers)
#     layout = QtWidgets.QVBoxLayout()
#     dialog_box.setLayout(layout)
#     dialog_box.layout().addWidget(table)
#     qtbot.addWidget(table)
#     spam_dir = speedwagon.widgets.FileSelectData('Spam')
#     spam_dir.placeholder_text = "Select a spam"
#
#     # user_args.append(spam_dir)
#
#     drop_down = speedwagon.widgets.DropDownSelection("Dummy")
#     # drop_down.value = "Option 2"
#     drop_down.placeholder_text = "Select an option"
#     drop_down.add_selection("Option 1")
#     drop_down.add_selection("Option 2")
#
#     # user_args.append(drop_down)
#
#     user_args = [
#         spam_dir,
#         drop_down
#
#     ]
#     model = speedwagon.models.ToolOptionsModel4(data=user_args)
#     table.setModel(model)
#     delegate = speedwagon.widgets.QtWidgetDelegateSelection()
#     table.setItemDelegate(delegate)
#     dialog_box.exec()


class TestDynamicForm:
    def test_update_model_boolean(self, qtbot):
        form = speedwagon.frontend.qtwidgets.widgets.DynamicForm()
        data = [
            speedwagon.workflow.BooleanSelect("spam"),
            speedwagon.workflow.BooleanSelect("bacon")
        ]
        model = speedwagon.frontend.qtwidgets.models.ToolOptionsModel4(data)
        form.setModel(model)
        checkbox: speedwagon.frontend.qtwidgets.widgets.CheckBoxWidget = form.widgets['spam']
        assert form.widgets['spam'].data is False
        checkbox.check_box.setChecked(True)
        qtbot.wait_until(lambda : form.widgets['spam'].data is True)
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

        form.setModel(model)
        qtbot.keyClicks(form.widgets['input'].edit, "/someinput/file.txt")
        qtbot.keyClicks(form.widgets['output'].edit, "/output/file.txt")

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

        form.setModel(model)
        combobox: speedwagon.frontend.qtwidgets.widgets.ComboWidget = form.widgets['choice 1']
        combobox.combo_box.setCurrentIndex(1)
        form.update_model()

        assert model.data(model.index(0, 0)) == "bacon"
