import argparse
from unittest.mock import Mock, MagicMock

import pytest


def test_version_exits_after_being_called(monkeypatch):
    from speedwagon import startup
    parser = startup.CliArgsSetter.get_arg_parser()
    version_exit_mock = Mock()

    with monkeypatch.context() as m:
        m.setattr(argparse.ArgumentParser, "exit", version_exit_mock)
        parser.parse_args(["--version"])

    version_exit_mock.assert_called()


def test_run_loads_window(qtbot, monkeypatch, tmpdir):
    from speedwagon import startup, config
    app = Mock()
    app.exec_ = MagicMock()

    def dummy_app_data_dir(*args, **kwargs):
        app_data_dir = tmpdir / "app_data_dir"
        app_data_dir.ensure_dir()
        return app_data_dir.strpath

    monkeypatch.setattr(config.get_platform_settings().__class__, "get_app_data_directory", dummy_app_data_dir)
    standard_startup = startup.StartupDefault(app=app)

    standard_startup.startup_settings['debug'] = True
    tabs_file = tmpdir / "tabs.yaml"
    tabs_file.ensure()

    # get_app_data_directory

    standard_startup.tabs_file = tabs_file
    from PyQt5 import QtWidgets
    monkeypatch.setattr(QtWidgets, "QSplashScreen", MagicMock())
    monkeypatch.setattr(startup, "MainWindow", MagicMock())
    standard_startup._logger = Mock()
    standard_startup.run()
    assert app.exec_.called is True


class TestTabsEditorApp:
    def test_on_okay_closes(self, qtbot):
        from speedwagon import startup
        editor = startup.TabsEditorApp()
        qtbot.addWidget(editor)
        editor.close = Mock()
        editor.on_okay()
        assert editor.close.called is True


def test_start_up_calls_default(monkeypatch):
    import speedwagon.startup
    StartupDefault_ = MagicMock()
    monkeypatch.setattr(speedwagon.startup, "StartupDefault", StartupDefault_)
    with pytest.raises(SystemExit):
        speedwagon.startup.main()
        StartupDefault_.assert_called()


def test_start_up_tab_editor(monkeypatch):
    import speedwagon.startup
    standalone_tab_editor = Mock()

    with monkeypatch.context() as mp:
        mp.setattr(speedwagon.startup,
                   "standalone_tab_editor",
                   standalone_tab_editor)

        speedwagon.startup.main(argv=["tab-editor"])
        assert standalone_tab_editor.called is True


def test_load_as_module(monkeypatch):
    import logging
    monkeypatch.setattr(logging, "getLogger", Mock())
    import speedwagon.__main__
    import speedwagon.startup
    main_mock = Mock()
    monkeypatch.setattr(speedwagon.startup, "main", main_mock)
    speedwagon.__main__.main()
    assert main_mock.called is True


def test_load_module_self_test(monkeypatch):
    import logging
    monkeypatch.setattr(logging, "getLogger", Mock())
    import importlib
    pytest_mock = MagicMock()
    monkeypatch.setattr(importlib, "import_module", lambda x: pytest_mock)
    import speedwagon.__main__

    with pytest.raises(SystemExit):
        speedwagon.__main__.main(["_", "--pytest"])
    assert pytest_mock.main.called is True
