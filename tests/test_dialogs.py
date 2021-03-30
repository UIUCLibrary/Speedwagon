import platform
from unittest.mock import Mock

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

