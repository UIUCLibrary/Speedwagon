import typing
from typing import Any, List, Dict
from unittest.mock import Mock, MagicMock, patch, mock_open
import webbrowser

import pytest

import speedwagon.startup


import speedwagon.workflow
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QtGui = pytest.importorskip("PySide6.QtGui")
from speedwagon.frontend.qtwidgets import shared_custom_widgets




def test_show_help_open_web(qtbot, monkeypatch):
    mock_work_manager = Mock()
    main_window = \
        speedwagon.frontend.qtwidgets.gui.MainWindow1(mock_work_manager)

    qtbot.addWidget(main_window)

    def mock_open_new(url, *args, **kwargs):
        assert "http" in url

    with monkeypatch.context() as e:
        e.setattr(webbrowser, "open_new", mock_open_new)
        main_window.show_help()


def test_exit_button(qtbot, monkeypatch):
    exit_calls = []
    monkeypatch.setattr(
        QtWidgets.QApplication,
        "exit",
        lambda: exit_calls.append(1)
    )

    mock_work_manager = Mock()
    main_window = \
        speedwagon.frontend.qtwidgets.gui.MainWindow1(mock_work_manager)

    qtbot.addWidget(main_window)
    exit_button = main_window.findChild(QtGui.QAction, name="exitAction")
    exit_button.trigger()
    assert exit_calls == [1]


def test_system_info_menu(qtbot, monkeypatch):
    from speedwagon.frontend.qtwidgets.dialog import dialogs
    mock_work_manager = Mock()
    main_window = \
        speedwagon.frontend.qtwidgets.gui.MainWindow1(mock_work_manager)

    qtbot.addWidget(main_window)
    from PySide6 import QtWidgets
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
    main_window = \
        speedwagon.frontend.qtwidgets.gui.MainWindow1(mock_work_manager)

    qtbot.addWidget(main_window)
    from PySide6 import QtWidgets
    system_menu = main_window.menuBar().findChild(QtWidgets.QMenu,
                                                  name="systemMenu")

    for action in system_menu.actions():
        if action.objectName() == "settingsAction":
            settings_action = action
            break
    else:
        assert False, "settingsAction not found"

    import os
    from speedwagon.frontend.qtwidgets.dialog import settings
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


class TestToolConsole:
    def test_add_message(self, qtbot):
        console = speedwagon.frontend.qtwidgets.gui.ToolConsole(None)
        qtbot.addWidget(console)
        console.add_message("I'm a message")
        assert "I'm a message" in console.text


def test_window_save_log(qtbot, monkeypatch):
    mock_work_manager = MagicMock(settings_path="some-path")
    main_window = \
        speedwagon.frontend.qtwidgets.gui.MainWindow1(mock_work_manager)

    qtbot.addWidget(main_window)
    monkeypatch.setattr(
        speedwagon.frontend.qtwidgets.gui.QtWidgets.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: ("spam.log", None)
    )

    m = mock_open()
    with patch('builtins.open', m):
        main_window.save_log()

    m.assert_called_once_with('spam.log', 'w', encoding='utf-8')


def test_set_current_tab(qtbot):
    mock_work_manager = MagicMock(settings_path="some-path")
    main_window = \
        speedwagon.frontend.qtwidgets.gui.MainWindow1(mock_work_manager)

    qtbot.addWidget(main_window)
    main_window.tab_widget.tabs.count = Mock(return_value=1)
    main_window.tab_widget.tabs.tabText = Mock(return_value='spam')
    main_window.tab_widget.tabs.setCurrentIndex = Mock()

    main_window.set_current_tab("spam")
    assert main_window.tab_widget.tabs.setCurrentIndex.called


class TestMainWindow:
    def test_about_dialog_box(self, qtbot, monkeypatch):
        work_manager = Mock()
        work_manager.settings_path = None
        window = speedwagon.frontend.qtwidgets.gui.MainWindow1(work_manager)
        qtbot.add_widget(window)
        about_dialog_box = Mock()
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.dialog,
            "about_dialog_box",
            about_dialog_box
        )
        window.show_about_window()
        assert about_dialog_box.called is True

    def test_show_system_info(self, qtbot, monkeypatch):
        work_manager = Mock()
        work_manager.settings_path = None
        window = speedwagon.frontend.qtwidgets.gui.MainWindow1(work_manager)
        qtbot.add_widget(window)
        exec_ = Mock()
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.dialog.dialogs.SystemInfoDialog,
            "exec",
            exec_
        )
        window.show_system_info()
        assert exec_.called is True

    def test_show_configuration_opens_settings_dialog(
            self,
            qtbot,
            monkeypatch
    ):
        work_manager = Mock()
        work_manager.settings_path = None
        window = speedwagon.frontend.qtwidgets.gui.MainWindow1(work_manager)
        qtbot.add_widget(window)
        exec_ = Mock()
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.dialog.settings.SettingsDialog,
            "exec",
            exec_
        )
        window.show_configuration()
        assert exec_.called is True


class TestMainWindow2:
    def test_exit(self, qtbot, monkeypatch):
        exit_called = Mock()
        manager = Mock()

        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.gui.QtWidgets.QWidget,
            "close",
            exit_called
        )

        main_window = speedwagon.frontend.qtwidgets.gui.MainWindow2(manager)
        qtbot.addWidget(main_window)
        main_window.findChild(QtGui.QAction, name="exitAction").trigger()
        assert exit_called.called is True

    @pytest.mark.parametrize("tab_name", ["Spam", "Dummy"])
    def test_set_current_tab(self, qtbot, tab_name):
        manager = Mock()
        main_window = speedwagon.frontend.qtwidgets.gui.MainWindow2(manager)
        workflows_tab1 = speedwagon.frontend.qtwidgets.tabs.WorkflowsTab2(
            parent=main_window.tab_widget,
            workflows=MagicMock(),
        )
        main_window.tab_widget.add_tab(workflows_tab1.tab_widget, "Dummy")
        workflows_tab2 = speedwagon.frontend.qtwidgets.tabs.WorkflowsTab2(
            parent=main_window.tab_widget,
            workflows=MagicMock(),
        )
        main_window.tab_widget.add_tab(workflows_tab2.tab_widget, "Spam")

        main_window.set_current_tab(tab_name)
        current_tab_name = \
            main_window.tab_widget.tabs.tabText(
                main_window.tab_widget.tabs.currentIndex()
            )
        assert current_tab_name == tab_name

    def test_set_current_tab_invalid_throws(self, qtbot):
        main_window = speedwagon.frontend.qtwidgets.gui.MainWindow2(Mock())
        main_window.tab_widget.add_tab(
            speedwagon.frontend.qtwidgets.tabs.WorkflowsTab2(
                parent=main_window.tab_widget,
                workflows=MagicMock(),
            ).tab_widget,
            "Spam"
        )

        # eggs is NOT a valid tab
        with pytest.raises(IndexError):
            main_window.set_current_tab("eggs")

    def test_set_active_workflow(self, qtbot):
        main_window = speedwagon.frontend.qtwidgets.gui.MainWindow2(Mock())

        bacon = MagicMock()
        bacon.name = "Bacon"

        eggs = MagicMock()
        eggs.name = "Eggs"

        main_window.add_tab(
            "All", {
                "Bacon": bacon,
                "Eggs": eggs,
            }
        )
        main_window.tab_widget.add_tab(
            speedwagon.frontend.qtwidgets.tabs.WorkflowsTab2(
                parent=main_window.tab_widget,
                workflows=MagicMock(),
            ).tab_widget,
            "Spam"
        )
        main_window.set_active_workflow("Eggs")
        assert main_window.get_current_workflow_name() == "Eggs"

    def test_set_current_workflow_settings(self, qtbot):
        main_window = speedwagon.frontend.qtwidgets.gui.MainWindow2(Mock())

        class Eggs(speedwagon.Workflow):
            def discover_task_metadata(self, initial_results: List[Any],
                                       additional_data: Dict[str, Any],
                                       **user_args) -> List[dict]:
                return []

            def get_user_options(self) -> List[
                speedwagon.workflow.AbsOutputOptionDataType
            ]:
                return [
                    speedwagon.workflow.TextLineEditData("Dummy")
                ]

            def user_options(self) -> typing.List[Any]:
                return [
                    shared_custom_widgets.UserOptionPythonDataType2(
                        label_text="Dummy"
                    )
                ]

        main_window.add_tab("All", {"Eggs": Eggs})

        main_window.set_active_workflow("Eggs")

        main_window.set_current_workflow_settings({"Dummy": "Yes"})
        assert main_window.get_current_job_settings()["Dummy"] == "Yes"


def test_load_job_settings_model(qtbot):
    data = {
        'Source': '/Volumes/G-RAID with Thunderbolt/hathi_test/access/',
        'Check for page_data in meta.yml': True,
        'Check ALTO OCR xml files': True,
        'Check OCR xml files are utf-8': False
    }
    source = speedwagon.workflow.DirectorySelect("Source")

    check_page_data_option = \
        speedwagon.workflow.BooleanSelect("Check for page_data in meta.yml")
    check_page_data_option.value = False

    check_ocr_option = speedwagon.workflow.BooleanSelect("Check ALTO OCR xml files")
    check_ocr_option.value = True

    check_ocr_utf8_option = \
        speedwagon.workflow.BooleanSelect('Check OCR xml files are utf-8')
    check_ocr_utf8_option.value = False

    workflow_options = [
        source,
        check_page_data_option,
        check_ocr_option,
        check_ocr_utf8_option

    ]
    form = speedwagon.frontend.qtwidgets.widgets.DynamicForm()
    speedwagon.frontend.qtwidgets.gui.load_job_settings_model(data, form, workflow_options)
    assert form._background.widgets['Source'].data == '/Volumes/G-RAID with Thunderbolt/hathi_test/access/'
