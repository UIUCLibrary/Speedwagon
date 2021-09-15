import argparse
import os.path
from unittest.mock import Mock, MagicMock, mock_open, patch

import json
import logging
import os
import importlib
import yaml
import pytest
from PyQt5 import QtWidgets

import speedwagon.startup
import speedwagon.config
import speedwagon.job
import speedwagon.runner_strategies


def test_version_exits_after_being_called(monkeypatch):

    parser = speedwagon.startup.CliArgsSetter.get_arg_parser()
    version_exit_mock = Mock()

    with monkeypatch.context() as m:
        m.setattr(argparse.ArgumentParser, "exit", version_exit_mock)
        parser.parse_args(["--version"])

    version_exit_mock.assert_called()


def test_run_loads_window(qtbot, monkeypatch, tmpdir):
    app = Mock()
    app.exec_ = MagicMock()

    def dummy_app_data_dir(*args, **kwargs):
        app_data_dir = tmpdir / "app_data_dir"
        app_data_dir.ensure_dir()
        return app_data_dir.strpath

    monkeypatch.setattr(
        speedwagon.config.get_platform_settings().__class__,
        "get_app_data_directory",
        dummy_app_data_dir
    )
    standard_startup = speedwagon.startup.StartupDefault(app=app)

    standard_startup.startup_settings['debug'] = True
    tabs_file = tmpdir / "tabs.yaml"
    tabs_file.ensure()

    # get_app_data_directory

    standard_startup.tabs_file = tabs_file

    monkeypatch.setattr(QtWidgets, "QSplashScreen", MagicMock())
    monkeypatch.setattr(
        speedwagon.startup.speedwagon.gui,
        "MainWindow",
        MagicMock()
    )
    standard_startup._logger = Mock()
    standard_startup.run()
    assert app.exec_.called is True


class TestTabsEditorApp:
    def test_on_okay_closes(self, qtbot):
        editor = speedwagon.startup.TabsEditorApp()
        qtbot.addWidget(editor)
        editor.close = Mock()
        editor.on_okay()
        assert editor.close.called is True


def test_start_up_calls_default(monkeypatch):
    StartupDefault_ = MagicMock()
    monkeypatch.setattr(speedwagon.startup, "StartupDefault", StartupDefault_)
    with pytest.raises(SystemExit):
        speedwagon.startup.main()
        StartupDefault_.assert_called()


def test_start_up_tab_editor(monkeypatch):
    standalone_tab_editor = Mock()

    with monkeypatch.context() as mp:
        mp.setattr(speedwagon.startup,
                   "standalone_tab_editor",
                   standalone_tab_editor)

        speedwagon.startup.main(argv=["tab-editor"])
        assert standalone_tab_editor.called is True


def test_load_as_module(monkeypatch):

    monkeypatch.setattr(logging, "getLogger", Mock())
    import speedwagon.__main__
    main_mock = Mock()
    monkeypatch.setattr(speedwagon.startup, "main", main_mock)
    speedwagon.__main__.main()
    assert main_mock.called is True


def test_load_module_self_test(monkeypatch):
    monkeypatch.setattr(logging, "getLogger", Mock())

    pytest_mock = MagicMock()
    monkeypatch.setattr(importlib, "import_module", lambda x: pytest_mock)
    import speedwagon.__main__

    with pytest.raises(SystemExit):
        speedwagon.__main__.main(["_", "--pytest"])
    assert pytest_mock.main.called is True


def test_get_custom_tabs_missing_file(capsys, monkeypatch):
    all_workflows = {
        "my workflow": Mock()
    }
    monkeypatch.setattr(os.path, "exists", lambda x: False)
    list(speedwagon.startup.get_custom_tabs(all_workflows, "not_a_real_file"))
    captured = capsys.readouterr()
    assert "file not found" in captured.err


def test_get_custom_tabs_bad_data_raises_exception(monkeypatch):
    test_file = "test.yml"
    monkeypatch.setattr(os.path, "exists", lambda x: x == test_file)
    with pytest.raises(speedwagon.startup.FileFormatError):
        with patch('speedwagon.startup.open', mock_open(
                read_data='not valid yml data')):
            list(
                speedwagon.startup.get_custom_tabs(
                    {
                        "my workflow": Mock()
                    },
                    test_file
                )
            )


def test_missing_workflow(monkeypatch, capsys):
    test_file = "test.yml"
    monkeypatch.setattr(os.path, "exists", lambda x: x == test_file)

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
    with patch('speedwagon.startup.open', mock_open()):
        list(
            speedwagon.startup.get_custom_tabs(
                {
                    "my workflow": Mock()
                },
                test_file
            )
        )
    captured = capsys.readouterr()
    assert "Unable to load" in captured.err


def test_get_custom_tabs_loads_workflows_from_file(monkeypatch):
    test_file = "test.yml"
    monkeypatch.setattr(os.path, "exists", lambda x: x == test_file)
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
    with patch('speedwagon.startup.open', mock_open()):
        tab_name, workflows = next(
            speedwagon.startup.get_custom_tabs(all_workflows, test_file)
        )
    assert tab_name == "my workflow" and "spam" in workflows


def test_standalone_tab_editor_loads(qtbot, monkeypatch):
    TabsEditorApp = MagicMock()
    monkeypatch.setattr(speedwagon.startup, "TabsEditorApp", TabsEditorApp)
    app = Mock()
    settings = Mock()
    get_platform_settings = Mock(return_value=settings)
    settings.get_app_data_directory = Mock(return_value=".")

    monkeypatch.setattr(
        speedwagon.config,
        "get_platform_settings",
        get_platform_settings
    )

    speedwagon.startup.standalone_tab_editor(app)
    assert app.exec.called is True


class TestCustomTabsFileReader:
    def test_load_custom_tabs_file_not_found(self, capsys):
        all_workflows = Mock()
        reader = speedwagon.startup.CustomTabsFileReader(all_workflows)
        reader.read_yml_file = Mock()
        reader.read_yml_file.side_effect = FileNotFoundError()

        fake_file = Mock()
        all(reader.load_custom_tabs(fake_file))
        captured = capsys.readouterr()
        assert "Custom tabs file not found" in captured.err

    def test_load_custom_tabs_file_attribute_error(self, capsys):
        all_workflows = Mock()
        reader = speedwagon.startup.CustomTabsFileReader(all_workflows)
        reader.read_yml_file = Mock()
        reader.read_yml_file.side_effect = AttributeError()

        fake_file = Mock()
        all(reader.load_custom_tabs(fake_file))
        captured = capsys.readouterr()
        assert "Custom tabs file failed to load" in captured.err

    def test_load_custom_tabs_file_yaml_error(self, capsys):

        all_workflows = Mock()
        reader = speedwagon.startup.CustomTabsFileReader(all_workflows)
        reader.read_yml_file = Mock()
        reader.read_yml_file.side_effect = yaml.YAMLError()

        fake_file = Mock()
        all(reader.load_custom_tabs(fake_file))
        captured = capsys.readouterr()
        assert "file failed to load" in captured.err

    def test_load_custom_tabs_file_error_loading_tab(self, capsys):
        all_workflows = Mock()
        reader = speedwagon.startup.CustomTabsFileReader(all_workflows)
        reader.read_yml_file = Mock(return_value={"my tab": []})
        reader._get_tab_items = Mock()
        reader._get_tab_items.side_effect = TypeError()

        fake_file = Mock()
        all(reader.load_custom_tabs(fake_file))
        captured = capsys.readouterr()
        assert "Error loading tab" in captured.err


class TestStartupDefault:
    def test_invalid_setting_logs_warning(self, caplog, monkeypatch):

        def update(*_, **__):
            raise ValueError("oops")
        # Monkey patch Path.home() because this will fail on linux systems if
        # uid not found. For example: in some docker containers
        monkeypatch.setattr(
            speedwagon.config.Path, "home", lambda: "my_home"
        )

        monkeypatch.setattr(
            speedwagon.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )
        startup_worker = speedwagon.startup.StartupDefault(app=Mock())
        resolution = Mock(FRIENDLY_NAME="dummy")
        resolution.update = lambda _: update()
        startup_worker.resolve_settings(resolution_strategy_order=[resolution])
        assert any("oops is an invalid setting" in m for m in caplog.messages)

    def test_invalid_setting_logs_warning_for_ConfigFileSetter(
            self, caplog, monkeypatch):

        def update(*_, **__):
            raise ValueError("oops")

        # Monkey patch Path.home() because this will fail on linux systems if
        # uid not found. For example: in some docker containers
        monkeypatch.setattr(
            speedwagon.config.Path, "home", lambda: "my_home"
        )
        monkeypatch.setattr(
            speedwagon.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )
        startup_worker = speedwagon.startup.StartupDefault(app=Mock())
        resolution = Mock(FRIENDLY_NAME="dummy")
        resolution.__class__ = speedwagon.startup.ConfigFileSetter
        resolution.update = lambda _: update()
        startup_worker.resolve_settings(resolution_strategy_order=[resolution])
        assert any("contains an invalid setting" in m for m in caplog.messages)

    def test_missing_debug_setting(self, caplog, monkeypatch):
        # Monkey patch Path.home() because this will fail on linux systems if
        # uid not found. For example: in some docker containers
        monkeypatch.setattr(
            speedwagon.config.Path, "home", lambda: "my_home"
        )
        monkeypatch.setattr(
            speedwagon.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )
        startup_worker = speedwagon.startup.StartupDefault(app=Mock())
        startup_worker.startup_settings = MagicMock()

        startup_worker.startup_settings.__getitem__ = Mock(
            side_effect=KeyError
        )

        startup_worker.resolve_settings([])
        assert any(
            "Unable to find a key for debug mode" in m for m in caplog.messages
        )

    def test_invalid_debug_setting(self, caplog, monkeypatch):
        # Monkey patch Path.home() because this will fail on linux systems if
        # uid not found. For example: in some docker containers
        monkeypatch.setattr(
            speedwagon.config.Path, "home", lambda: "my_home"
        )
        monkeypatch.setattr(
            speedwagon.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )
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

        def update(*_, **__):
            raise ValueError("oops")

        default_setter = Mock()
        monkeypatch.setattr(
            speedwagon.startup, "DefaultsSetter", default_setter
        )

        # Monkey patch Path.home() because this will fail on linux systems if
        # uid not found. For example: in some docker containers
        monkeypatch.setattr(
            speedwagon.config.Path, "home", lambda: "my_home"
        )

        monkeypatch.setattr(
            speedwagon.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )

        monkeypatch.setattr(
            speedwagon.startup.CliArgsSetter, "update", MagicMock()
        )

        startup_worker = speedwagon.startup.StartupDefault(app=Mock())
        resolution = Mock(friendly_name="dummy")
        resolution.update = lambda _: update()
        startup_worker.resolve_settings()
        assert default_setter.called is True

    def test_ensure_settings_files_called_generate_default(
            self,
            monkeypatch,
            first_time_startup_worker
    ):
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
        # Monkey patch Path.home() because this will fail on linux systems if
        # uid not found. For example: in some docker containers
        monkeypatch.setattr(
            speedwagon.config.Path, "home", lambda: "my_home"
        )
        monkeypatch.setattr(
            speedwagon.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )
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
        # Monkey patch Path.home() because this will fail on linux systems if
        # uid not found. For example: in some docker containers
        monkeypatch.setattr(
            speedwagon.config.Path, "home", lambda: "my_home"
        )
        monkeypatch.setattr(
            speedwagon.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )
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


class TestSingleWorkflowJSON:
    def test_run_without_json_raises_exception(self):
        with pytest.raises(ValueError) as error:
            startup = speedwagon.startup.SingleWorkflowJSON()
            startup.options = Mock()
            startup.workflow = None
            startup.run()
        assert "workflow" in str(error.value).lower()

    def test_run_without_options_raises_exception(self):
        with pytest.raises(ValueError) as error:
            startup = speedwagon.startup.SingleWorkflowJSON()
            startup.options = None
            startup.workflow = Mock()
            startup.run()
        assert "no data" in str(error.value).lower()

    def test_initialize_without_workflow_raises_exception(self):
        with pytest.raises(ValueError) as error:
            startup = speedwagon.startup.SingleWorkflowJSON()
            startup.options = Mock()
            startup.workflow = None
            startup.initialize()
        assert "workflow" in str(error.value).lower()

    def test_initialize_without_options_raises_exception(self):
        with pytest.raises(ValueError) as error:
            startup = speedwagon.startup.SingleWorkflowJSON()
            startup.options = None
            startup.workflow = Mock()
            startup.initialize()
        assert "no data" in str(error.value).lower()

    def test_initialize_success(self):
        startup = speedwagon.startup.SingleWorkflowJSON()
        startup.options = Mock()
        startup.workflow = Mock()
        startup.initialize()

    def test_load_json(self):
        startup = speedwagon.startup.SingleWorkflowJSON()

        startup.load_json_string(
            json.dumps(
                {
                    "workflow": "Zip Packages",
                    "options": {
                        "Source": "dummy_source",
                        "Output": "dummy_out"
                    }
                }
            )
        )

        assert startup.options["Source"] == "dummy_source" and \
               startup.options["Output"] == "dummy_out" and \
               startup.workflow.name == 'Zip Packages'

    def test_runner_strategies_called(self, monkeypatch):
        startup = speedwagon.startup.SingleWorkflowJSON()

        startup.load_json_string(
            json.dumps(
                {
                    "workflow": "Zip Packages",
                    "options": {
                        "Source": "dummy_source",
                        "Output": "dummy_out"
                    }
                }
            )
        )

        monkeypatch.setattr(
            speedwagon.startup.speedwagon.gui,
            "MainWindow",
            MagicMock()
        )

        run = MagicMock()

        monkeypatch.setattr(
            speedwagon.startup.runner_strategies.QtRunner,
            "run",
            run
        )

        startup.workflow.validate_user_options = MagicMock()
        startup.run()
        assert run.called is True


class TestMultiWorkflowLauncher:
    def test_all_workflows_validate_user_options(self, qtbot):
        startup_launcher = speedwagon.startup.MultiWorkflowLauncher()
        workflow_tasks = [

            (
                'Verify Checksum Batch [Single]',
                {
                    "Input": os.path.join("somepath", "checksum.md5")
                }

            ),
            (
                "Convert CaptureOne TIFF to Hathi TIFF package",
                {
                    "Input": os.path.join("some", "valid", "input", "path"),
                    "Output": os.path.join("some", "valid", "output", "path")
                }
            ),
        ]

        jobs = []
        for workflow_name, workflow_args in workflow_tasks:
            mock_workflow = MagicMock()
            mock_workflow.name = workflow_name
            mock_workflow.__class__ = speedwagon.job.Workflow
            jobs.append(mock_workflow)
            startup_launcher.add_job(mock_workflow, workflow_args)
        startup_launcher.run()
        assert all(job.validate_user_options.called is True for job in jobs)

    def test_task_failing(self, qtbot):
        startup_launcher = speedwagon.startup.MultiWorkflowLauncher()
        mock_workflow = MagicMock()
        mock_workflow.name = 'Verify Checksum Batch [Single]'
        mock_workflow.__class__ = speedwagon.job.Workflow
        mock_workflow.initial_task = \
            Mock(side_effect=speedwagon.runner_strategies.TaskFailed())

        startup_launcher.add_job(
            mock_workflow,
            {
                    "Input": os.path.join("somepath", "checksum.md5")
                }
         )
        with pytest.raises(speedwagon.job.JobCancelled):
            startup_launcher.run()
