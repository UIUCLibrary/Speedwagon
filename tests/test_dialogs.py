import platform
from unittest.mock import Mock

from speedwagon.dialog import settings


def test_settings_open_dir_if_location_is_set(qtbot, monkeypatch):
    settings_dialog = settings.SettingsDialog()
    qtbot.addWidget(settings_dialog)
    settings_dialog.settings_location = "some_file_path"

    import os
    mock_call = Mock()
    if platform.system() == "Windows":
        monkeypatch.setattr(os, "startfile", mock_call)
    elif platform.system() == "Darwin":
        monkeypatch.setattr(os, "system", mock_call)
    settings_dialog.open_settings_path_button.click()
    assert mock_call.called is True and \
           "some_file_path" in mock_call.call_args_list[0][0][0]


