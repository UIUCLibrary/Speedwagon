import platform
import logging
from unittest.mock import Mock, patch, mock_open
import pytest
QtCore = pytest.importorskip("PySide6.QtCore")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from speedwagon.frontend.qtwidgets.dialog import settings, dialogs


def test_settings_open_dir_if_location_is_set(qtbot, monkeypatch):
    settings_dialog = settings.SettingsDialog()
    qtbot.addWidget(settings_dialog)
    settings_dialog.settings_location = "some_file_path"

    mock_call = Mock()
    monkeypatch.setattr(settings.OpenSettingsDirectory, "open", mock_call)
    settings_dialog.open_settings_path_button.click()
    assert mock_call.called is True


class TestOpenSettings:
    def test_open_darwin_settings(self, monkeypatch):
        settings_directory = "some/settings/path"
        opening_strategy = settings.DarwinOpenSettings(settings_directory)
        import os
        system = Mock()
        monkeypatch.setattr(os, "system", system)
        opening_strategy.open()
        assert system.called is True and \
               settings_directory in system.call_args_list[0][0][0]

    def test_open_unsupported_settings(self, qtbot, monkeypatch):
        from PySide6 import QtWidgets
        settings_directory = "some/settings/path"
        opening_strategy = settings.UnsupportedOpenSettings(settings_directory)
        show = Mock()
        monkeypatch.setattr(QtWidgets.QMessageBox, "show", show)
        opening_strategy.open()
        assert show.called is True

    def test_open_windows_settings(self, monkeypatch):
        settings_directory = "some\\settings\\path"
        opening_strategy = settings.WindowsOpenSettings(settings_directory)
        import os
        startfile = Mock()
        if platform.system() != "Windows":
            setattr(os, "startfile", startfile)
        else:
            monkeypatch.setattr(os, "startfile", startfile)
        opening_strategy.open()
        assert startfile.called is True


class TestGlobalSettingsTab:
    def test_on_okay_not_modified(self, qtbot, monkeypatch):
        from PySide6 import QtWidgets
        mock_exec = Mock()
        monkeypatch.setattr(QtWidgets.QMessageBox, "exec", mock_exec)
        settings_tab = settings.GlobalSettingsTab()
        qtbot.addWidget(settings_tab)
        settings_tab.on_okay()
        assert mock_exec.called is False

    @pytest.mark.parametrize("config_file, expect_file_written",
                             [
                                 (None, False),
                                 ("dummy.yml", True)
                             ])
    def test_on_okay_modified(self, qtbot, monkeypatch, config_file,
                              expect_file_written):
        from PySide6 import QtWidgets
        from speedwagon.frontend.qtwidgets import models
        mock_exec = Mock()
        monkeypatch.setattr(QtWidgets.QMessageBox, "exec", mock_exec)
        monkeypatch.setattr(models, "serialize_settings_model", Mock())
        settings_tab = settings.GlobalSettingsTab()
        qtbot.addWidget(settings_tab)
        settings_tab.on_modified()
        settings_tab.config_file = config_file
        m = mock_open()
        with patch('builtins.open', m):
            settings_tab.on_okay()
        assert m.called is expect_file_written


class TestTabsConfigurationTab:
    def test_on_ok_not_modified(self, qtbot, monkeypatch):
        config_tab = settings.TabsConfigurationTab()
        from PySide6 import QtWidgets
        mock_exec = Mock()
        monkeypatch.setattr(QtWidgets.QMessageBox, "exec", mock_exec)
        config_tab.on_okay()
        assert mock_exec.called is False

    @pytest.mark.parametrize("settings_location, writes_to_file", [
        ("setting_location", True),
        (None, False)
    ])
    def test_on_okay_modified(self, qtbot, monkeypatch, settings_location,
                              writes_to_file):

        from PySide6 import QtWidgets

        config_tab = settings.TabsConfigurationTab()
        config_tab.settings_location = settings_location
        config_tab.editor.on_modified()
        from speedwagon.frontend.qtwidgets import tabs
        write_tabs_yaml = Mock()
        mock_exec = Mock(name="message box exec")
        with monkeypatch.context() as mp:
            mp.setattr(tabs, "write_tabs_yaml", write_tabs_yaml)
            mp.setattr(QtWidgets.QMessageBox, "exec", mock_exec)
            config_tab.on_okay()

        assert \
            mock_exec.called is True and \
            write_tabs_yaml.called is writes_to_file


class TestTabEditor:
    @pytest.fixture()
    def editor(self):
        return settings.TabEditor()

    def test_set_all_workflows_set_model(self, qtbot, editor):
        qtbot.addWidget(editor)
        mock_workflow = Mock()
        from speedwagon import job
        mock_workflow.__type__ = job.Workflow
        workflows = {
            '': mock_workflow
        }
        editor.all_workflows_list_view.setModel = Mock()
        editor.set_all_workflows(workflows)
        assert editor.all_workflows_list_view.setModel.called is True

    def test_create_new_tab(self, qtbot, monkeypatch, editor):
        qtbot.addWidget(editor)
        assert editor.selected_tab_combo_box.model().rowCount() == 0
        with monkeypatch.context() as mp:
            mp.setattr(
                settings.QtWidgets.QInputDialog,
                "getText",
                lambda *args, **kwargs: ("new tab", True)
            )
            qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)
        assert editor.selected_tab_combo_box.model().rowCount() == 1

    def test_create_new_tab_can_cancel(self, qtbot, monkeypatch, editor):
        qtbot.addWidget(editor)
        assert editor.selected_tab_combo_box.model().rowCount() == 0
        with monkeypatch.context() as mp:
            mp.setattr(
                settings.QtWidgets.QInputDialog,
                "getText",
                lambda *args, **kwargs: ("new tab", False)
            )
            qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)
        assert editor.selected_tab_combo_box.model().rowCount() == 0

    def test_create_new_tab_cannot_create_same_name_tabs(
            self,
            qtbot,
            monkeypatch,
            editor
    ):
        qtbot.addWidget(editor)
        from speedwagon.frontend.qtwidgets import tabs
        from speedwagon.frontend.qtwidgets import models
        with monkeypatch.context() as mp:
            def read_tabs_yaml(*args, **kwargs):
                return [
                    tabs.TabData("existing tab", models.WorkflowListModel2())
                ]

            mp.setattr(tabs, "read_tabs_yaml", read_tabs_yaml)
            editor.tabs_file = "dummy.yml"

        with monkeypatch.context() as mp:

            mp.setattr(
                settings.QtWidgets.QInputDialog,
                "getText",
                lambda *args, **kwargs: ("existing tab", True)
            )

            # Make sure that this can exit
            QMessageBox = Mock()
            QMessageBox.exec = \
                Mock(side_effect=lambda context=mp: context.setattr(
                         settings.QtWidgets.QInputDialog,
                         "getText",
                         lambda *args, **kwargs: ("new tab", False)
                     ))

            QMessageBox.name = 'QMessageBox'

            mp.setattr(
                settings.QtWidgets,
                "QMessageBox",
                Mock(return_value=QMessageBox)
            )
            qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)
            assert QMessageBox.setWindowTitle.called is True

    def test_delete_tab(self, qtbot, monkeypatch, editor):
        qtbot.addWidget(editor)
        with monkeypatch.context() as mp:
            mp.setattr(
                settings.QtWidgets.QInputDialog,
                "getText",
                lambda *args, **kwargs: ("new tab", True)
            )
            qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)
        assert editor.selected_tab_combo_box.model().rowCount() == 1

        qtbot.mouseClick(
            editor.delete_current_tab_button,
            QtCore.Qt.LeftButton
        )

        assert editor.selected_tab_combo_box.model().rowCount() == 0


class TestSettingsBuilder:
    @pytest.fixture()
    def nothing_set_settings(self, qtbot):
        builder = settings.SettingsBuilder()
        return builder.build()

    def test_nothing_has_no_tabs(self, nothing_set_settings):
        assert nothing_set_settings.tabs_widget.count() == 0

    def test_nothing_no_settings_directory_button(self, nothing_set_settings):
        assert \
            nothing_set_settings.open_settings_path_button.isHidden() is True

    def test_add_global_settings(self, qtbot, monkeypatch):
        builder = settings.SettingsBuilder()
        builder.add_global_settings("something.ini")
        read_config_data = Mock()

        monkeypatch.setattr(
            settings.GlobalSettingsTab,
            "read_config_data",
            read_config_data
        )

        dialog = builder.build()
        assert dialog.tabs_widget.count() == 1

    def test_add_editor_tab(self, qtbot, monkeypatch):
        builder = settings.SettingsBuilder()
        builder.add_tabs_setting("something")
        dialog = builder.build()
        assert dialog.tabs_widget.count() == 1

    def test_settings_path(self, qtbot):
        builder = settings.SettingsBuilder()
        builder.add_open_settings("some_directory")
        dialog = builder.build()
        assert dialog.open_settings_path_button.isHidden() is False


class TestWorkflowProgress:
    @pytest.mark.parametrize(
        "button_type, expected_active",
        [
            (QtWidgets.QDialogButtonBox.Cancel, False),
            (QtWidgets.QDialogButtonBox.Close, True)
        ]
    )
    def test_default_buttons(self, qtbot, button_type, expected_active):
        progress_dialog = dialogs.WorkflowProgress()
        qtbot.addWidget(progress_dialog)
        assert progress_dialog.button_box.button(button_type).isEnabled() is \
               expected_active

    def test_get_console(self, qtbot):
        progress_dialog = dialogs.WorkflowProgress()
        progress_dialog.write_to_console("spam")
        assert "spam" in progress_dialog.get_console_content()

    def test_start_changes_state_to_working(self, qtbot):
        progress_dialog = dialogs.WorkflowProgress()
        assert progress_dialog.current_state == "idle"
        progress_dialog.start()
        assert progress_dialog.current_state == "working"

    def test_stop_changes_working_state_to_stopping(self, qtbot):
        progress_dialog = dialogs.WorkflowProgress()
        progress_dialog.start()
        assert progress_dialog.current_state == "working"
        progress_dialog.stop()
        assert progress_dialog.current_state == "stopping"

    def test_failed_changes_working_state_to_failed(self, qtbot):
        progress_dialog = dialogs.WorkflowProgress()
        progress_dialog.start()
        assert progress_dialog.current_state == "working"
        progress_dialog.failed()
        assert progress_dialog.current_state == "failed"

    def test_cancel_completed_changes_stopping_state_to_aborted(self, qtbot):
        progress_dialog = dialogs.WorkflowProgress()
        progress_dialog.start()
        assert progress_dialog.current_state == "working"
        progress_dialog.stop()
        progress_dialog.cancel_completed()
        assert progress_dialog.current_state == "aborted"

    def test_success_completed_chances_status_to_done(self, qtbot):
        progress_dialog = dialogs.WorkflowProgress()
        progress_dialog.start()
        progress_dialog.success_completed()
        assert progress_dialog.current_state == "done"


class TestWorkflowProgressGui:
    def test_remove_log_handles(self, qtbot):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        progress_dialog = dialogs.WorkflowProgressGui()
        qtbot.add_widget(progress_dialog)
        progress_dialog.attach_logger(logger)
        progress_dialog.remove_log_handles()
        logger.info("Some message")
        progress_dialog.flush()
        assert "Some message" not in progress_dialog.get_console_content()

    def test_attach_logger(self, qtbot):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        progress_dialog = dialogs.WorkflowProgressGui()
        qtbot.add_widget(progress_dialog)
        progress_dialog.attach_logger(logger)
        try:
            logger.info("Some message")
            progress_dialog.flush()
            assert "Some message" in progress_dialog.get_console_content()
        finally:
            progress_dialog.remove_log_handles()

    def test_write_html_block_to_console(self, qtbot):
        progress_dialog = dialogs.WorkflowProgressGui()
        qtbot.add_widget(progress_dialog)
        progress_dialog.write_html_block_to_console("<h1>hello</h1>")
        assert "hello" in progress_dialog.get_console_content()


class TestWorkflowProgressState:
    @pytest.mark.parametrize(
        "button_clicked, event_called",
        [
            (dialogs.QtWidgets.QMessageBox.Yes, "accept"),
            (dialogs.QtWidgets.QMessageBox.No, "ignore"),
        ]
    )
    def test_event_called_based_on_button_press(
            self,
            qtbot,
            monkeypatch,
            button_clicked,
            event_called
    ):
        context = Mock()
        state = dialogs.WorkflowProgressStateWorking(context)
        event = Mock()
        exec_ = Mock(return_value=button_clicked)
        monkeypatch.setattr(dialogs.QtWidgets.QMessageBox, "exec", exec_)
        state.close_dialog(event)
        assert getattr(event, event_called).called is True

    @pytest.mark.parametrize(
        "state_class,command",
        [
            (dialogs.WorkflowProgressStateWorking, "start"),
            (dialogs.WorkflowProgressStateStopping, "start"),
            (dialogs.WorkflowProgressStateAborted, "stop"),
            (dialogs.WorkflowProgressStateFailed, "stop"),
            (dialogs.WorkflowProgressStateDone, "stop"),
        ]
    )
    def test_warnings(self, state_class, command):
        with pytest.warns(Warning) as record:
            state = state_class(context=Mock())
            getattr(state, command)()
        assert len(record) > 0