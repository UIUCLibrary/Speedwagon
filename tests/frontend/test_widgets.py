import logging
import os
from unittest.mock import Mock

import pytest

QtCore = pytest.importorskip("PySide6.QtCore")
from PySide6 import QtWidgets, QtGui, QtCore
from typing import List, TypedDict, Sequence
import sys

if sys.version_info < (3, 10):
    import importlib_metadata as metadata
else:
    from importlib import metadata

import speedwagon.workflow
import speedwagon.frontend.qtwidgets.widgets
from speedwagon.frontend.qtwidgets.models import options as option_models
from speedwagon.frontend.qtwidgets import models
from speedwagon.frontend.qtwidgets import (
    user_interaction as qt_user_interaction,
)
from speedwagon.frontend.cli import user_interaction as cli_user_interaction
from speedwagon.frontend import interaction
from speedwagon import Workflow
from speedwagon.config import StandardConfigFileLocator


class TestDropDownWidget:
    def test_empty_widget_metadata(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.ComboWidget(
            widget_metadata={}, parent=parent
        )
        qtbot.addWidget(parent)
        assert isinstance(widget, QtWidgets.QWidget)

    def test_data_updating(self, qtbot):

        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        widget = speedwagon.frontend.qtwidgets.widgets.ComboWidget(
            parent=parent,
            widget_metadata={"selections": ["spam", "bacon", "eggs"]},
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
                "placeholder_text": "Dummy",
            },
        )
        qtbot.addWidget(widget)
        assert widget.combo_box.placeholderText() == "Dummy"

    def test_get_selections(self, qtbot):
        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        widget = speedwagon.frontend.qtwidgets.widgets.ComboWidget(
            parent=parent,
            widget_metadata={
                "selections": ["spam", "bacon", "eggs"],
                "placeholder_text": "Dummy",
            },
        )
        qtbot.addWidget(widget)
        assert widget.get_selections() == ["spam", "bacon", "eggs"]

    def test_no_layout(self, caplog, qtbot, monkeypatch):
        parent = QtWidgets.QWidget()
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.widgets.ComboWidget,
            "layout",
            lambda *_: None
        )
        qtbot.addWidget(
            speedwagon.frontend.qtwidgets.widgets.ComboWidget(
                widget_metadata={}, parent=parent
            )
        )
        assert "has no layout" in caplog.text


class TestCheckBoxWidget:
    def test_empty_widget_metadata(self, qtbot):
        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        widget = speedwagon.frontend.qtwidgets.widgets.CheckBoxWidget(
            widget_metadata={}, parent=parent
        )
        qtbot.addWidget(widget)
        assert isinstance(widget, QtWidgets.QWidget)

    def test_checking_changes_value(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.CheckBoxWidget(
            widget_metadata={}, parent=parent
        )
        assert widget.data is False
        with qtbot.wait_signal(widget.dataChanged):
            widget.check_box.setChecked(True)
        assert widget.data is True
    def test_no_layout(self, caplog, qtbot, monkeypatch):
        parent = QtWidgets.QWidget()
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.widgets.CheckBoxWidget,
            "layout",
            lambda *_: None
        )
        qtbot.addWidget(
            speedwagon.frontend.qtwidgets.widgets.CheckBoxWidget(
                widget_metadata={}, parent=parent
            )
        )
        assert "has no layout" in caplog.text

class TestFileSelectWidget:
    def test_empty_widget_metadata(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
            widget_metadata={}, parent=parent
        )
        qtbot.addWidget(widget)
        assert isinstance(widget, QtWidgets.QWidget)

    def test_browse_dir_valid(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
            widget_metadata={}, parent=parent
        )
        fake_file_path = "/some/directory/file"
        with qtbot.wait_signal(widget.dataChanged):
            widget.browse_file(get_file_callback=lambda: fake_file_path)
        assert widget.data == fake_file_path

    def test_browse_dir_canceled(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
            widget_metadata={}, parent=parent
        )
        widget.browse_file(get_file_callback=lambda: None)
        assert widget.data is None

    def test_drop_acceptable_data(self, qtbot, monkeypatch):

        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
            widget_metadata={}, parent=parent
        )
        mime_data = Mock(
            urls=Mock(return_value=[Mock(path=Mock(return_value="fakepath"))])
        )
        monkeypatch.setattr(os.path, "exists", lambda *_: True)
        monkeypatch.setattr(os.path, "isdir", lambda *_: False)
        assert widget.drop_acceptable_data(mime_data) is True

    def test_drop_acceptable_data_no_url(self, qtbot, monkeypatch):

        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
            widget_metadata={}, parent=parent
        )
        mime_data = Mock(
            hasUrls=Mock(return_value=False),
            urls=Mock(return_value=[Mock(path=Mock(return_value="fakepath"))]),
        )
        monkeypatch.setattr(os.path, "exists", lambda *_: True)
        monkeypatch.setattr(os.path, "isdir", lambda *_: False)
        assert widget.drop_acceptable_data(mime_data) is False

    def test_drop_acceptable_data_no_multiple_files(self, qtbot, monkeypatch):

        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
            widget_metadata={}, parent=parent
        )
        mime_data = Mock(
            hasUrls=Mock(return_value=True),
            urls=Mock(
                return_value=[
                    Mock(path=Mock(return_value="fake_file1")),
                    Mock(path=Mock(return_value="fake_file2")),
                ]
            ),
        )
        monkeypatch.setattr(os.path, "exists", lambda *_: True)
        monkeypatch.setattr(os.path, "isdir", lambda *_: False)
        assert widget.drop_acceptable_data(mime_data) is False

    def test_extract_path_from_event(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
            widget_metadata={}, parent=parent
        )
        event = Mock(
            mimeData=Mock(
                return_value=Mock(
                    urls=Mock(
                        return_value=[
                            Mock(
                                path=Mock(return_value="fakepath"),
                                toLocalFile=Mock(return_value="fakepath"),
                            )
                        ]
                    ),
                )
            )
        )
        assert widget.extract_path_from_event(event) == "fakepath"

    def test_open_default_file_dialog(self, qtbot, monkeypatch):
        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        getOpenFileName = Mock(return_value=("filepath", "..." ))
        monkeypatch.setattr(speedwagon.frontend.qtwidgets.widgets.QtWidgets.QFileDialog, "getOpenFileName", getOpenFileName)
        widget = speedwagon.frontend.qtwidgets.widgets.FileSelectWidget(
            widget_metadata={}, parent=parent
        )
        assert widget.open_default_file_dialog() == "filepath"

class TestDirectorySelectWidget:
    def test_empty_widget_metadata(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
            widget_metadata={}, parent=parent
        )
        assert isinstance(widget, QtWidgets.QWidget)

    def test_browse_dir_valid(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
            widget_metadata={}, parent=parent
        )
        fake_directory = "/some/directory"
        with qtbot.wait_signal(widget.dataChanged):
            widget.browse_dir(get_file_callback=lambda: fake_directory)
        assert widget.data == fake_directory

    def test_browse_dir_canceled(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
            widget_metadata={}, parent=parent
        )
        widget.browse_dir(get_file_callback=lambda: None)
        assert widget.data is None

    def test_drag_drop_success(self, qtbot, monkeypatch):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
            widget_metadata={}, parent=parent
        )

        watched = Mock()
        event = Mock(
            type=Mock(return_value=QtGui.QDropEvent.Type.DragEnter),
            Type=Mock(DragEnter=QtGui.QDropEvent.Type.DragEnter),
        )
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget,
            "drop_acceptable_data",
            lambda *_: True,
        )
        widget.eventFilter(watched, event)
        assert event.accept.called is True

    def test_drag_invalid(self, qtbot, monkeypatch):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
            widget_metadata={}, parent=parent
        )

        watched = Mock()
        event = Mock(
            type=Mock(return_value=QtGui.QDropEvent.Type.DragEnter),
            Type=Mock(DragEnter=QtGui.QDropEvent.Type.DragEnter),
        )
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget,
            "drop_acceptable_data",
            lambda *_: False,
        )
        widget.eventFilter(watched, event)
        assert event.accept.called is False

    def test_drop(self, qtbot, monkeypatch, mocker):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
            widget_metadata={}, parent=parent
        )
        setText = mocker.spy(widget.edit, "setText")
        watched = Mock()
        event = Mock(
            type=Mock(return_value=QtGui.QDropEvent.Type.Drop),
            Type=Mock(Drop=QtGui.QDropEvent.Type.Drop),
        )
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.widgets.FileSystemItemSelectWidget,
            "extract_path_from_event",
            lambda *_: "some folder",
        )
        widget.eventFilter(watched, event)
        setText.assert_called_once_with("some folder")

    def test_drop_acceptable_data(self, qtbot, monkeypatch):

        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
            widget_metadata={}, parent=parent
        )
        mime_data = Mock(
            urls=Mock(return_value=[Mock(path=Mock(return_value="fakepath"))])
        )
        monkeypatch.setattr(os.path, "exists", lambda *_: True)
        monkeypatch.setattr(os.path, "isdir", lambda *_: True)
        assert widget.drop_acceptable_data(mime_data) is True

    def test_drop_acceptable_data_has_no_urls(self, qtbot, monkeypatch):

        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
            widget_metadata={}, parent=parent
        )
        mime_data = Mock(
            hasUrls=Mock(return_value=False),
            urls=Mock(return_value=[Mock(path=Mock(return_value="fakepath"))]),
        )
        monkeypatch.setattr(os.path, "exists", lambda *_: True)
        monkeypatch.setattr(os.path, "isdir", lambda *_: True)
        assert widget.drop_acceptable_data(mime_data) is False

    def test_drop_acceptable_data_reject_multiple_folders(
        self, qtbot, monkeypatch
    ):

        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.DirectorySelectWidget(
            widget_metadata={}, parent=parent
        )
        mime_data = Mock(
            hasUrls=Mock(return_value=True),
            urls=Mock(
                return_value=[
                    Mock(path=Mock(return_value="fakepath1")),
                    Mock(path=Mock(return_value="fakepath2")),
                ]
            ),
        )
        monkeypatch.setattr(os.path, "exists", lambda *_: True)
        monkeypatch.setattr(os.path, "isdir", lambda *_: True)
        assert widget.drop_acceptable_data(mime_data) is False


class TestDynamicForm:
    def test_update_model_boolean(self, qtbot):
        form = speedwagon.frontend.qtwidgets.widgets.DynamicForm()
        data = [
            speedwagon.workflow.BooleanSelect("spam"),
            speedwagon.workflow.BooleanSelect("bacon"),
        ]
        model = option_models.ToolOptionsModel(data)
        form.set_model(model)
        checkbox: speedwagon.frontend.qtwidgets.widgets.CheckBoxWidget = (
            form._background.widgets["spam"]
        )
        assert form._background.widgets["spam"].data is False
        checkbox.check_box.setChecked(True)
        qtbot.wait_until(lambda: form._background.widgets["spam"].data is True)
        form.update_model()
        assert model.data(model.index(0, 0)) is True
        assert model.data(model.index(1, 0)) is False

    def test_update_model_file_select(self, qtbot):
        form = speedwagon.frontend.qtwidgets.widgets.DynamicForm()
        data = [
            speedwagon.workflow.FileSelectData("input"),
            speedwagon.workflow.FileSelectData("output"),
        ]
        model = option_models.ToolOptionsModel(data)

        form.set_model(model)
        qtbot.keyClicks(
            form._background.widgets["input"].edit, "/someinput/file.txt"
        )
        qtbot.keyClicks(
            form._background.widgets["output"].edit, "/output/file.txt"
        )

        form.update_model()
        assert model.data(model.index(0, 0)) == "/someinput/file.txt"
        assert model.data(model.index(1, 0)) == "/output/file.txt"

    def test_update_model_combobox(self, qtbot):
        form = speedwagon.frontend.qtwidgets.widgets.DynamicForm()
        option = speedwagon.workflow.ChoiceSelection("choice 1")
        option.add_selection("spam")
        option.add_selection("bacon")
        data = [option]
        model = option_models.ToolOptionsModel(data)

        form.set_model(model)
        combobox: speedwagon.frontend.qtwidgets.widgets.ComboWidget = (
            form._background.widgets["choice 1"]
        )
        combobox.combo_box.setCurrentIndex(1)
        form.update_model()

        assert model.data(model.index(0, 0)) == "bacon"

    def test_paint_event_calls_draw_primitive(self, qtbot, monkeypatch):
        form = speedwagon.frontend.qtwidgets.widgets.InnerForm()

        device = Mock(
            name="device",
            height=Mock(return_value=480),
            width=Mock(return_value=640),
        )

        drawPrimitive = Mock()

        monkeypatch.setattr(
            QtWidgets.QStylePainter, "device", Mock(return_value=device)
        )

        monkeypatch.setattr(
            QtWidgets.QStylePainter, "drawPrimitive", drawPrimitive
        )
        event = QtGui.QPaintEvent(QtCore.QRect(0, 0, 0, 0))
        form.paintEvent(event)
        assert drawPrimitive.called is True

    def test_is_valid(self, qtbot):
        form = speedwagon.frontend.qtwidgets.widgets.DynamicForm()
        form.is_valid()


class TestPluginConfig:
    def test_no_plugins_by_default(self, qtbot):
        plugin_widget = speedwagon.frontend.qtwidgets.widgets.PluginConfig()
        qtbot.addWidget(plugin_widget)
        assert plugin_widget.enabled_plugins() == {}

    def test_checkbox_selection(self, qtbot):
        plugin_widget = speedwagon.frontend.qtwidgets.widgets.PluginConfig()
        entry_point = Mock(metadata.EntryPoint)
        entry_point.name = "Spam"
        entry_point.module = "SpamPlugins"

        plugin_widget.model.add_entry_point(entry_point)
        qtbot.addWidget(plugin_widget)

        plugin_widget.model.setData(
            plugin_widget.model.index(0, 0),
            QtCore.Qt.CheckState.Checked.value,
            QtCore.Qt.ItemDataRole.CheckStateRole,
        )

        assert plugin_widget.enabled_plugins() == {"SpamPlugins": ["Spam"]}

    @pytest.fixture()
    def plugin_with_spam(self, qtbot):
        plugin_widget = speedwagon.frontend.qtwidgets.widgets.PluginConfig()
        entry_point = Mock(metadata.EntryPoint)
        entry_point.name = "Spam"
        entry_point.module = "Bacon"

        plugin_widget.model.add_entry_point(entry_point)
        qtbot.addWidget(plugin_widget)
        return plugin_widget

    def test_changes_made_signal(self, qtbot, plugin_with_spam):
        with qtbot.wait_signal(plugin_with_spam.changes_made):
            plugin_with_spam.model.setData(
                plugin_with_spam.model.index(0, 0),
                QtCore.Qt.CheckState.Checked.value,
                QtCore.Qt.ItemDataRole.CheckStateRole,
            )
        assert plugin_with_spam.modified is True

    def test_changes_made_signal_reverting_makes_arg_false(
        self, qtbot, plugin_with_spam
    ):
        with qtbot.wait_signal(plugin_with_spam.changes_made):
            plugin_with_spam.model.setData(
                plugin_with_spam.model.index(0, 0),
                QtCore.Qt.CheckState.Checked.value,
                QtCore.Qt.ItemDataRole.CheckStateRole,
            )
        with qtbot.wait_signal(plugin_with_spam.changes_made):
            plugin_with_spam.model.setData(
                plugin_with_spam.model.index(0, 0),
                QtCore.Qt.CheckState.Unchecked.value,
                QtCore.Qt.ItemDataRole.CheckStateRole,
            )
        assert plugin_with_spam.modified is False

    def test_plugins(self, qtbot, plugin_with_spam):
        plugins = plugin_with_spam.plugins()
        qtbot.addWidget(plugin_with_spam)
        assert "Bacon" in plugins

class TestWorkspace:
    @pytest.fixture()
    def sample_workflow_klass(self, qtbot):
        class Spam(Workflow):
            name = "Spam bacon eggs"
            description = "some description"

            def discover_task_metadata(
                self, initial_results, additional_data, **user_args
            ):
                return []

        return Spam

    @pytest.fixture()
    def workspace(self, monkeypatch):
        monkeypatch.setattr(
            StandardConfigFileLocator, "get_app_data_dir", lambda _: "."
        )
        return speedwagon.frontend.qtwidgets.widgets.Workspace()

    def test_set_workflow_with_missing_configuration(self, qtbot, workspace):
        workspace.session_config = Mock(application_settings=Mock(side_effect=speedwagon.exceptions.MissingConfiguration('nope')))
        qtbot.addWidget(workspace)
        class Spam(speedwagon.Workflow):
            pass
        workspace.set_workflow(Spam)
        assert "Workflow unavailable" in workspace.workflow_description_value.toHtml()

    @pytest.mark.parametrize(
        "workspace_param, expected_value",
        [
            ("description", "some description"),
            ("name", "Spam bacon eggs"),
            ("configuration", {}),
        ]
    )
    def test_qt_properties(self, qtbot, workspace, sample_workflow_klass, workspace_param, expected_value):
        qtbot.addWidget(workspace)
        workspace.session_config = Mock()
        workspace.set_workflow(sample_workflow_klass)
        assert getattr(workspace, workspace_param) == expected_value

    @pytest.mark.parametrize("truthy", [True, False])
    def test_is_valid_matches_setting_form(self, qtbot, workspace, sample_workflow_klass, truthy):
        qtbot.addWidget(workspace)
        workspace.session_config = Mock()
        workspace.settings_form.is_valid = Mock(return_value=truthy)
        assert workspace.is_valid() is truthy

class TestWorkflowSettingsEditor:
    class GenWorkflow(speedwagon.Workflow):
        name = "Generate OCR Files!"

        def discover_task_metadata(
            self, initial_results, additional_data, **user_args
        ):
            return []

        def workflow_options(self):
            return [
                speedwagon.workflow.TextLineEditData(
                    "Dummy config 1", required=True
                ),
                speedwagon.workflow.TextLineEditData(
                    "Other config 2", required=True
                ),
            ]

    #     # def test_s(self, qtbot):
    def test_editor_data_changed(self, qtbot):
        editor = speedwagon.frontend.qtwidgets.widgets.WorkflowSettingsEditor()
        model = models.WorkflowSettingsModel()
        model.add_workflow(self.GenWorkflow())
        model.reset_modified()

        editor.model = model

        qtbot.addWidget(editor)

        with qtbot.wait_signal(editor.workflow_settings_view.expanded):
            editor.workflow_settings_view.expandAll()

        index = model.index(0, 1, parent=model.index(0, 0))
        with qtbot.waitSignal(editor.data_changed):
            # without editor.show() focusWidget doesn't return the delegate
            editor.show()

            qtbot.mouseClick(
                editor.workflow_settings_view.viewport(),
                QtCore.Qt.LeftButton,
                pos=editor.workflow_settings_view.visualRect(index).center(),
            )
            delegate_widget = editor.workflow_settings_view.focusWidget()
            qtbot.keyClicks(delegate_widget, "some data")
            qtbot.keyClick(delegate_widget, QtCore.Qt.Key.Key_Enter)
        assert model.modified() is True


class TestQtWidgetTableEditWidget:
    def test_no_selection_returns_to_existing_value(self, qtbot):
        def update_data(value, existing_row, index):
            existing_row[index.column()].value = value
            return existing_row

        def is_editable_rule(selection, index):
            return selection[index.column()].editable

        def display_role(selection, index):
            return selection[index.column()].value

        def options_role(selection, index):
            return selection[index.column()].possible_values

        def process_data(data: List[Sequence[interaction.DataItem]]):
            results = []
            for row in data:
                results.append({i.name: i.value for i in row})

            return results

        def get_data_callback(
            *args, **kwargs
        ) -> List[Sequence[interaction.DataItem]]:
            second_column = interaction.DataItem(name="two", value="Option 1")
            second_column.editable = True
            second_column.possible_values = ["Option 1", "Option 2"]

            return [
                (interaction.DataItem(name="one", value="1234"), second_column)
            ]

        table_edit_widget = qt_user_interaction.QtWidgetTableEditWidget[
            interaction.DataItem,
            List[TypedDict("Report", {"one": str, "two": str})],
        ](
            enter_data=get_data_callback,
            process_data=process_data,
            model_mapping_roles=qt_user_interaction.QtModelMappingRoles(
                is_editable_rule=is_editable_rule,
                update_data=update_data,
                display_role=display_role,
                options_role=options_role,
            ),
        )
        table_edit_widget.column_names = ["one", "two"]
        old_function = table_edit_widget.get_dialog_box

        def get_dialog_box(selections):
            dialog = old_function(selections)
            editable_index = dialog.view.model().index(0, 1)
            uneditable_index = dialog.view.model().index(0, 0)

            # select the table widget
            qtbot.mouseClick(
                dialog.view.viewport(),
                QtCore.Qt.LeftButton,
            )

            # Select the editable column
            qtbot.mouseClick(
                dialog.view.viewport(),
                QtCore.Qt.LeftButton,
                pos=dialog.view.visualRect(editable_index).center(),
            )

            # Click off of the edit delegate
            qtbot.mouseClick(
                dialog.view.viewport(),
                QtCore.Qt.LeftButton,
                pos=dialog.view.visualRect(uneditable_index).center(),
            )
            dialog.exec = Mock()
            return dialog

        table_edit_widget.get_dialog_box = get_dialog_box

        table_edit_widget.data_gathering_callback = get_data_callback
        results = table_edit_widget.get_user_response({}, [])
        assert (
            results[0]["two"] == "Option 1"
        ), f'expected "Option 1" but got {results}'

        table_edit_widget = cli_user_interaction.CLIEditTable[
            interaction.DataItem,
            List[TypedDict("Report", {"one": str, "two": str})],
        ](
            enter_data=get_data_callback,
            process_data=process_data,
        )
        table_edit_widget.edit_strategy
        table_edit_widget.edit_strategy = lambda data, title: data

        def get_data_callback(
            *args, **kwargs
        ) -> List[Sequence[interaction.DataItem]]:
            second_column = interaction.DataItem(name="two", value="Option 1")
            second_column.editable = True
            second_column.possible_values = ["Option 1", "Option 2"]

            return [
                (interaction.DataItem(name="one", value="1234"), second_column)
            ]

        table_edit_widget.data_gathering_callback = get_data_callback

        results = table_edit_widget.get_user_response({}, [])
        assert (
            results[0]["two"] == "Option 1"
        ), f'expected "Option 1" but got {results}'


class TestLineEditWidget:
    def test_no_layout(self, caplog, qtbot, monkeypatch):
        parent = QtWidgets.QWidget()
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.widgets.LineEditWidget,
            "layout",
            lambda *_: None
        )
        qtbot.addWidget(
            speedwagon.frontend.qtwidgets.widgets.LineEditWidget(
                widget_metadata={},
                parent=parent
            )
        )
        assert "has no layout" in caplog.text

    def test_edit(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.LineEditWidget(
            widget_metadata={}, parent=parent
        )
        qtbot.addWidget(widget)
        with qtbot.wait_signal(widget.dataChanged):
            qtbot.keyClicks(widget.text_box, "hello")
        assert widget.data == "hello"

    def test_data_assignment(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.LineEditWidget(
            widget_metadata={}, parent=parent
        )
        qtbot.addWidget(widget)
        with qtbot.wait_signal(widget.dataChanged):
            widget.data = "hello"
        assert widget.data == "hello"

    def test_editing_finished(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.LineEditWidget(
            widget_metadata={}, parent=parent
        )
        qtbot.addWidget(widget)
        with qtbot.wait_signal(widget.editingFinished):
            qtbot.keyClicks(widget.text_box, "hello")
            qtbot.keyPress(widget.text_box, QtCore.Qt.Key.Key_Enter)

class TestFileSystemItemSelectWidget:
    def test_no_layout(self, caplog, qtbot, monkeypatch):
        parent = QtWidgets.QWidget()
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.widgets.FileSystemItemSelectWidget,
            "layout",
            lambda *_: None
        )
        qtbot.addWidget(
            speedwagon.frontend.qtwidgets.widgets.FileSystemItemSelectWidget(
                widget_metadata={}, parent=parent
            )
        )
        assert "has no layout" in caplog.text

class TestSelectWorkflow:
    @pytest.fixture
    def Spam(self):
        return type("Spam", (Workflow,), {
            "name": "Spam",
            "description": "some description"
        })

    @pytest.fixture
    def Bacon(self):
        return type("Bacon", (Workflow,), {
            "name": "bacon",
            "description": "some other description"
        })

    def test_workflow_selected(self, qtbot, Spam):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.SelectWorkflow(
            parent=parent
        )
        qtbot.add_widget(widget)

        widget.add_workflow(Spam)
        index = widget.model.index(0, 0)
        with qtbot.wait_signal(widget.workflow_selected):
            qtbot.mouseClick(
                widget.workflowSelectionView.viewport(),
                QtCore.Qt.LeftButton,
                pos=widget.workflowSelectionView.visualRect(index).center(),
            )

    @pytest.mark.parametrize("name", ["Spam", "bacon"])
    def test_set_current_by_name_emit_workflow_selected(self, qtbot, name, Spam, Bacon):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.SelectWorkflow(
            parent=parent
        )
        widget.add_workflow(Spam)
        widget.add_workflow(Bacon)
        qtbot.add_widget(widget)
        with qtbot.wait_signal(widget.workflow_selected) as signal:
            widget.set_current_by_name(name)
        assert len(signal.args) == 1
        assert signal.args[0].name == name

    @pytest.mark.parametrize("name", ["Spam", "bacon"])
    def test_set_current_by_name_sets_selected(self, qtbot, name, Spam, Bacon):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.SelectWorkflow(
            parent=parent
        )
        qtbot.add_widget(widget)
        widget.add_workflow(Spam)
        widget.add_workflow(Bacon)
        widget.set_current_by_name(name)
        assert len(widget.workflowSelectionView.selectedIndexes()) == 1
        assert widget.model.data(
            widget.workflowSelectionView.selectedIndexes()[0]
        ) == name

    def test_set_current_by_name_invalid(self, qtbot, Spam, Bacon):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.SelectWorkflow(
            parent=parent
        )
        qtbot.add_widget(widget)
        widget.add_workflow(Spam)
        widget.add_workflow(Bacon)
        with pytest.raises(ValueError) as error:
            widget.set_current_by_name("Invalid Workflow")
        assert "Invalid Workflow" in str(error.value)

    def test_get_current_workflow_type(self, qtbot, Spam):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.SelectWorkflow(
            parent=parent
        )
        qtbot.add_widget(widget)
        widget.add_workflow(Spam)
        widget.set_current_by_name("Spam")
        assert widget.get_current_workflow_type() == Spam

    def test_workflows(self, qtbot, Spam):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.SelectWorkflow(
            parent=parent
        )
        qtbot.add_widget(widget)
        widget.add_workflow(Spam)
        assert "Spam" in widget.workflows

class TestToolConsole:
    def test_starts_with_no_text(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.ToolConsole(
            parent=parent
        )
        qtbot.add_widget(widget)
        assert widget.text == ""

    def test_adding_message(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.ToolConsole(
            parent=parent
        )
        qtbot.add_widget(widget)
        widget.add_message("hello")
        assert widget.text == "hello"

    def test_attach_logger(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.ToolConsole(
            parent=parent
        )
        qtbot.add_widget(widget)
        logger = logging.getLogger("test_attach_logger")
        logger.setLevel(logging.INFO)
        widget.attach_logger(logger)
        try:
            with qtbot.wait_signal(widget.log_handler.signals.messageSent) as signal:
                logger.info("hello")
            assert widget.text.strip() == "hello"
        finally:
            widget.detach_logger()

    def test_close_detaches_logger(self, qtbot):
        parent = QtWidgets.QWidget()
        widget = speedwagon.frontend.qtwidgets.widgets.ToolConsole(
            parent=parent
        )
        qtbot.add_widget(widget)
        logger = logging.getLogger('test_close_detaches_logger')
        logger.setLevel(logging.INFO)
        widget.attach_logger(logger)
        assert len(logger.handlers) == 1
        widget.close()
        assert len(logger.handlers) == 0
