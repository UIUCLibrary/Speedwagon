import argparse
import json
import logging
import os

import pytest
gui_startup = pytest.importorskip("speedwagon.frontend.qtwidgets.gui_startup")
from unittest.mock import Mock, MagicMock, patch, mock_open, ANY
from PySide6 import QtWidgets
import speedwagon.config
import io
# from speedwagon.frontend.qtwidgets import gui_startup
from speedwagon.frontend.qtwidgets.dialog import dialogs
from speedwagon.frontend.qtwidgets.dialog.settings import SettingsDialog



def test_standalone_tab_editor_loads(qtbot, monkeypatch):
    TabsEditorApp = MagicMock()
    monkeypatch.setattr(speedwagon.startup.frontend.qtwidgets.gui_startup, "TabsEditorApp", TabsEditorApp)
    app = Mock()
    settings = Mock()
    get_platform_settings = Mock(return_value=settings)
    settings.get_app_data_directory = Mock(return_value=".")

    monkeypatch.setattr(
        speedwagon.config,
        "get_platform_settings",
        get_platform_settings
    )

    gui_startup.standalone_tab_editor(app)
    assert app.exec.called is True


class TestTabsEditorApp:
    def test_on_okay_closes(self, qtbot):
        editor = gui_startup.TabsEditorApp()
        qtbot.addWidget(editor)
        editor.close = Mock()
        editor.on_okay()
        assert editor.close.called is True


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

    monkeypatch.setattr(
        speedwagon.config.NixConfig,
        "get_user_data_directory",
        lambda _: '~'
    )

    standard_startup = gui_startup.StartupGuiDefault(app=app)

    standard_startup.startup_settings['debug'] = True
    tabs_file = tmpdir / "tabs.yaml"
    tabs_file.ensure()

    # get_app_data_directory

    standard_startup.tabs_file = tabs_file

    monkeypatch.setattr(QtWidgets, "QSplashScreen", MagicMock())
    monkeypatch.setattr(
        speedwagon.frontend.qtwidgets.gui,
        "MainWindow1",
        MagicMock()
    )
    standard_startup._logger = Mock()
    standard_startup.run()
    assert app.exec_.called is True

class TestStartupDefault:
    @pytest.fixture
    def parse_args(self):
        def parse(*args, **kwargs):
            return argparse.Namespace(
                debug=False,
                start_tab="main"
            )
        return parse

    def test_invalid_setting_logs_warning(
            self,
            caplog,
            monkeypatch,
            parse_args
    ):

        def update(*_, **__):
            raise ValueError("oops")
        # Monkey patch Path.home() because this will fail on linux systems if
        # uid not found. For example: in some docker containers
        monkeypatch.setattr(
            speedwagon.config.Path, "home", lambda: "my_home"
        )

        monkeypatch.setattr(
            speedwagon.startup.argparse.ArgumentParser,
            "parse_args",
            parse_args
        )

        monkeypatch.setattr(
            speedwagon.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )
        startup_worker = gui_startup.StartupGuiDefault(app=Mock())
        resolution = Mock(FRIENDLY_NAME="dummy")
        resolution.update = lambda _: update()

        loader = speedwagon.config.ConfigLoader(startup_worker.config_file)
        loader.resolution_strategy_order = [resolution]

        startup_worker.resolve_settings(
            resolution_order=[resolution],
            loader=loader
        )

        assert any("oops is an invalid setting" in m for m in caplog.messages)

    def test_invalid_setting_logs_warning_for_ConfigFileSetter(
            self, caplog, monkeypatch, parse_args):

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

        monkeypatch.setattr(
            speedwagon.startup.argparse.ArgumentParser,
            "parse_args",
            parse_args
        )

        startup_worker = gui_startup.StartupGuiDefault(app=Mock())
        resolution = Mock(FRIENDLY_NAME="dummy")
        resolution.__class__ = speedwagon.config.ConfigFileSetter
        resolution.update = lambda _: update()
        startup_worker.resolve_settings(resolution_order=[resolution])
        assert any("contains an invalid setting" in m for m in caplog.messages)

    def test_missing_debug_setting(self, caplog, monkeypatch, parse_args):
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

        startup_worker = gui_startup.StartupGuiDefault(app=Mock())
        startup_worker.startup_settings = {"sss": "dd"}

        monkeypatch.setattr(
            speedwagon.startup.argparse.ArgumentParser,
            "parse_args",
            parse_args
        )

        loader = speedwagon.config.ConfigLoader(startup_worker.config_file)
        loader.resolution_strategy_order = []
        loader.startup_settings = {"sss": "dd"}

        startup_worker.resolve_settings(
            resolution_order=[],
            loader=loader
        )

        assert any(
            "Unable to find a key for debug mode" in m for m in caplog.messages
        )

    def test_default_resolve_settings_calls_default_setter(self, monkeypatch):

        def update(*_, **__):
            raise ValueError("oops")

        default_setter = MagicMock()
        monkeypatch.setattr(
            speedwagon.config, "DefaultsSetter", default_setter
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
            speedwagon.config.CliArgsSetter, "update", MagicMock()
        )

        startup_worker = \
            gui_startup.StartupGuiDefault(app=Mock(name="app"))

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
        startup_worker = gui_startup.StartupGuiDefault(app=Mock())
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
        monkeypatch.setattr(speedwagon.config.pathlib.Path, "touch", touch)

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
        startup_worker = gui_startup.StartupGuiDefault(app=Mock())
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
        monkeypatch.setattr(speedwagon.config.os, "makedirs", makedirs)

        touch = Mock()
        monkeypatch.setattr(speedwagon.config.pathlib.Path, "touch", touch)

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
            startup = gui_startup.SingleWorkflowJSON(app=None)
            startup.options = Mock()
            startup.workflow = None
            startup.run()
        assert "workflow" in str(error.value).lower()

    def test_run_without_options_raises_exception(self):
        with pytest.raises(ValueError) as error:
            startup = gui_startup.SingleWorkflowJSON(app=None)
            startup.options = None
            startup.workflow = Mock()
            startup.run()
        assert "no data" in str(error.value).lower()

    def test_runner_strategies_called(self, monkeypatch, qtbot):
        import tracemalloc
        tracemalloc.start()
        monkeypatch.setattr(
            dialogs.WorkflowProgress,
            "show",
            lambda *args, **kwargs: None
        )

        startup = gui_startup.SingleWorkflowJSON(app=None)
        startup.load_json_string(
            json.dumps(
                {
                    "Workflow": "Zip Packages",
                    "Configuration": {
                        "Source": "dummy_source",
                        "Output": "dummy_out"
                    }
                }
            )
        )

        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.gui,
            "MainWindow2",
            Mock()
        )

        submit_job = MagicMock()

        monkeypatch.setattr(
            speedwagon.runner_strategies.BackgroundJobManager,
            "submit_job",
            submit_job
        )

        monkeypatch.setattr(
            dialogs.WorkflowProgress,
            "exec",
            Mock()
        )

        startup.workflow.validate_user_options = Mock(return_value=True)
        startup.run()
        assert submit_job.called is True

    def test_signal_is_sent(self, qtbot):
        from PySide6 import QtCore
        class Dummy(QtCore.QObject):
            dummy_signal = QtCore.Signal(str, int)

            def __init__(self):
                super().__init__()
                self.dummy_signal.connect(self.d)

            def d(self, message, level):
                print("hhh")

        dummy = Dummy()

        signal_log_handler = \
            speedwagon.frontend.qtwidgets.logging_helpers.SignalLogHandler(
                dummy.dummy_signal
            )

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logger.addHandler(signal_log_handler)

        with qtbot.waitSignal(dummy.dummy_signal) as f:
            logger.info("Spam!")
        logger.removeHandler(signal_log_handler)

    def test_run_on_exit_is_called(self, qtbot, monkeypatch):
        from PySide6 import QtWidgets
        startup = speedwagon.frontend.qtwidgets.gui_startup.SingleWorkflowJSON(app=None)
        startup.options = {}
        workflow = Mock()
        workflow.name = "spam"
        startup.workflow = workflow
        startup.on_exit = Mock()

        MainWindow2 = QtWidgets.QMainWindow()
        MainWindow2.logger = Mock()
        MainWindow2.console = Mock()
        MainWindow2.show = Mock()
        qtbot.addWidget(MainWindow2)
        monkeypatch.setattr(
            dialogs.WorkflowProgress,
            "exec",
            Mock()
        )
        monkeypatch.setattr(
            speedwagon.runner_strategies.BackgroundJobManager,
            "run_job_on_thread",
            lambda *args, **kwargs: Mock()
        )
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.gui,
            "MainWindow2",
            lambda _: MainWindow2
        )

        monkeypatch.setattr(
            dialogs.WorkflowProgress,
            "show",
            lambda *args, **kwargs: None
        )

        startup.run()
        assert startup.on_exit.called is True

    def test_load_json(self):
        startup = gui_startup.SingleWorkflowJSON(app=None)

        startup.load_json_string(
            json.dumps(
                {
                    "Workflow": "Zip Packages",
                    "Configuration": {
                        "Source": "dummy_source",
                        "Output": "dummy_out"
                    }
                }
            )
        )

        assert startup.options["Source"] == "dummy_source" and \
               startup.options["Output"] == "dummy_out" and \
               startup.workflow.name == 'Zip Packages'

class TestMultiWorkflowLauncher:
    def test_all_workflows_validate_user_options(self, qtbot, monkeypatch):
        startup_launcher = gui_startup.MultiWorkflowLauncher(app=None)
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

        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.gui.MainWindow1,
            "show", lambda self: None
        )

        for workflow_name, workflow_args in workflow_tasks:
            mock_workflow = MagicMock()
            mock_workflow.name = workflow_name
            mock_workflow.__class__ = speedwagon.job.Workflow
            jobs.append(mock_workflow)
            startup_launcher.add_job(mock_workflow, workflow_args)
        startup_launcher.run()
        assert all(job.validate_user_options.called is True for job in jobs)

    def test_task_failing(self, qtbot):
        startup_launcher = gui_startup.MultiWorkflowLauncher(app=None)
        mock_workflow = MagicMock()
        mock_workflow.name = 'Verify Checksum Batch [Single]'
        mock_workflow.__class__ = speedwagon.job.Workflow
        mock_workflow.initial_task = \
            Mock(
                side_effect=speedwagon.frontend.qtwidgets.runners.TaskFailed()
            )

        startup_launcher.add_job(
            mock_workflow,
            {
                    "Input": os.path.join("somepath", "checksum.md5")
                }
         )
        with pytest.raises(speedwagon.exceptions.JobCancelled):
            startup_launcher.run()

class TestStartQtThreaded:
    @pytest.fixture(scope="function")
    def starter(self, monkeypatch, qtbot):
        monkeypatch.setattr(
            speedwagon.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )

        monkeypatch.setattr(
            speedwagon.config.Path,
            "home",
            lambda *_: "/usr/home"
        )

        app = Mock()
        startup = gui_startup.StartQtThreaded(app)
        yield startup
        if startup.windows is not None:
            startup.windows.close()
        startup.app.closeAllWindows()

    def test_report_exception(self, qtbot, monkeypatch, starter):
        from PySide6 import QtWidgets
        message_box = Mock(name="QMessageBox")

        monkeypatch.setattr(
            QtWidgets,
            "QMessageBox",
            Mock(return_value=message_box)
        )

        error_message = "I'm an error"

        exc = ValueError(error_message)
        starter.report_exception(exc)
        message_box.setText.assert_called_with(error_message)

    def test_save_workflow_config(self, qtbot, starter):
        dialog = Mock()
        dialog.getSaveFileName = MagicMock(return_value=("make_jp2.json", ""))

        serialization_strategy = Mock()
        starter.save_workflow_config(
            workflow_name="Spam",
            data={},
            dialog_box=dialog,
            serialization_strategy=serialization_strategy
        )
        assert serialization_strategy.save.called is True

    def test_load_workflow_config(self, qtbot, starter):
        dialog = Mock()
        dialog.getOpenFileName = MagicMock(return_value=("make_jp2.json", ""))

        serialization_strategy = MagicMock()
        serialization_strategy.load = Mock(return_value=("name", {}))
        starter.import_workflow_config(
            parent=Mock(),
            dialog_box=dialog,
            serialization_strategy=serialization_strategy
        )
        assert serialization_strategy.load.called is True

    def test_save_log_opens_dialog(self, qtbot, monkeypatch, starter):
        from PySide6 import QtWidgets
        getSaveFileName = Mock(
            return_value=("dummy", None)
        )

        monkeypatch.setattr(
            QtWidgets.QFileDialog,
            "getSaveFileName",
            getSaveFileName
        )
        parent = Mock()
        with patch('speedwagon.startup.frontend.qtwidgets.gui_startup', mock_open()) as w:
            starter.save_log(parent)
        assert getSaveFileName.called is True

    def test_save_log_error(self, qtbot, monkeypatch, starter):
        # Make sure that a dialog with an error message pops up if there is a
        # problem with saving the log

        save_file_return_name = "dummy"

        def getSaveFileName(*args, **kwargs):
            return save_file_return_name, None

        from PySide6 import QtWidgets
        monkeypatch.setattr(
            QtWidgets.QFileDialog,
            "getSaveFileName",
            getSaveFileName
        )

        QMessageBox = Mock()

        def side_effect_for_saving(*args, **kwargs):
            # Set the filename to None so that the function thinks it was
            # canceled during the second loop otherwise, this will run as an
            # infinite loop
            nonlocal save_file_return_name
            save_file_return_name = None

            raise OSError("nope")

        monkeypatch.setattr(
            QtWidgets,
            "QMessageBox",
            QMessageBox
        )
        with patch('speedwagon.frontend.qtwidgets.gui_startup.open', mock_open()) as mock:
            mock.side_effect = side_effect_for_saving
            starter.save_log(None)

        assert QMessageBox.called is True

    def test_request_system_info(self, monkeypatch, qtbot):
        SystemInfoDialog = Mock()

        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.dialog.dialogs,
            "SystemInfoDialog",
            SystemInfoDialog
        )

        gui_startup.StartQtThreaded.request_system_info()
        assert SystemInfoDialog.called is True

    def test_request_settings_opens_setting_dialog(self, qtbot, monkeypatch):
        exec_ = Mock()
        monkeypatch.setattr(SettingsDialog, "exec_", exec_)

        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.dialog.settings.GlobalSettingsTab,
            "read_config_data",
            Mock()
        )

        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.dialog.settings.TabsConfigurationTab,
            "load",
            Mock()
        )

        monkeypatch.setattr(
            speedwagon.config.Path,
            "home",
            lambda *_: "/usr/home"
        )

        monkeypatch.setattr(
            speedwagon.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )

        gui_startup.StartQtThreaded.request_settings()
        assert exec_.called is True

    def test_run_opens_window(self, qtbot, monkeypatch, starter):

        main_window2 = Mock(spec=speedwagon.frontend.qtwidgets.gui.MainWindow2)
        main_window2.show = Mock()
        main_window2.console = Mock()
        MainWindow2 = Mock(
            name="MainWindow2",
            return_value=main_window2,
        )
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.gui,
            "MainWindow2",
            MainWindow2
        )

        starter.load_custom_tabs = Mock()
        starter.load_all_workflows_tab = Mock()
        starter.run()
        assert main_window2.show.called is True

    def test_load_custom_tabs(self, qtbot, monkeypatch, starter):
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

    def test_load_help_no_package_info(
            self,
            qtbot,
            monkeypatch,
            caplog,
            starter
    ):
        show = Mock()

        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.gui.MainWindow2,
            "show",
            show
        )

        starter.load_custom_tabs = Mock()
        starter.load_all_workflows_tab = Mock()
        starter.run()

        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.gui_startup.metadata,
            "metadata",
            Mock(
                side_effect=speedwagon.frontend.qtwidgets.gui_startup.metadata.PackageNotFoundError(
                    "Not found yet"
                )
            )
        )
        starter.windows.help_requested.emit()
        assert any(
            "No help link available" in m for m in caplog.messages
        )

    def test_load_help(self, qtbot, monkeypatch, starter):
        show = Mock()

        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.gui.MainWindow2,
            "show",
            show
        )

        starter.load_custom_tabs = Mock()
        starter.load_all_workflows_tab = Mock()
        starter.run()
        open_new = Mock()

        def metadata(*args, **kwargs):
            return {'Home-page': "https://www.fake.com"}

        monkeypatch.setattr(speedwagon.frontend.qtwidgets.gui_startup.metadata, "metadata", metadata)

        monkeypatch.setattr(
            speedwagon.startup.frontend.qtwidgets.gui_startup.webbrowser,
            "open_new",
            open_new
        )

        qtbot.addWidget(starter.windows)
        starter.windows.help_requested.emit()
        assert open_new.called is True

    def test_resolve_settings_calls_get_settings(
            self,
            qtbot,
            monkeypatch,
            starter
    ):
        starter.load_custom_tabs = Mock()
        starter.load_all_workflows_tab = Mock()
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.gui.MainWindow2,
            "show",
            lambda *args, **kwargs: None
        )

        starter.run()
        loader = Mock()
        loader.get_settings = Mock(return_value={})
        loader.read_settings_file = Mock(return_value={})
        starter.resolve_settings(resolution_order=[], loader=loader)
        try:
            assert loader.get_settings.called is True
        finally:
            starter.windows.console.detach_logger()

    def test_read_settings_file(self, qtbot, monkeypatch, starter):
        read = Mock()

        monkeypatch.setattr(
            speedwagon.config.configparser.ConfigParser,
            "read",
            read
        )

        starter.read_settings_file("somefile")
        read.assert_called_with("somefile")

    def test_request_more_info_emits_request_signal(self, qtbot, starter):
        workflow = Mock()
        options = {}
        pre_results = []
        wait_condition = MagicMock()
        with qtbot.waitSignal(starter._request_window.request):
            starter.request_more_info(
                workflow,
                options,
                pre_results,
                wait_condition=wait_condition
            )

    def test_submit_job_errors_on_unknown_workflow(
            self,
            qtbot,
            monkeypatch,
            starter
    ):
        from PySide6 import QtWidgets
        main_app = QtWidgets.QWidget()
        job_manager = Mock()
        workflow_name = "unknown_workflow"
        options = {}
        starter.report_exception = Mock()

        # Simulate no valid workflow
        monkeypatch.setattr(
            speedwagon.startup.job, "available_workflows", lambda: {}
        )

        starter.submit_job(
            main_app,
            job_manager,
            workflow_name,
            options
        )
        assert starter.report_exception.called is True

    def test_submit_job_submits_to_job_manager(
            self,
            qtbot,
            monkeypatch,
            starter
    ):
        monkeypatch.setattr(
            speedwagon.config.Path, "home", lambda: "my_home"
        )
        monkeypatch.setattr(
            speedwagon.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )

        job_manager = Mock()
        workflow_name = "spam"
        options = {}
        starter.report_exception = Mock()
        spam_workflow = Mock()

        monkeypatch.setattr(
            speedwagon.startup.job,
            "available_workflows",
            lambda: {"spam": spam_workflow}
        )
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.dialog.dialogs.WorkflowProgress,
            "show",
            lambda *args, **kwargs: None
        )

        starter.submit_job(
            job_manager,
            workflow_name,
            options
        )
        assert job_manager.submit_job.called is True


class TestWorkflowProgressCallbacks:

    @pytest.fixture()
    def dialog_box(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            dialogs.WorkflowProgress,
            "show",
            lambda *args, **kwargs: None
        )

        widget = dialogs.WorkflowProgress()
        monkeypatch.setattr(
            dialogs.WorkflowProgressStateWorking,
            "close_dialog", lambda self, event: None)
        qtbot.add_widget(widget)
        yield widget
        widget.close()

    def test_job_changed_signal(self, dialog_box, qtbot):
        callbacks = \
            speedwagon.frontend.qtwidgets.runners.WorkflowProgressCallbacks(
                dialog_box
            )

        with qtbot.waitSignal(callbacks.signals.total_jobs_changed) as blocker:
            callbacks.update_progress(1, 10)

    def test_job_progress_none_total_does_not_trigger(self, dialog_box, qtbot):
        callbacks = \
            speedwagon.frontend.qtwidgets.runners.WorkflowProgressCallbacks(
                dialog_box
            )

        with qtbot.assertNotEmitted(
                callbacks.signals.total_jobs_changed
        ) as blocker:
            callbacks.update_progress(10, None)

    def test_job_progress_none_current_does_not_trigger(
            self,
            dialog_box,
            qtbot
    ):
        callbacks = \
            speedwagon.frontend.qtwidgets.runners.WorkflowProgressCallbacks(
                dialog_box
            )

        with qtbot.assertNotEmitted(callbacks.signals.progress_changed) as \
                blocker:
            callbacks.update_progress(None, 10)

    def test_job_log_signal(self, dialog_box, qtbot):
        callbacks = \
            speedwagon.frontend.qtwidgets.runners.WorkflowProgressCallbacks(
                dialog_box
            )

        with qtbot.waitSignal(callbacks.signals.message) as blocker:
            callbacks.log("dummy", logging.INFO)

    def test_job_cancel_completed_signal(self, dialog_box, qtbot):
        callbacks = \
            speedwagon.frontend.qtwidgets.runners.WorkflowProgressCallbacks(
                dialog_box
            )

        with qtbot.waitSignal(callbacks.signals.cancel_complete) as blocker:
            callbacks.cancelling_complete()

    def test_job_finished_signal(self, dialog_box, qtbot):
        callbacks = \
            speedwagon.frontend.qtwidgets.runners.WorkflowProgressCallbacks(
                dialog_box
            )

        with qtbot.waitSignal(callbacks.signals.finished) as blocker:
            callbacks.finished(speedwagon.runner_strategies.JobSuccess.SUCCESS)

    def test_job_status_signal(self, dialog_box, qtbot):
        callbacks = \
            speedwagon.frontend.qtwidgets.runners.WorkflowProgressCallbacks(
                dialog_box
            )

        with qtbot.waitSignal(callbacks.signals.status_changed) as blocker:
            blocker.connect(callbacks.signals.status_changed)
            callbacks.status("some_other_status")

        assert "some_other_status" in blocker.args

    def test_set_banner_text(self, dialog_box, qtbot):
        dialog_box.banner.setText = Mock()
        callbacks = \
            speedwagon.frontend.qtwidgets.runners.WorkflowProgressCallbacks(
                dialog_box
            )

        callbacks.set_banner_text("something new")
        dialog_box.banner.setText.assert_called_with("something new")

    @pytest.mark.parametrize("message,exc,traceback", [
        ("Something", None, None),
        (None, OSError(), None),
        (None, OSError(), "Some traceback info"),
    ])
    def test_error(
            self,
            qtbot,
            dialog_box,
            monkeypatch,
            message,
            exc,
            traceback
    ):
        from PySide6 import QtWidgets
        callbacks = \
            speedwagon.frontend.qtwidgets.runners.WorkflowProgressCallbacks(
                dialog_box
            )

        QMessageBox = Mock()

        monkeypatch.setattr(
            QtWidgets,
            "QMessageBox",
            QMessageBox
        )

        with qtbot.waitSignal(callbacks.signals.error) as blocker:
            blocker.connect(callbacks.signals.error)
            callbacks.error(message, exc, traceback)
        assert QMessageBox.called is True

    def test_start_calls_start_signal(self, dialog_box, qtbot):

        callbacks = \
            speedwagon.frontend.qtwidgets.runners.WorkflowProgressCallbacks(
                dialog_box
            )

        with qtbot.waitSignal(callbacks.signals.started):
            callbacks.start()

    def test_refresh_calls_process_events(
            self,
            dialog_box,
            monkeypatch,
            qtbot
    ):
        from PySide6 import QtCore
        callbacks = \
            speedwagon.frontend.qtwidgets.runners.WorkflowProgressCallbacks(
                dialog_box
            )

        processEvents = Mock()
        monkeypatch.setattr(
            QtCore.QCoreApplication,
            "processEvents",
            processEvents
        )
        callbacks.refresh()
        assert processEvents.called is True

class TestQtRequestMoreInfo:
    def test_job_cancelled(self, qtbot):
        from PySide6 import QtWidgets
        info_request = \
            speedwagon.frontend.qtwidgets.user_interaction.QtRequestMoreInfo(
                QtWidgets.QWidget()
            )

        user_is_interacting = MagicMock()
        workflow = Mock()
        exc = speedwagon.exceptions.JobCancelled()
        workflow.get_additional_info = Mock(
            side_effect=exc
        )
        options = Mock()
        pre_results = Mock()

        info_request.request_more_info(
            user_is_interacting,
            workflow,
            options,
            pre_results
        )
        assert info_request.exc == exc

    def test_job_exception_passes_on(self, qtbot):
        from PySide6 import QtWidgets
        info_request = \
            speedwagon.frontend.qtwidgets.user_interaction.QtRequestMoreInfo(
                QtWidgets.QWidget()
            )

        user_is_interacting = MagicMock()
        workflow = Mock()
        workflow.get_additional_info = Mock(
            side_effect=ValueError("ooops")
        )
        options = Mock()
        pre_results = Mock()
        with pytest.raises(ValueError):
            info_request.request_more_info(
                user_is_interacting,
                workflow,
                options,
                pre_results
            )


class TestRunCommand:
    def test_application_launcher_called(self, monkeypatch):
        f = io.StringIO('{"Workflow":"dummy", "Configuration": {}}')
        args = argparse.Namespace(json=f)

        ApplicationLauncher = Mock()

        monkeypatch.setattr(
            speedwagon.job,
            "available_workflows",
            lambda: MagicMock()
        )

        monkeypatch.setattr(
            speedwagon.startup,
            "ApplicationLauncher",
            ApplicationLauncher
        )

        run_command = speedwagon.startup.RunCommand(args)
        with pytest.raises(SystemExit):
            run_command.run()
        assert ApplicationLauncher.called is True


def test_start_up_tab_editor(monkeypatch):
    standalone_tab_editor = Mock()

    with monkeypatch.context() as mp:
        mp.setattr(speedwagon.frontend.qtwidgets.gui_startup,
                   "standalone_tab_editor",
                   standalone_tab_editor)

        speedwagon.startup.main(argv=["tab-editor"])
        assert standalone_tab_editor.called is True