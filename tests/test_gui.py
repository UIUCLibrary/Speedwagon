from unittest.mock import Mock, MagicMock, patch, mock_open
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


def test_window_save_log(qtbot, monkeypatch):
    mock_work_manager = MagicMock(settings_path="some-path")
    main_window = speedwagon.gui.MainWindow(mock_work_manager)

    qtbot.addWidget(main_window)
    monkeypatch.setattr(
        speedwagon.gui.QtWidgets.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: ("spam.log", None)
    )

    m = mock_open()
    with patch('builtins.open', m):
        main_window.save_log()

    m.assert_called_once_with('spam.log', 'w')


def test_set_current_tab(qtbot):
    mock_work_manager = MagicMock(settings_path="some-path")
    main_window = speedwagon.gui.MainWindow(mock_work_manager)

    qtbot.addWidget(main_window)
    main_window.tab_widget.tabs.count = Mock(return_value=1)
    main_window.tab_widget.tabs.tabText = Mock(return_value='spam')
    main_window.tab_widget.tabs.setCurrentIndex = Mock()

    main_window.set_current_tab("spam")
    assert main_window.tab_widget.tabs.setCurrentIndex.called
