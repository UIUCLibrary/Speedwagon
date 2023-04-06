import platform
import logging
from unittest.mock import Mock, patch, mock_open, MagicMock
import pytest

import speedwagon
import sys
import typing
QtCore = pytest.importorskip("PySide6.QtCore")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from speedwagon.frontend.qtwidgets.dialog import settings, dialogs
from speedwagon.frontend.qtwidgets import models, tabs
if sys.version_info < (3, 10):
    import importlib_metadata as metadata
else:
    from importlib import metadata

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
        import subprocess
        call = Mock()
        monkeypatch.setattr(subprocess, "call", call)
        opening_strategy.open()
        assert call.called is True and \
               settings_directory in call.call_args_list[0][0][0]

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
        assert mock_exec.called is False

    def test_not_modified_from_init(self, qtbot):
        tab = settings.GlobalSettingsTab()
        assert tab.data_is_modified() is False

    def test_read_config_data_raises_if_no_config_file(self, qtbot):
        tab = settings.GlobalSettingsTab()
        tab.config_file = None
        with pytest.raises(FileNotFoundError):
            tab.read_config_data()

    def test_read_config_data_raises_if_config_file_is_invalid(self, monkeypatch, qtbot):
        tab = settings.GlobalSettingsTab()
        tab.config_file = "some invalid file"
        monkeypatch.setattr(settings.os.path, "exists", lambda path: False)
        with pytest.raises(FileNotFoundError):
            tab.read_config_data()


    def test_read_config_data(self, monkeypatch, mocker, qtbot):
        tab = settings.GlobalSettingsTab()
        tab.config_file = "some valid file"
        monkeypatch.setattr(
            settings.os.path,
            "exists",
            lambda path: path == "some valid file"
        )
        settings_model = models.SettingsModel()
        monkeypatch.setattr(
            settings.models,
            "build_setting_qt_model",
            lambda config_file: settings_model
        )
        table_set_model = mocker.spy(tab.settings_table, "setModel")
        tab.read_config_data()
        table_set_model.assert_called_once_with(settings_model)


    # @pytest.mark.parametrize("config_file, expect_file_written",
    #                          [
    #                              (None, False),
    #                              ("dummy.yml", True)
    #                          ])
    # def test_on_okay_modified(self, qtbot, monkeypatch, config_file,
    #                           expect_file_written):
    #     from PySide6 import QtWidgets
    #     from speedwagon.frontend.qtwidgets import models
    #     mock_exec = Mock()
    #     monkeypatch.setattr(QtWidgets.QMessageBox, "exec", mock_exec)
    #     monkeypatch.setattr(models, "serialize_settings_model", Mock())
    #     settings_tab = settings.GlobalSettingsTab()
    #     qtbot.addWidget(settings_tab)
    #     settings_tab.on_modified()
    #     settings_tab.config_file = config_file
    #     m = mock_open()
    #     with patch('builtins.open', m):
    #         settings_tab.on_okay()
    #     assert m.called is expect_file_written


class TestTabsConfigurationTab:
    @pytest.mark.parametrize("settings_location, writes_to_file", [
        ("setting_location", True),
        (None, False)
    ])
    def test_on_okay_modified(self, qtbot, monkeypatch, settings_location,
                              writes_to_file):

        from PySide6 import QtWidgets

        config_tab = settings.TabsConfigurationTab()
        config_tab.settings_location = settings_location
        from speedwagon.frontend.qtwidgets import tabs
        write_tabs_yaml = Mock()
        mock_exec = Mock(name="message box exec")
        with monkeypatch.context() as mp:
            mp.setattr(tabs, "write_tabs_yaml", write_tabs_yaml)
            mp.setattr(QtWidgets.QMessageBox, "exec", mock_exec)
            config_tab.on_okay()

        assert \
            mock_exec.called is True and \
            write_tabs_yaml.called is writes_to_file, \
            f"mock_exec.called is {mock_exec.called}"

    def test_create_new_tab_set_modified_true(self, qtbot, monkeypatch):
        config_tab = settings.TabsConfigurationTab()
        with qtbot.wait_signal(config_tab.changes_made):
            with monkeypatch.context() as mp:
                mp.setattr(
                    settings.QtWidgets.QInputDialog,
                    "getText",
                    lambda *args, **kwargs: ("new tab", True)
                )
                qtbot.mouseClick(
                    config_tab.editor.new_tab_button,
                    QtCore.Qt.LeftButton
                )
        assert config_tab.data_is_modified() is True
    def test_revert_changes(self, qtbot, monkeypatch):
        # Test if the changes made reverted to original start shows data not
        # modified
        config_tab = settings.TabsConfigurationTab()
        with qtbot.wait_signal(config_tab.changes_made):
            with monkeypatch.context() as mp:
                mp.setattr(
                    settings.QtWidgets.QInputDialog,
                    "getText",
                    lambda *args, **kwargs: ("new tab", True)
                )
                qtbot.mouseClick(
                    config_tab.editor.new_tab_button,
                    QtCore.Qt.LeftButton
                )
        assert config_tab.data_is_modified() is True
        config_tab.editor.set_current_tab("new tab")
        with qtbot.wait_signal(config_tab.changes_made):
            qtbot.mouseClick(
                config_tab.editor.delete_current_tab_button,
                QtCore.Qt.LeftButton
            )
        assert config_tab.data_is_modified() is False

    def test_load_calls_set_workflows(self, qtbot, monkeypatch):
        all_workflows = {
            "myworkflow": Mock('Workflow')
        }

        monkeypatch.setattr(
            settings.job,
            "available_workflows",
            lambda : all_workflows
        )
        set_all_workflows = Mock()
        monkeypatch.setattr(settings.TabEditor, 'tabs_file', Mock())
        monkeypatch.setattr(
            settings.TabEditor,
            'set_all_workflows',
            set_all_workflows
        )
        config_tab = settings.TabsConfigurationTab()
        config_tab.load("file.yml")
        assert set_all_workflows.called is True
        set_all_workflows.assert_called_once_with(all_workflows)



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

    def test_modified_by_add(self, qtbot, monkeypatch):
        editor = settings.TabEditor()

        qtbot.addWidget(editor)
        def getText(*args, **kwargs):
            return "new name", True
        with qtbot.wait_signal(editor.changed_made):
            with monkeypatch.context() as ctx:
                ctx.setattr(settings.QtWidgets.QInputDialog, "getText", getText)
                qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)
        assert editor.modified is True
    def test_not_modified_if_deleted_newly_added_tab(
            self,
            qtbot,
            monkeypatch
    ):
        editor = settings.TabEditor()

        qtbot.addWidget(editor)
        def getText(*args, **kwargs):
            return "new name", True

        with qtbot.wait_signal(editor.changed_made):
            with monkeypatch.context() as ctx:
                ctx.setattr(settings.QtWidgets.QInputDialog, "getText", getText)
                qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)
        editor.set_current_tab("new name")
        with qtbot.wait_signal(editor.changed_made):
            assert editor.modified is True
            qtbot.mouseClick(editor.delete_current_tab_button, QtCore.Qt.LeftButton)
        assert editor.modified is False
class TestSettingsBuilder2:
    def test_accepted(self, qtbot):
        builder = settings.SettingsBuilder2()
        dialog = builder.build()
        ok = dialog.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        ok.setEnabled(True)
        qtbot.add_widget(dialog)
        with qtbot.wait_signal(dialog.accepted):
            qtbot.mouseClick(ok, QtCore.Qt.LeftButton)

    def test_rejected(self, qtbot):
        builder = settings.SettingsBuilder2()
        dialog = builder.build()
        cancel_button = dialog.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        qtbot.add_widget(dialog)
        with qtbot.wait_signal(dialog.rejected):
            qtbot.mouseClick(cancel_button, QtCore.Qt.LeftButton)

    def test_add_tab_increases_tabs(self, qtbot):
        builder = settings.SettingsBuilder2()
        item = settings.TabsConfigurationTab()
        builder.add_tab("spam", item)
        dialog = builder.build()
        assert dialog.tabs_widget.count() == 1

    def test_save_callback_called(self, qtbot):
        builder = settings.SettingsBuilder2()
        on_save_callback = Mock()
        builder.add_on_save_callback(on_save_callback)
        item = settings.TabsConfigurationTab()
        builder.add_tab("spam", item)
        dialog = builder.build()
        ok = dialog.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        ok.setEnabled(True)
        qtbot.add_widget(dialog)
        with qtbot.wait_signal(dialog.accepted):
            qtbot.mouseClick(ok, QtCore.Qt.LeftButton)
        assert on_save_callback.called is True

    def test_add_on_save_callback_returns_same_widgets(self, qtbot):

        builder = settings.SettingsBuilder2()
        item = settings.TabsConfigurationTab()
        builder.add_tab("spam", item)

        def my_callback(parent, tab_widgets: typing.Dict[str, settings.SettingsTab]):
            assert tab_widgets['spam'] == item

        builder.add_on_save_callback(my_callback)
        dialog = builder.build()
        ok = dialog.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        ok.setEnabled(True)
        qtbot.add_widget(dialog)
        with qtbot.wait_signal(dialog.accepted):
            qtbot.mouseClick(ok, QtCore.Qt.LeftButton)

    @pytest.mark.parametrize(
        "settings_widget",
        [
            settings.TabsConfigurationTab,
            settings.GlobalSettingsTab,
            settings.PluginsTab
        ]
    )
    def test_get_data(self, qtbot, settings_widget):

        builder = settings.SettingsBuilder2()
        item = settings_widget()
        builder.add_tab("spam", item)

        def my_callback(parent, tab_widgets: typing.Dict[str, settings.SettingsTab]):
            assert isinstance(tab_widgets['spam'].get_data(), dict)

        builder.add_on_save_callback(my_callback)
        dialog = builder.build()
        ok = dialog.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        ok.setEnabled(True)
        qtbot.add_widget(dialog)
        with qtbot.wait_signal(dialog.accepted):
            qtbot.mouseClick(ok, QtCore.Qt.LeftButton)


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

class TestConfigSaver:

    @pytest.fixture()
    def sample_settings(self):
        return {
            "spam": "bacon",
            "eggs": "lovely spam"
        }

    @pytest.fixture()
    def settings_model(self, sample_settings):
        new_model = models.SettingsModel()
        for key, value in sample_settings.items():
            new_model.add_setting(key, value)
        return new_model
    def test_write_config_file_called(self, qtbot, monkeypatch, settings_model, sample_settings):

        global_settings = settings.GlobalSettingsTab()
        global_settings.model = settings_model

        saver = settings.ConfigSaver(QtWidgets.QWidget())
        write_config_file = Mock()
        monkeypatch.setattr(saver, "write_config_file", write_config_file)
        saver.save({
            "Global Settings": global_settings,
            "Tabs": settings.TabsConfigurationTab(),
            "Plugins": settings.PluginsTab()
        })

        assert write_config_file.called is True

    def test_writes_config_file_keys(
        self,
        qtbot,
        monkeypatch,
        settings_model,
        sample_settings
    ):
        global_settings = settings.GlobalSettingsTab()
        global_settings.model = settings_model

        saver = settings.ConfigSaver(QtWidgets.QWidget())

        def write_config_file(data):
            assert all(k in data for k in sample_settings)

        monkeypatch.setattr(saver, "write_config_file", write_config_file)

        saver.save({
            "Global Settings": global_settings,
            "Tabs": settings.TabsConfigurationTab(),
            "Plugins": settings.PluginsTab()
        })

    def test_writes_config_file_plugins(
        self,
        qtbot,
        monkeypatch,
        sample_settings
    ):
        plugins_tab = settings.PluginsTab()
        entry_point = Mock(module="bar")
        entry_point.name = "foo"
        plugins_tab.plugins_activation.model.add_entry_point(
            entry_point,
            enabled=True
        )
        saver = settings.ConfigSaver(QtWidgets.QWidget())

        def write_config_file(data):
            assert "foo" in data
            # assert all(k in data for k in sample_settings)

        monkeypatch.setattr(saver, "write_config_file", write_config_file)

        saver.save({
            "Global Settings": settings.GlobalSettingsTab(),
            "Tabs": settings.TabsConfigurationTab(),
            "Plugins": plugins_tab
        })

    def test_set_config_path(
            self,
            qtbot,
            monkeypatch,
            sample_settings,
            settings_model
    ):
        plugins_tab = settings.PluginsTab()
        entry_point = Mock(module="bar")
        entry_point.name = "foo"
        plugins_tab.plugins_activation.model.add_entry_point(
            entry_point,
            enabled=True
        )
        saver = settings.ConfigSaver(QtWidgets.QWidget())
        saver.config_file_path = "some/file/path.ini"
        global_settings = settings.GlobalSettingsTab()
        global_settings.model = settings_model
        with patch('builtins.open', mock_open()) as mocked_file:
            saver.save({
                "Global Settings": global_settings,
                "Tabs": settings.TabsConfigurationTab(),
                "Plugins": settings.PluginsTab()
            })
            mocked_file.assert_called_once()

    def test_write_yaml(self, qtbot, monkeypatch):
        saver = settings.ConfigSaver(QtWidgets.QWidget())
        tab_config = settings.TabsConfigurationTab()
        tabs_model = models.TabsModel()
        workflows_list = models.WorkflowListModel2()

        class FakeWorkflow(speedwagon.Workflow):
            pass

        workflows_list.add_workflow(FakeWorkflow)
        tabs_model.add_tab(tabs.TabData("My Workflow", workflows_model=workflows_list))
        tab_config.editor.model = tabs_model

        def write_tabs_yml(data):
            assert "My Workflow" in data
        monkeypatch.setattr(saver, "write_tabs_yml", write_tabs_yml)

        saver.save({
            "Global Settings": settings.GlobalSettingsTab(),
            "Tabs": tab_config,
            "Plugins": settings.PluginsTab()
        })


class TestSettingsTab:
    def test_data_is_modified_raises_not_implemented(self, qtbot):
        new_tab = settings.SettingsTab()
        with pytest.raises(NotImplementedError):
            new_tab.data_is_modified()

    def test_get_data_defaults_to_none(self, qtbot):
        new_tab = settings.SettingsTab()
        assert new_tab.get_data() is None
class TestPluginsTab:
    def test_not_modified_from_init(self, qtbot):
        tab = settings.PluginsTab()
        assert tab.data_is_modified() is False

    def test_load(self, qtbot, mocker, monkeypatch):
        data = """
[PLUGINS.mysampleplugin]
myworkflow = True
"""
        with patch(
                'configparser.open',
                mock_open(read_data=data)
        ):
            config_file = "config.ini"
            tab = settings.PluginsTab()
            entry_point = Mock(
                metadata.EntryPoint,
                name="EntryPoint",
                module="mysampleplugin"
            )
            entry_point.name = "myworkflow"
            add_entry_point = mocker.spy(
                tab.plugins_activation.model,
                "add_entry_point"
            )
            with monkeypatch.context() as mp:
                mp.setattr(
                    settings.metadata,
                    "entry_points",
                    lambda *_, **__: [entry_point]
                )
                tab.load(config_file)
            add_entry_point.assert_called_once_with(entry_point, True)


class TestEntrypointsPluginModelLoader:
    def test_load_plugins_into_model(self, monkeypatch):
        sample_ini_file = "config.ini"
        model = models.PluginActivationModel()
        assert model.rowCount() == 0
        loader_strategy = \
            settings.EntrypointsPluginModelLoader(sample_ini_file)

        monkeypatch.setattr(
            loader_strategy,
            "plugin_entry_points",
            Mock(return_value=[
                Mock()
            ])
        )
        read_settings_file_plugins = MagicMock()
        monkeypatch.setattr(
            settings.ConfigLoader,
            "read_settings_file_plugins",
            read_settings_file_plugins
        )
        loader_strategy.load_plugins_into_model(model)
        assert model.rowCount() > 0


class TestSettingsDialog:
    def test_okay_button_active_only_when_modified(self, qtbot):
        dialog_box = settings.SettingsDialog()

        dialog_tab = settings.GlobalSettingsTab()
        dialog_tab.model.add_setting("spam", "yes")

        dialog_box.add_tab(dialog_tab, "dummy")

        ok_enabled_before_modified = dialog_box.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).isEnabled()

        with qtbot.wait_signal(dialog_tab.changes_made):
            dialog_tab.model.setData(dialog_tab.model.index(0, 1), "no")

        ok_enabled_after_modified = dialog_box.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).isEnabled()

        assert all(
            (
                ok_enabled_before_modified is False,
                ok_enabled_after_modified is True,
            )
        )

    def test_revert__new_tab_plugins_state_buttons(self, qtbot, monkeypatch):
        dialog_box = settings.SettingsDialog()

        plugin_tab = settings.TabsConfigurationTab()
        dialog_box.add_tab(plugin_tab, "Plugins")
        ok_enabled_before_modified = dialog_box.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).isEnabled()
        with qtbot.wait_signal(dialog_box.changes_made):
            with monkeypatch.context() as mp:
                mp.setattr(
                    settings.QtWidgets.QInputDialog,
                    "getText",
                    lambda *args, **kwargs: ("new tab", True)
                )
                qtbot.mouseClick(
                    plugin_tab.editor.new_tab_button,
                    QtCore.Qt.LeftButton
                )
        ok_enabled_after_modified = dialog_box.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).isEnabled()
        with qtbot.wait_signal(dialog_box.changes_made):
            qtbot.mouseClick(
                plugin_tab.editor.delete_current_tab_button,
                QtCore.Qt.LeftButton
            )
        ok_enabled_after_reverted = dialog_box.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).isEnabled()

        assert all(
            (
                ok_enabled_before_modified is False,
                ok_enabled_after_modified is True,
                ok_enabled_after_reverted is False,
            )
        )
    def test_revert_add_workflwos_plugins_state_buttons(self, qtbot, monkeypatch):
        dialog_box = settings.SettingsDialog()

        plugin_tab = settings.TabsConfigurationTab()
        dialog_box.add_tab(plugin_tab, "Plugins")
        with qtbot.wait_signal(dialog_box.changes_made):
            with monkeypatch.context() as mp:
                mp.setattr(
                    settings.QtWidgets.QInputDialog,
                    "getText",
                    lambda *args, **kwargs: ("new tab", True)
                )
                qtbot.mouseClick(
                    plugin_tab.editor.new_tab_button,
                    QtCore.Qt.LeftButton
                )
        plugin_tab.editor.model.reset_modified()
        ok_enabled_before_modified = dialog_box.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).isEnabled()
        # ok_enabled_after_modified = dialog_box.button_box.button(
        #     QtWidgets.QDialogButtonBox.StandardButton.Ok
        # ).isEnabled()
        # with qtbot.wait_signal(dialog_box.changes_made):
        #     qtbot.mouseClick(
        #         plugin_tab.editor.delete_current_tab_button,
        #         QtCore.Qt.LeftButton
        #     )
        # ok_enabled_after_reverted = dialog_box.button_box.button(
        #     QtWidgets.QDialogButtonBox.StandardButton.Ok
        # ).isEnabled()

        assert all(
            (
                ok_enabled_before_modified is False,
                # ok_enabled_after_modified is True,
                # ok_enabled_after_reverted is False,
            )
        )
    # dialog_box.exec()
