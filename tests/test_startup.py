import argparse
import os.path
from unittest.mock import Mock, MagicMock, mock_open, patch, ANY

import json
import logging
import os
import importlib
import yaml
import pytest
from PyQt5 import QtWidgets, QtCore

import speedwagon.startup
import speedwagon.config
import speedwagon.job
import speedwagon.runner_strategies
from speedwagon.dialog.settings import SettingsDialog


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
        "MainWindow1",
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

@pytest.mark.skip("This might be changing")
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
            "MainWindow1",
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


class TestSignalLogger:
    def test_signal_is_sent(self, qtbot):
        class Dummy(QtCore.QObject):
            dummy_signal = QtCore.pyqtSignal(str, int)

            def __init__(self):
                super().__init__()
                self.dummy_signal.connect(self.d)

            def d(self, message, level):
                print("hhh")

        dummy = Dummy()

        signal_log_handler = \
            speedwagon.startup.SignalLogHandler(dummy.dummy_signal)

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logger.addHandler(signal_log_handler)

        with qtbot.waitSignal(dummy.dummy_signal) as f:
            logger.info("Spam!")
        logger.removeHandler(signal_log_handler)


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


class TestSimplePopup:
    def test_cancel_aborts(self, qtbot):
        app = speedwagon.startup.SimpleWindow(Mock())
        pop_up_window = speedwagon.startup.SimplePopup(app)
        qtbot.add_widget(pop_up_window)

        with qtbot.waitSignal(app.abort):
            pop_up_window.button_box.button(
                QtWidgets.QDialogButtonBox.Cancel
            ).click()


class TestBackgroundThreadLauncher:
    def test_have_no_window_fails(self):
        with speedwagon.runner_strategies.BackgroundJobManager() as manager:
            launcher = speedwagon.startup.BackgroundThreadLauncher(manager)
            with pytest.raises(RuntimeError) as e:
                # launcher.workflow_name = "spam"
                launcher.start()
            assert "active window" in str(e.value)


class TestGuiJobCallbacks:
    @pytest.fixture()
    def background_thread_launcher(self):
        launcher = Mock()
        return launcher

    @pytest.fixture()
    def gui_job_callbacks(self, background_thread_launcher):
        return speedwagon.startup.GuiJobCallbacks(background_thread_launcher)

    def test_refresh_calls_process_events(self, gui_job_callbacks, monkeypatch):
        processEvents = Mock()
        monkeypatch.setattr(
            speedwagon.startup.QtWidgets.QApplication,
            "processEvents",
            processEvents
        )
        gui_job_callbacks.refresh()
        assert processEvents.called is True

    def test_error_opens_error_message(self, gui_job_callbacks, qtbot, monkeypatch):
        error = Mock()

        def QMessageBox():
            return error

        Critical = speedwagon.startup.QtWidgets.QMessageBox.Critical
        monkeypatch.setattr(
            speedwagon.startup.QtWidgets,
            "QMessageBox",
            QMessageBox
        )
        speedwagon.startup.QtWidgets.QMessageBox.Critical = Critical
        gui_job_callbacks.error("Failed!")
        error.setText.assert_called_with("Failed!")

    def test_update_progress(
            self,
            gui_job_callbacks,
            background_thread_launcher
    ):
        gui_job_callbacks.update_progress(10, 100)
        progress = background_thread_launcher.window.progress
        progress.setMaximum.assert_called_with(100)
        progress.setValue.assert_called_with(10)

    def test_done(self, gui_job_callbacks, background_thread_launcher):
        gui_job_callbacks.done()
        window = background_thread_launcher.window
        assert window.done.emit.called is True


class TestWorkflowProgressCallbacks:
    def test_job_changed_signal(self, qtbot):
        callbacks = speedwagon.startup.WorkflowProgressCallbacks(Mock())
        with qtbot.waitSignal(callbacks.signals.total_jobs_changed) as blocker:
            callbacks.update_progress(1, 10)

    def test_job_log_signal(self, qtbot):
        callbacks = speedwagon.startup.WorkflowProgressCallbacks(Mock())
        with qtbot.waitSignal(callbacks.signals.message) as blocker:
            callbacks.log("dummy", logging.INFO)

    def test_job_cancel_completed_signal(self, qtbot):
        callbacks = speedwagon.startup.WorkflowProgressCallbacks(Mock())
        with qtbot.waitSignal(callbacks.signals.cancel_complete) as blocker:
            callbacks.cancelling_complete()

    def test_job_done_signal(self, qtbot):
        callbacks = speedwagon.startup.WorkflowProgressCallbacks(Mock())
        with qtbot.waitSignal(callbacks.signals.success_achieved) as blocker:
            callbacks.done()

    def test_set_banner_text(self, qtbot):
        dialog_box = Mock()
        callbacks = speedwagon.startup.WorkflowProgressCallbacks(dialog_box)
        callbacks.set_banner_text("something new")
        dialog_box.banner.setText.assert_called_with("something new")


class TestStartQtThreaded:
    def test_save_log_opens_dialog(self, qtbot, monkeypatch):
        app = Mock()

        getSaveFileName = Mock(
            return_value=("dummy", None)
        )

        monkeypatch.setattr(
            speedwagon.startup.QtWidgets.QFileDialog,
            "getSaveFileName",
            getSaveFileName
        )

        starter = speedwagon.startup.StartQtThreaded(app)
        parent = Mock()
        with patch('speedwagon.startup.open', mock_open()) as w:
            starter.save_log(parent)
        assert getSaveFileName.called is True

    def test_save_log_error(self, qtbot, monkeypatch):
        # Make sure that a dialog with an error message pops up if there is a
        # problem with saving the log

        save_file_return_name = "dummy"

        def getSaveFileName(*args, **kwargs):
            return save_file_return_name, None

        monkeypatch.setattr(
            speedwagon.startup.QtWidgets.QFileDialog,
            "getSaveFileName",
            getSaveFileName
        )

        starter = speedwagon.startup.StartQtThreaded(Mock())
        QMessageBox = Mock()

        def side_effect_for_saving(*args, **kwargs):
            # Set the filename to None so that the function thinks it was
            # canceled during the second loop otherwise, this will run as an
            # infinite loop
            nonlocal save_file_return_name
            save_file_return_name = None

            raise OSError("nope")

        monkeypatch.setattr(
            speedwagon.startup.QtWidgets,
            "QMessageBox",
            QMessageBox
        )

        with patch('speedwagon.startup.open', mock_open()) as mock:
            mock.side_effect = side_effect_for_saving
            starter.save_log(None)

        assert QMessageBox.called is True

    def test_request_system_info(self, monkeypatch):
        SystemInfoDialog = Mock()

        monkeypatch.setattr(
            speedwagon.startup.speedwagon.dialog.dialogs,
            "SystemInfoDialog",
            SystemInfoDialog
        )

        speedwagon.startup.StartQtThreaded.request_system_info()
        assert SystemInfoDialog.called is True

    def test_request_settings_opens_setting_dialog(self, qtbot, monkeypatch):
        exec_ = Mock()
        monkeypatch.setattr(SettingsDialog, "exec_", exec_)

        monkeypatch.setattr(
            speedwagon.dialog.settings.GlobalSettingsTab,
            "read_config_data",
            Mock()
        )

        monkeypatch.setattr(
            speedwagon.dialog.settings.TabsConfigurationTab,
            "load",
            Mock()
        )

        speedwagon.startup.StartQtThreaded.request_settings()
        assert exec_.called is True

    def test_run_opens_window(self, qtbot, monkeypatch):
        app = Mock()
        show = Mock()

        monkeypatch.setattr(
            speedwagon.startup.speedwagon.gui.MainWindow2,
            "show",
            show
        )

        starter = speedwagon.startup.StartQtThreaded(app)
        starter.load_custom_tabs = Mock()
        starter.load_all_workflows_tab = Mock()
        starter.run()
        assert show.called is True

    def test_load_custom_tabs(self, qtbot, monkeypatch):
        app = Mock()
        starter = speedwagon.startup.StartQtThreaded(app)

        tabs_file = "somefile.yml"

        loaded_workflows = Mock()

        monkeypatch.setattr(
            speedwagon.startup.os.path,
            "getsize",
            Mock(return_value=10)
        )

        monkeypatch.setattr(
            speedwagon.startup,
            "get_custom_tabs",
            Mock(return_value=[
                ("dummy", {})
            ])
        )
        main_window = Mock()

        starter.load_custom_tabs(
            main_window=main_window,
            tabs_file=tabs_file,
            loaded_workflows=loaded_workflows
        )

        main_window.add_tab.assert_called_with("dummy", ANY)

    def test_load_help(self, qtbot, monkeypatch):
        show = Mock()

        monkeypatch.setattr(
            speedwagon.startup.speedwagon.gui.MainWindow2,
            "show",
            show
        )

        starter = speedwagon.startup.StartQtThreaded(Mock())
        starter.load_custom_tabs = Mock()
        starter.load_all_workflows_tab = Mock()
        starter.run()
        open_new = Mock()

        def metadata(*args, **kwargs):
            return {'Home-page': "https://www.fake.com"}

        monkeypatch.setattr(speedwagon.startup.metadata, "metadata", metadata)
        monkeypatch.setattr(speedwagon.startup.webbrowser, "open_new", open_new)
        qtbot.addWidget(starter.windows)
        starter.windows.help_requested.emit()
        assert open_new.called is True
