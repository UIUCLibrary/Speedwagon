import platform
from unittest.mock import Mock, patch, mock_open
import pytest
from speedwagon.dialog import settings


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

    def test_open_unsupported_settings(self, monkeypatch):
        from PyQt5 import QtWidgets
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
        from PyQt5 import QtWidgets
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
        from PyQt5 import QtWidgets
        from speedwagon import config
        mock_exec = Mock()
        monkeypatch.setattr(QtWidgets.QMessageBox, "exec", mock_exec)
        monkeypatch.setattr(config, "serialize_settings_model", Mock())
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
        from PyQt5 import QtWidgets
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

        from PyQt5 import QtWidgets

        config_tab = settings.TabsConfigurationTab()
        config_tab.settings_location = settings_location
        config_tab.editor.on_modified()
        from speedwagon import tabs
        write_tabs_yaml = Mock()
        mock_exec = Mock(name="message box exec")
        with monkeypatch.context() as mp:
            mp.setattr(tabs, "write_tabs_yaml", write_tabs_yaml)
            mp.setattr(QtWidgets.QMessageBox, "exec", mock_exec)
            config_tab.on_okay()

        assert \
            mock_exec.called is True and \
            write_tabs_yaml.called is writes_to_file
