import sys
import typing
from unittest.mock import Mock
import webbrowser

from PyQt5 import QtCore

import speedwagon.startup
import speedwagon.gui
from PyQt5.QtWidgets import QApplication, QAction, QMainWindow, QWidget, QPushButton
from PyQt5.QtCore import Qt

def test_show_help_open_web(qtbot, monkeypatch):
    mock_work_manager = Mock()
    main_window = speedwagon.gui.MainWindow(mock_work_manager)

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
    exit_button = main_window.findChild(QAction, name="exitAction")
    exit_button.trigger()
    assert exit_calls == [1]