import argparse
import os.path
from unittest.mock import Mock, MagicMock, mock_open, patch

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


def test_get_custom_tabs_missing_file(capsys, monkeypatch):
    from speedwagon import startup
    all_workflows = {
        "my workflow": Mock()
    }
    import os
    monkeypatch.setattr(os.path, "exists", lambda x: False)
    list(startup.get_custom_tabs(all_workflows, "not_a_real_file"))
    captured = capsys.readouterr()
    assert "file not found" in captured.err


def test_get_custom_tabs_bad_data_raises_exception(monkeypatch):
    from speedwagon import startup
    from speedwagon.startup import FileFormatError
    import os
    test_file = "test.yml"
    monkeypatch.setattr(os.path, "exists", lambda x: x == test_file)
    with pytest.raises(FileFormatError):
        with patch('speedwagon.startup.open', mock_open(
                read_data='not valid yml data')) as m:
            list(startup.get_custom_tabs({"my workflow": Mock()}, test_file))


def test_missing_workflow(monkeypatch, capsys):
    from speedwagon import startup
    import os
    test_file = "test.yml"
    monkeypatch.setattr(os.path, "exists", lambda x: x == test_file)
    import yaml

    # These workflow are not valid
    tabs_config_data = {
        "my workflow": [
            "spam",
            "bacon",
            "eggs"
        ]
    }
    load = Mock(name="load", return_value=tabs_config_data)
    load.__class__ = dict
    monkeypatch.setattr(yaml, "load", load)
    with patch('speedwagon.startup.open', mock_open()) as m:
        list(startup.get_custom_tabs({"my workflow": Mock()}, test_file))
    captured = capsys.readouterr()
    assert "Unable to load" in captured.err


def test_get_custom_tabs_loads_workflows_from_file(monkeypatch):
    from speedwagon import startup
    import os
    test_file = "test.yml"
    monkeypatch.setattr(os.path, "exists", lambda x: x == test_file)
    import yaml
    all_workflows = {
        "spam": Mock(active=True)
    }
    tabs_config_data = {
        "my workflow": [
            "spam",
        ]
    }
    load = Mock(name="load", return_value=tabs_config_data)
    load.__class__ = dict
    monkeypatch.setattr(yaml, "load", load)
    with patch('speedwagon.startup.open', mock_open()) as m:
        tab_name, workflows = next(
            startup.get_custom_tabs(all_workflows, test_file)
        )
    assert "my workflow" == tab_name and "spam" in workflows


def test_standalone_tab_editor_loads(qtbot, monkeypatch):
    from speedwagon import startup, config
    TabsEditorApp = MagicMock()
    monkeypatch.setattr(startup, "TabsEditorApp", TabsEditorApp)
    app = Mock()
    settings = Mock()
    get_platform_settings = Mock(return_value=settings)
    settings.get_app_data_directory = Mock(return_value=".")
    monkeypatch.setattr(config, "get_platform_settings", get_platform_settings)
    startup.standalone_tab_editor(app)
    assert app.exec.called is True


class TestCustomTabsFileReader:
    def test_load_custom_tabs_file_not_found(self, capsys):
        from speedwagon import startup
        all_workflows = Mock()
        reader = startup.CustomTabsFileReader(all_workflows)
        reader.read_yml_file = Mock()
        reader.read_yml_file.side_effect = FileNotFoundError()

        fake_file = Mock()
        all(reader.load_custom_tabs(fake_file))
        captured = capsys.readouterr()
        assert "Custom tabs file not found" in captured.err

    def test_load_custom_tabs_file_attribute_error(self, capsys):
        from speedwagon import startup
        all_workflows = Mock()
        reader = startup.CustomTabsFileReader(all_workflows)
        reader.read_yml_file = Mock()
        reader.read_yml_file.side_effect = AttributeError()

        fake_file = Mock()
        all(reader.load_custom_tabs(fake_file))
        captured = capsys.readouterr()
        assert "Custom tabs file failed to load" in captured.err

    def test_load_custom_tabs_file_yaml_error(self, capsys):
        from speedwagon import startup
        import yaml

        all_workflows = Mock()
        reader = startup.CustomTabsFileReader(all_workflows)
        reader.read_yml_file = Mock()
        reader.read_yml_file.side_effect = yaml.YAMLError()

        fake_file = Mock()
        all(reader.load_custom_tabs(fake_file))
        captured = capsys.readouterr()
        assert "file failed to load" in captured.err

    def test_load_custom_tabs_file_error_loading_tab(self, capsys):
        from speedwagon import startup

        all_workflows = Mock()
        reader = startup.CustomTabsFileReader(all_workflows)
        reader.read_yml_file = Mock(return_value={"my tab": []})
        reader._get_tab_items = Mock()
        reader._get_tab_items.side_effect = TypeError()

        fake_file = Mock()
        all(reader.load_custom_tabs(fake_file))
        captured = capsys.readouterr()
        assert "Error loading tab" in captured.err


class TestStartupDefault:
    def test_invalid_setting_logs_warning(self, caplog):
        import speedwagon.startup

        def update(*_, **__):
            raise ValueError("oops")
        startup_worker = speedwagon.startup.StartupDefault(app=Mock())
        resolution = Mock(FRIENDLY_NAME="dummy")
        resolution.update = lambda _: update()
        startup_worker.resolve_settings(resolution_strategy_order=[resolution])
        assert any("oops is an invalid setting" in m for m in caplog.messages)

    def test_invalid_setting_logs_warning_for_ConfigFileSetter(self, caplog):
        import speedwagon.startup

        def update(*_, **__):
            raise ValueError("oops")
        startup_worker = speedwagon.startup.StartupDefault(app=Mock())
        resolution = Mock(FRIENDLY_NAME="dummy")
        resolution.__class__ = speedwagon.startup.ConfigFileSetter
        resolution.update = lambda _: update()
        startup_worker.resolve_settings(resolution_strategy_order=[resolution])
        assert any("contains an invalid setting" in m for m in caplog.messages)

    def test_missing_debug_setting(self, caplog):
        import speedwagon.startup
        startup_worker = speedwagon.startup.StartupDefault(app=Mock())
        startup_worker.startup_settings = MagicMock()

        startup_worker.startup_settings.__getitem__ = Mock(
            side_effect=KeyError
        )

        startup_worker.resolve_settings([])
        assert any(
            "Unable to find a key for debug mode" in m for m in caplog.messages
        )

    def test_invalid_debug_setting(self, caplog):
        import speedwagon.startup
        startup_worker = speedwagon.startup.StartupDefault(app=Mock())
        startup_worker.startup_settings = MagicMock()

        startup_worker.startup_settings.__getitem__ = Mock(
            side_effect=ValueError
        )

        startup_worker.resolve_settings([])
        assert any(
            "invalid setting for debug mode" in m for m in caplog.messages
        )

    def test_default_resolve_settings_calls_default_setter(self, monkeypatch):
        import speedwagon.startup

        def update(*_, **__):
            raise ValueError("oops")

        default_setter = Mock()
        monkeypatch.setattr(
            speedwagon.startup, "DefaultsSetter", default_setter
        )

        monkeypatch.setattr(
            speedwagon.startup.CliArgsSetter, "update", MagicMock()
        )

        startup_worker = speedwagon.startup.StartupDefault(app=Mock())
        resolution = Mock(FRIENDLY_NAME="dummy")
        resolution.update = lambda _: update()
        startup_worker.resolve_settings()
        assert default_setter.called is True

    def test_ensure_settings_files_called_generate_default(
            self,
            monkeypatch,
            first_time_startup_worker
    ):
        import speedwagon.startup
        generate_default = Mock()

        monkeypatch.setattr(
            speedwagon.startup.speedwagon.config,
            "generate_default",
            generate_default
        )

        first_time_startup_worker.ensure_settings_files()
        assert generate_default.called is True

    @pytest.fixture()
    def first_time_startup_worker(self, monkeypatch):
        import speedwagon.startup
        startup_worker = speedwagon.startup.StartupDefault(app=Mock())
        startup_worker.config_file = "dummy.yml"
        startup_worker.tabs_file = "tabs.yml"
        startup_worker.app_data_dir = \
            os.path.join("invalid", "app_data", "path")

        startup_worker.user_data_dir = os.path.join("invalid", "path")

        def exists(path):
            config_files = [
                startup_worker.config_file,
                startup_worker.tabs_file,
                startup_worker.app_data_dir,
                startup_worker.user_data_dir
            ]
            if path in config_files:
                return False

            return False

        monkeypatch.setattr(
            speedwagon.startup.os.path, "exists", exists
        )

        makedirs = Mock()
        monkeypatch.setattr(speedwagon.startup.os, "makedirs", makedirs)

        touch = Mock()
        monkeypatch.setattr(speedwagon.startup.pathlib.Path, "touch", touch)

        return startup_worker

    @pytest.fixture()
    def returning_startup_worker(self, monkeypatch):
        import speedwagon.startup
        startup_worker = speedwagon.startup.StartupDefault(app=Mock())
        startup_worker.config_file = "dummy.yml"
        startup_worker.tabs_file = "tabs.yml"
        startup_worker.app_data_dir = os.path.join("some", "path")
        startup_worker.user_data_dir = os.path.join("some", "user", "path")

        def exists(path):
            config_files = [
                startup_worker.config_file,
                startup_worker.tabs_file,
                startup_worker.app_data_dir,
                startup_worker.user_data_dir
            ]
            if path in config_files:
                return True
            return False

        monkeypatch.setattr(
            speedwagon.startup.os.path, "exists", exists
        )
        makedirs = Mock()
        monkeypatch.setattr(speedwagon.startup.os, "makedirs", makedirs)

        touch = Mock()
        monkeypatch.setattr(speedwagon.startup.pathlib.Path, "touch", touch)

        return startup_worker

    @pytest.mark.parametrize(
        "expected_message",
        [
            'No config file found',
            "No tabs.yml file found",
            "Created",
            "Created directory "
        ]
    )
    def test_ensure_settings_files_called_messages(
            self,
            monkeypatch,
            caplog,
            expected_message,
            first_time_startup_worker
    ):
        import speedwagon.startup
        generate_default = Mock()

        monkeypatch.setattr(
            speedwagon.startup.speedwagon.config,
            "generate_default",
            generate_default
        )

        first_time_startup_worker.ensure_settings_files()

        assert any(
            expected_message in m for m in caplog.messages
        )

    @pytest.mark.parametrize(
        "expected_message",
        [
            'Found existing config file',
            "Found existing tabs file",
            "Found existing app data",
            "Found existing user data directory"
        ]
    )
    def test_ensure_settings_files_called_messages_on_success(
            self,
            monkeypatch,
            caplog,
            expected_message,
            returning_startup_worker
    ):
        import speedwagon.startup
        generate_default = Mock()

        monkeypatch.setattr(
            speedwagon.startup.speedwagon.config,
            "generate_default",
            generate_default
        )

        returning_startup_worker.ensure_settings_files()
        assert any(
            expected_message in m for m in caplog.messages
        )
