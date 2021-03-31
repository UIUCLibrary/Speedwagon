from unittest.mock import Mock, MagicMock
import webbrowser

import speedwagon.startup
import speedwagon.gui
from PyQt5.QtWidgets import QApplication, QAction


def test_show_help_open_web(qtbot, monkeypatch):
    mock_work_manager = Mock()
    main_window = speedwagon.gui.MainWindow(mock_work_manager)
    qtbot.addWidget(main_window)

    def mock_open_new(url, *args, **kwargs):
        assert "http" in url

    with monkeypatch.context() as e:
        e.setattr(webbrowser, "open_new", mock_open_new)
        main_window.show_help()


def test_exit_button(qtbot, monkeypatch):
    exit_calls = []
    monkeypatch.setattr(QApplication, "exit", lambda: exit_calls.append(1))
    mock_work_manager = Mock()
    main_window = speedwagon.gui.MainWindow(mock_work_manager)
    qtbot.addWidget(main_window)
    exit_button = main_window.findChild(QAction, name="exitAction")
    exit_button.trigger()
    assert exit_calls == [1]


def test_system_info_menu(qtbot, monkeypatch):
    from speedwagon.dialog import dialogs
    mock_work_manager = Mock()
    main_window = speedwagon.gui.MainWindow(mock_work_manager)
    qtbot.addWidget(main_window)
    from PyQt5 import QtWidgets
    system_menu = main_window.menuBar().findChild(QtWidgets.QMenu,
                                                  name="systemMenu")

    for action in system_menu.actions():
        if action.objectName() == "systemInfoAction":
            system_info_action = action
            break
    else:
        assert False, "systemInfoAction not found"
    mock_exec = Mock()
    monkeypatch.setattr(dialogs.SystemInfoDialog, "exec", mock_exec)
    system_info_action.trigger()
    assert mock_exec.called is True


def test_show_configuration_menu(qtbot, monkeypatch):
    mock_work_manager = MagicMock(settings_path="some-path")
    main_window = speedwagon.gui.MainWindow(mock_work_manager)
    qtbot.addWidget(main_window)
    from PyQt5 import QtWidgets
    system_menu = main_window.menuBar().findChild(QtWidgets.QMenu,
                                                  name="systemMenu")

    for action in system_menu.actions():
        if action.objectName() == "settingsAction":
            settings_action = action
            break
    else:
        assert False, "settingsAction not found"

    import os
    from speedwagon.dialog import settings
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    read_config_data = Mock()
    monkeypatch.setattr(
        settings.GlobalSettingsTab, "read_config_data", read_config_data
    )
    configure_tab_load = Mock()
    monkeypatch.setattr(settings.TabsConfigurationTab, "load",
                        configure_tab_load)

    mock_exec = Mock()
    monkeypatch.setattr(settings.SettingsDialog, "exec", mock_exec)

    settings_action.trigger()
    assert mock_exec.called is True
