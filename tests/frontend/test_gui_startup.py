import argparse
import json
import logging
import os
import pathlib
import webbrowser

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open, ANY, call
import io
import sys


if sys.version_info >= (3, 10):  # pragma: no cover
    import importlib.metadata as importlib_metadata
else:  # pragma: no cover
    import importlib_metadata

from speedwagon.workflow import FileSelectData
import speedwagon.config

QtCore = pytest.importorskip('PySide6.QtCore')
QtWidgets = pytest.importorskip('PySide6.QtWidgets')

from speedwagon.frontend.qtwidgets.gui import MainWindow3
gui_startup = pytest.importorskip("speedwagon.frontend.qtwidgets.gui_startup")

from speedwagon.frontend.qtwidgets.dialog import dialogs
from speedwagon.frontend.qtwidgets.dialog.settings import SettingsDialog, TabEditor, GlobalSettingsTab, SettingsBuilder
from speedwagon.frontend.qtwidgets.models.tabs import AbsLoadTabDataModelStrategy
from speedwagon.frontend.qtwidgets.gui_startup import save_workflow_config, TabsEditorApp
from speedwagon.frontend.qtwidgets.models import tabs as tab_models
from speedwagon.config import StandardConfigFileLocator
import speedwagon.workflows.builtin
from speedwagon.tasks import system as system_tasks
from speedwagon.job import AbsWorkflowFinder

def test_standalone_tab_editor_loads(qtbot, monkeypatch):
    TabsEditorApp = MagicMock()

    monkeypatch.setattr(
        speedwagon.frontend.qtwidgets.gui_startup,
        "TabsEditorApp",
        TabsEditorApp
    )

    app = Mock()
    settings = Mock()
    get_platform_settings = Mock(return_value=settings)
    settings.get_app_data_directory = Mock(return_value=".")

    monkeypatch.setattr(
        speedwagon.config,
        "get_platform_settings",
        get_platform_settings
    )

    with pytest.raises(SystemExit):
        gui_startup.standalone_tab_editor(app)
    assert app.exec.called is True


class TestTabsEditorApp:
    @pytest.fixture()
    def app(self, monkeypatch):
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            'get_tabs_file',
            lambda *_: 'dummy.yml'
        )
        return TabsEditorApp()
    def test_on_okay_closes(self, qtbot, app):
        qtbot.addWidget(app)
        app.close = Mock()
        app.on_okay()
        assert app.close.called is True

    def test_save_on_modify(self, qtbot, monkeypatch, app):
        qtbot.addWidget(app)
        editor: TabEditor = app.editor

        class DummyLoader(AbsLoadTabDataModelStrategy):
            def load(self, model) -> None:
                class Spam1(speedwagon.Workflow):
                    name = "spam 1"

                class Spam2(speedwagon.Workflow):
                    name = "spam 2"

                class Spam3(speedwagon.Workflow):
                    name = "spam 3"

                model.append_workflow_tab("All", [Spam1, Spam2, Spam3])
                model.append_workflow_tab("Eggs", [Spam1])
        # editor.set_tab_visibility("Eggs", True)
        editor.load_tab_data_model_strategy = DummyLoader()
        editor.load_data()
        mo = editor.all_workflows_list_view.model()

        qtbot.mouseClick(
            editor.all_workflows_list_view.viewport(),
            QtCore.Qt.LeftButton,
            pos=editor.all_workflows_list_view.visualRect(
                mo.index(1,0)
            ).center()
        )

        assert editor.model.rowCount(editor.model.index(1)) == 1
        with qtbot.waitSignal(editor.model.dataChanged):
            qtbot.mouseClick(
                editor.add_items_button,
                QtCore.Qt.LeftButton,
            )

        def get_error_info():
            existing_tabs = [
                editor.model.data(
                    editor.model.index(i, parent=editor.model.index(1))
                )
                for i in range(editor.model.rowCount(editor.model.index(1)))
            ]
            return f"Got the following workflows loaded: {*existing_tabs,}"

        assert \
            editor.model.rowCount(editor.model.index(1)) == 2, \
            get_error_info()
        save = Mock()
        monkeypatch.setattr(app, "get_tab_config_strategy", Mock(return_value=Mock(save=save)))
        okay_button = app.dialog_button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        qtbot.mouseClick(
            okay_button,
            QtCore.Qt.LeftButton,
        )
        save.assert_called_with(
            [
                speedwagon.config.tabs.CustomTabData(
                    tab_name='Eggs',
                    workflow_names=["spam 1", "spam 2"]
                )
            ]
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
        monkeypatch.setattr(
            speedwagon.config,
            "get_whitelisted_plugins",
            lambda: []
        )
        workflow = Mock()
        workflow.name = "Zip Packages"

        workflow_klass = Mock(return_value=workflow)
        monkeypatch.setattr(
            speedwagon.job,
            "available_workflows",
            lambda: {"Zip Packages": workflow_klass}
        )
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
            "MainWindow3",
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

    def test_run_on_exit_is_called(self, qtbot, monkeypatch):
        startup = \
            speedwagon.frontend.qtwidgets.gui_startup.SingleWorkflowJSON(
                app=None
            )
        exit_calls = []
        monkeypatch.setattr(QtWidgets.QApplication, 'exit', lambda: exit_calls.append(1))

        startup.options = {}
        workflow = Mock()
        workflow.name = "spam"
        startup.workflow = workflow
        startup.on_exit = Mock()

        MainWindow3 = QtWidgets.QMainWindow()
        # MainWindow3.logger = Mock()
        # MainWindow3.console = Mock()
        # MainWindow3.show = Mock()
        qtbot.addWidget(MainWindow3)
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
            "MainWindow3",
            lambda _: MainWindow3
        )

        monkeypatch.setattr(
            dialogs.WorkflowProgress,
            "show",
            lambda *args, **kwargs: None
        )
        monkeypatch.setattr(
            dialogs.WorkflowProgress,
            "exec",
            lambda *args, **kwargs: None
        )
        startup.run()
        assert startup.on_exit.called is True

    def test_load_json(self, monkeypatch):
        monkeypatch.setattr(
            speedwagon.config,
            "get_whitelisted_plugins",
            lambda: []
        )
        startup = gui_startup.SingleWorkflowJSON(app=None)
        workflow = Mock()
        workflow.name = "Zip Packages"

        workflow_klass = Mock(return_value=workflow)
        monkeypatch.setattr(
            speedwagon.job,
            "available_workflows",
            lambda: {"Zip Packages": workflow_klass}
        )
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


class TestStartQtThreaded:
    @pytest.fixture(scope="function")
    def starter(self, monkeypatch, qtbot):
        monkeypatch.setattr(
            speedwagon.config.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )

        monkeypatch.setattr(
            speedwagon.config.config.pathlib.Path,
            "home",
            lambda *_: pathlib.Path("/usr/home")
        )

        app = Mock()
        config = Mock(
            spec_set=speedwagon.config.AbsConfigSettings,
            application_settings=Mock(return_value={"GLOBAL": {}})
        )
        startup = gui_startup.StartQtThreaded(app=app, config=config)
        class SettingsFileLocatorDummy(
            speedwagon.config.config.AbsSettingLocator
        ):
            def get_app_data_dir(self):
                return ""

            def get_config_file(self):
                return ""
            def get_tabs_file(self):
                return ""
            def get_user_data_dir(self):
                return ""
        # startup.config_loader_strategy = SettingsFileLocatorDummy()
        def read_settings_file_plugins(*args, **kwargs):
            return {}
        # monkeypatch.setattr(
        #     speedwagon.config,
        #     "ConfigLoader",
        #     Mock(name="ConfigLoader", read_settings_file_plugins=read_settings_file_plugins)
        # )
        yield startup
        if startup.windows is not None:
            startup.windows.close()
        startup.app.closeAllWindows()
        startup.app.quit()
        # print(startup)

    def test_save_workflow_config(self, qtbot, starter, monkeypatch):
        dialog = Mock()
        parent = QtWidgets.QWidget()
        dialog.getSaveFileName = MagicMock(return_value=("make_jp2.json", ""))
        monkeypatch.setattr(QtWidgets.QMessageBox, "exec", Mock(name="exec"))
        serialization_strategy = Mock()
        spam_file_select = FileSelectData(label="spam")
        spam_file_select.value = "Spam.txt"
        save_workflow_config(
            workflow_name="Spam",
            data={"dummy": spam_file_select},
            parent=parent,
            dialog_box=dialog,
            serialization_strategy=serialization_strategy
        )
        assert serialization_strategy.save.called is True
        serialization_strategy.save.assert_called_with("Spam", {'dummy': 'Spam.txt'})

    def test_save_workflow_cancel(self, qtbot, starter):
        dialog = Mock()
        parent = QtWidgets.QWidget()
        dialog.getSaveFileName = MagicMock(return_value=(None, ""))

        serialization_strategy = Mock(spec_set=speedwagon.job.AbsJobConfigSerializationStrategy)
        serialization_strategy.save = Mock(side_effect=Exception("Should not be run"))
        save_workflow_config(
            workflow_name="Spam",
            data={},
            parent=parent,
            dialog_box=dialog,
            serialization_strategy=serialization_strategy
        )
        assert serialization_strategy.save.called is False

    def test_save_workflow_config_os_error(self, qtbot, starter, monkeypatch):
        dialog = Mock()
        parent = QtWidgets.QWidget()

        dialog.getSaveFileName = MagicMock(return_value=("make_jp2.json", ""))
        attempts_to_save = 0

        def save(*_, **__):
            nonlocal attempts_to_save
            if attempts_to_save == 0:
                attempts_to_save += 1
                raise OSError("Read only file system")

        serialization_strategy = Mock(save=save)

        q_message_box_exec = Mock()
        monkeypatch.setattr(QtWidgets.QMessageBox, "exec", q_message_box_exec)
        save_workflow_config(
            workflow_name="Spam",
            data={},
            parent=parent,
            dialog_box=dialog,
            serialization_strategy=serialization_strategy
        )
        assert q_message_box_exec.called is True

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

    def test_load_workflow_config_cancel(self, qtbot, starter):
        dialog = Mock()
        dialog.getOpenFileName = MagicMock(return_value=("", ""))

        serialization_strategy = MagicMock()
        serialization_strategy.load = Mock(return_value=("name", {}))
        starter.import_workflow_config(
            parent=Mock(),
            dialog_box=dialog,
            serialization_strategy=serialization_strategy
        )
        assert serialization_strategy.load.called is False

    def test_load_workflows_no_window(self, starter, monkeypatch):
        load_custom_tabs = Mock()
        starter.windows = None
        monkeypatch.setattr(starter, "load_custom_tabs", load_custom_tabs)
        starter.load_workflows()
        assert load_custom_tabs.called is False

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
        with patch(
                'speedwagon.frontend.qtwidgets.gui_startup',
                mock_open()
        ) as w:
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
        with patch(
                'speedwagon.frontend.qtwidgets.gui_startup.open',
                mock_open()
        ) as mock:
            mock.side_effect = side_effect_for_saving
            starter.save_log(None)

        assert QMessageBox.called is True

    @pytest.mark.parametrize("signal_name, expected_action_called", [
        ("action_system_info_requested", "open_system_info_dialog"),
        ("action_open_application_preferences", "open_settings_dialog"),
        ("action_help_requested", "open_help"),
        ("action_open_application_preferences", "open_settings_dialog"),
    ])
    def test_actions(self, starter, qtbot, signal_name, expected_action_called):
        actions = Mock(spec_set=gui_startup.MainWindowBuilder.WindowActions)
        main_window = starter.build_main_window(Mock(name="job_manager"), actions=actions)
        qtbot.addWidget(main_window)
        getattr(main_window, signal_name).trigger()
        getattr(actions, expected_action_called).assert_called_once()

    def test_run_opens_window(self, qtbot, monkeypatch, starter):

        main_window3 = speedwagon.frontend.qtwidgets.gui.MainWindow3()
        main_window3.show = Mock()
        main_window3.session_config = Mock()
        main_window3.update_settings = Mock()
        # main_window3.console = Mock()
        MainWindow3 = Mock(
            name="MainWindow3",
            return_value=main_window3,
        )
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.gui,
            "MainWindow3",
            MainWindow3
        )
        monkeypatch.setattr(
            speedwagon.config.config.ConfigFileSetter,
            "update", Mock()
        )
        starter.load_custom_tabs = Mock()
        starter.load_all_workflows_tab = Mock()
        workflow = Mock(
            name="workflow instance",
            workflow_options=Mock(return_value=[])
        )
        workflow.name = "Zip Packages"

        workflow_klass = Mock(return_value=workflow)
        monkeypatch.setattr(
            speedwagon.job,
            "available_workflows",
            lambda *_, **__: {"Zip Packages": workflow_klass}
        )
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            'get_tabs_file',
            lambda *_: 'dummy.yml'
        )
        starter.run()
        assert main_window3.show.called is True

    def test_load_custom_tabs(self, qtbot, monkeypatch, starter):
        tabs_file = "somefile.yml"

        loaded_workflows = Mock()

        monkeypatch.setattr(
            os.path,
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

    def test_load_help_web_page_no_url_found(
            self,
            qtbot,
            monkeypatch,
            caplog,
    ):
        monkeypatch.setattr(gui_startup, "get_help_url", lambda: None)
        gui_startup.load_help_web_page()
        assert any("No help link available" in m for m in caplog.messages)

    def test_load_help_web_page_no_package_info(
            self,
            qtbot,
            monkeypatch,
            caplog,
    ):
        monkeypatch.setattr(
            gui_startup,
            "get_help_url",
            Mock(
                side_effect=importlib_metadata.PackageNotFoundError(
                    'speedwagon'
                )
            )
        )
        gui_startup.load_help_web_page()
        assert any("No help link available" in m for m in caplog.messages)

    def test_load_help_web_page(
            self,
            qtbot,
            monkeypatch,
            caplog,
    ):
        open_new = Mock(name="open_new")
        monkeypatch.setattr(webbrowser, "open_new", open_new)
        monkeypatch.setattr(gui_startup, "get_help_url", Mock(return_value="www.example.com"))
        gui_startup.load_help_web_page()
        open_new.assert_called_once()

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
        monkeypatch.setattr(gui_startup, "report_exception_dialog", Mock())
        # starter.report_exception_dialog = Mock()

        # Simulate no valid workflow
        monkeypatch.setattr(
            speedwagon.job, "available_workflows", lambda: {}
        )

        starter.submit_job(
            job_manager,
            workflow_name,
            options,
            main_app,
        )
        assert gui_startup.report_exception_dialog.called is True

    def test_submit_job_submits_to_job_manager(
            self,
            qtbot,
            monkeypatch,
            starter
    ):
        monkeypatch.setattr(
            speedwagon.config.config.pathlib.Path, "home", lambda: "my_home"
        )
        monkeypatch.setattr(
            speedwagon.config.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )

        job_manager = Mock()
        workflow_name = "spam"
        options = {}
        spam_workflow = Mock()

        monkeypatch.setattr(
            speedwagon.job,
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

    def test_initialize(self, qtbot, monkeypatch):
        start = gui_startup.StartQtThreaded(app=Mock())
        get_startup_tasks = Mock(name="get_startup_tasks", return_value=[])
        monkeypatch.setattr(
            gui_startup,
            "get_startup_tasks",
            get_startup_tasks
        )
        start.initialize()
        get_startup_tasks.assert_called_once()

    def test_load_all_workflows_tab(self, qtbot):
        start = gui_startup.StartQtThreaded(app=Mock())
        main_window = Mock('MainWindow3', add_tab=Mock())
        loaded_workflows = {}
        start.load_all_workflows_tab(main_window, loaded_workflows)

        # Flushing because qt quits before the logging qt signals are
        # propagated to the log widget. This should be fixed but for now,
        # it's managed here in the tests
        for handler in start.logger.handlers:
            handler.flush()

        main_window.add_tab.assert_called_with("All", {})

    def test_set_application_name(self, qtbot):
        start = gui_startup.StartQtThreaded(app=Mock())
        start.set_application_name("new app")
        main_window = MainWindow3()
        start.load_workflows = Mock()
        qtbot.addWidget(main_window)
        main_window.show = Mock()
        main_window.update_settings = Mock()
        start.build_main_window = lambda *_: main_window
        start.config = Mock()
        start.start_gui(Mock())
        assert main_window.windowTitle() == "new app"

    def test_request_settings(self, starter):
        settings_builder_strategy = Mock(name="dialog_builder_strategy")
        starter.request_settings(dialog_builder_strategy=settings_builder_strategy)
        settings_builder_strategy.assert_called_once()


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

    def test_cli(self, monkeypatch, mocker):
        f = io.StringIO('{"Workflow":"dummy", "Configuration": {}}')
        args = argparse.Namespace(json=f)
        monkeypatch.setattr(
            speedwagon.job,
            "available_workflows",
            lambda: MagicMock()
        )
        run_command = speedwagon.startup.RunCommand(args)

        run_strategy = Mock()
        SingleWorkflowJSON = Mock()
        monkeypatch.setattr(run_command, "get_gui_strategy", Mock(side_effect=ImportError))
        monkeypatch.setattr(run_command, "_run_strategy", run_strategy)
        monkeypatch.setattr(speedwagon.startup, "SingleWorkflowJSON", SingleWorkflowJSON)

        run_command.run()
        assert SingleWorkflowJSON.called is True


def test_start_up_tab_editor(monkeypatch):
    standalone_tab_editor = Mock()

    with monkeypatch.context() as mp:
        mp.setattr(speedwagon.frontend.qtwidgets.gui_startup,
                   "standalone_tab_editor",
                   standalone_tab_editor)

        speedwagon.startup.main(argv=["tab-editor"])
        assert standalone_tab_editor.called is True


class TestResolveSettings:
    def test_get_settings(self, monkeypatch):
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            "get_config_file",
            lambda _ : "dummy.ini"
        )
        monkeypatch.setattr(
            speedwagon.config.IniConfigManager,
            "data",
            lambda _: {}
        )

        resolver = gui_startup.ResolveSettings()
        assert isinstance(resolver.get_settings(), dict)
from pytestqt.qt_compat import qt_api
class CustomQApplication(qt_api.QtWidgets.QApplication):
    def __init__(self, *argv):
        super().__init__(*argv)
        self.custom_attr = "xxx"

    def custom_function(self):
        pass


def test_gui_exceptions_hook(qtbot, monkeypatch):
    monkeypatch.setattr(gui_startup.tb, "print_tb", Mock())
    monkeypatch.setattr(gui_startup, "report_exception_dialog", Mock())
    app = Mock()
    gui_startup.gui_exceptions_hook(
        BaseException,
        Mock(name="BaseException"),
        Mock(name="traceback: Optional[types.TracebackType]"),
        app
    )
    app.exit.assert_called_with(1)


def test_report_exception_dialog(qtbot, monkeypatch):
    monkeypatch.setattr(
        gui_startup.dialog.dialogs.SpeedwagonExceptionDialog,
        "exec",
        Mock(name='exec')
    )
    gui_startup.report_exception_dialog(RuntimeError())
    assert \
        gui_startup.dialog.dialogs.SpeedwagonExceptionDialog.exec.called \
        is True


def test_export_system_info_to_file():
    writer = Mock()
    gui_startup.export_system_info_to_file(
        file="fake.txt",
        file_type="Text (*.txt)",
        writer=writer
    )
    writer.assert_called_once()


def test_get_help_url(monkeypatch):
    pkg_metadata = Mock(
        get_all=Mock(
            return_value=["project, https://www.fake.com"]
        )
    )
    monkeypatch.setattr(
        gui_startup.metadata, "metadata",
        Mock(
            spec_set=importlib_metadata.PackageMetadata,
            return_value=pkg_metadata
        )
    )
    assert gui_startup.get_help_url() == "https://www.fake.com"


def test_get_help_url_nothing_on_missing(monkeypatch):
    pkg_metadata = Mock(
        get_all=Mock(return_value=[])
    )
    monkeypatch.setattr(
        gui_startup.metadata, "metadata",
        Mock(
            spec_set=importlib_metadata.PackageMetadata,
            return_value=pkg_metadata
        )
    )
    assert gui_startup.get_help_url() is None


def test_get_help_url_malformed_data(monkeypatch):
    pkg_metadata = Mock(
        get_all=Mock(
            return_value=["bad data"]
        )
    )
    monkeypatch.setattr(
        gui_startup.metadata, "metadata",
        Mock(
            spec_set=importlib_metadata.PackageMetadata,
            return_value=pkg_metadata
        )
    )
    with pytest.raises(ValueError) as error:
        gui_startup.get_help_url()
    assert "malformed" in str(error)

def test_get_active_workflows():
    config_file = "dummy.ini"
    workflow_finder = Mock(
        name='finder',
        spec_set=AbsWorkflowFinder,
        locate=Mock(
            return_value={
                "spam": Mock(name="spam workflow")
            }
        )
    )
    assert "spam" in gui_startup.get_active_workflows(config_file, workflow_finder=workflow_finder)

class TestResolveSettingsStrategyConfigAdapter:
    @pytest.fixture()
    def mock_source_application_settings(self):
        return Mock(spec_set=gui_startup.AbsResolveSettingsStrategy)

    @pytest.fixture()
    def mocked_workflow_backend(self):
        return Mock()

    @pytest.fixture()
    def adapter(self, mock_source_application_settings, mocked_workflow_backend):
        return gui_startup.ResolveSettingsStrategyConfigAdapter(
            mock_source_application_settings,
            mocked_workflow_backend
        )

    def test_application_settings(
        self,
        adapter,
        mock_source_application_settings
    ):
        adapter.application_settings()
        mock_source_application_settings.get_settings.assert_called_once()

    def test_workflow_settings(self, adapter, mocked_workflow_backend):
        workflow = Mock()
        adapter.workflow_settings(workflow)
        mocked_workflow_backend.assert_called_once_with(workflow)


def test_build_request_settings_dialog2(qtbot, monkeypatch):
    def exists(path):
        return path in ["somedir", "someconfig.ini"]
    monkeypatch.setattr(
        speedwagon.frontend.qtwidgets.dialog.settings.os.path,
        "exists",
        exists
    )

    def build_setting_qt_model(config_file):
        my_model = speedwagon.frontend.qtwidgets.models.settings.SettingsModel()
        my_model.add_setting('starting-tab', "all")
        return my_model

    monkeypatch.setattr(
        speedwagon.frontend.qtwidgets.dialog.settings,
        "build_setting_qt_model",
        build_setting_qt_model
    )
    monkeypatch.setattr(
        speedwagon.config.plugins,
        "read_settings_file_plugins",
        Mock(
            name="read_settings_file_plugins",
            return_value={"myplugin": {
                "one": True
            }}
        )
    )
    def entry_points(*args, **kwargs):
        entry_point_1 = Mock(module='myplugin')
        entry_point_1.name = "one"
        return [
            entry_point_1
        ]
    monkeypatch.setattr(importlib_metadata, "entry_points", entry_points)

    def get_active_workflows(config_file, workflow_finder=None):
        return {}
    monkeypatch.setattr(gui_startup, "get_active_workflows", get_active_workflows)
    initialize_workflows = Mock(name="initialize_workflows", return_value=[])
    monkeypatch.setattr(speedwagon.workflow, "initialize_workflows", initialize_workflows)
    monkeypatch.setattr(
        speedwagon.config.tabs.CustomTabsYamlConfig,
        "data",
        Mock(name="data", return_value=[])
    )
    config_locations = Mock(
        name="config_locations",
        spec_set=speedwagon.config.config.AbsSettingLocator,
        get_app_data_dir=Mock(return_value="somedir"),
        get_config_file=Mock(return_value="someconfig.ini"),
        get_tabs_file=Mock(return_value="sometabs.yml"),
    )
    on_success_save_updated_settings = Mock(name="on_success_save_updated_settings")

    dialog_box = gui_startup.build_request_settings_dialog(
        config_locations,
        on_success_save_updated_settings
    )

    with qtbot.waitSignal(dialog_box.finished):
        dialog_box.tabs_widget.setCurrentIndex(3)
        plugin_tab = dialog_box.tabs_widget.currentWidget()
        assert "myplugin" in plugin_tab.plugins_activation.enabled_plugins()
        qtbot.mousePress(
            plugin_tab.plugins_activation.plugin_list_view.viewport(),
            QtCore.Qt.LeftButton,
            pos=plugin_tab.plugins_activation.plugin_list_view.visualRect(
                plugin_tab.plugins_activation.model.index(0,0)
            ).center()
        )
        qtbot.keyPress(
            plugin_tab.plugins_activation.plugin_list_view.viewport(),
            QtCore.Qt.Key_Space
        )
        dialog_box.button_box.button(dialog_box.button_box.StandardButton.Ok).click()
    on_success_save_updated_settings.assert_called_once()

class TestLocalSettingsBuilder2:
    def test_tabs_start_with_zero(self):
        builder = gui_startup.LocalSettingsBuilder()
        assert len(builder.tabs) == 0

    def test_add_tab(self):
        builder = gui_startup.LocalSettingsBuilder()
        def _setup_config_tab():
            tabs_config = dialog.settings.TabsConfigurationTab()
            return tabs_config
        builder.add_tab(
            "Tabs",
            _setup_config_tab,

        )
        assert len(builder.tabs) == 1

    @pytest.fixture()
    def setup_config_tab_func(self):
        def _setup_config_tab():
            tabs_config = speedwagon.frontend.qtwidgets.dialog.settings.TabsConfigurationTab()
            tab_manager = Mock(
                name="tab_manager",
                spec_set=speedwagon.config.AbsTabsConfigDataManagement,
                data=Mock(return_value=[
                    speedwagon.config.tabs.CustomTabData("dummy", [])
                ])
            )
            model_loader = tab_models.TabDataModelConfigLoader(
                tabs_manager=tab_manager,
            )
            model_loader.get_all_active_workflows_strategy = lambda :{
                "Spam": type(
                    "SpamWorkflow",
                    (speedwagon.Workflow,),
                    {"name": "Spam"}
                )
            }
            tabs_config.load_tab_data_model_strategy = model_loader
            tabs_config.editor.load_data()
            return tabs_config
        return _setup_config_tab
    def test_build(self, qtbot, setup_config_tab_func):
        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        builder = gui_startup.LocalSettingsBuilder()

        save_tabs_function = Mock(name="save_tabs_function")
        builder.add_tab(
            "Tabs",
            setup_config_tab_func,
            save_data_func=save_tabs_function
        )
        dialog_box = builder.build(parent=parent)
        with qtbot.waitSignal(dialog_box.accepted):
            widget = dialog_box.tabs_widget.currentWidget()
            # Make a change in the settings
            qtbot.mousePress(
                widget.editor.all_workflows_list_view.viewport(),
                QtCore.Qt.LeftButton,
                pos=widget.editor.all_workflows_list_view.visualRect(
                    widget.editor.all_workflows_list_view.model().index(0,0)
                ).center()
            )
            widget.editor.add_items_button.click()
            dialog_box.button_box.button(dialog_box.button_box.StandardButton.Ok).click()
        save_tabs_function.assert_called_once_with([
                speedwagon.config.tabs.CustomTabData(tab_name="dummy", workflow_names=["Spam"])
            ]
        )

    def test_build2(self, qtbot, setup_config_tab_func):
        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        builder = gui_startup.LocalSettingsBuilder()

        save_tabs_function = Mock(name="save_tabs_function")
        builder.add_tab(
            "Tab config",
            setup_config_tab_func,
            save_data_func=save_tabs_function
        )

        builder.add_tab(
            "Global Settings",
            speedwagon.frontend.qtwidgets.dialog.settings.GlobalSettingsTab,
            save_data_func=Mock()
        )
        dialog_box: speedwagon.frontend.qtwidgets.dialog.settings.SettingsDialog = builder.build(parent=parent)
        with qtbot.waitSignal(dialog_box.accepted):
            dialog_box.tabs_widget.setCurrentIndex(0)
            widget = dialog_box.tabs_widget.currentWidget()
            # Make a change in the settings
            qtbot.mousePress(
                widget.editor.all_workflows_list_view.viewport(),
                QtCore.Qt.LeftButton,
                pos=widget.editor.all_workflows_list_view.visualRect(
                    widget.editor.all_workflows_list_view.model().index(0,0)
                ).center()
            )
            widget.editor.add_items_button.click()
            dialog_box.button_box.button(dialog_box.button_box.StandardButton.Ok).click()

        save_tabs_function.assert_called_once_with([
                speedwagon.config.tabs.CustomTabData(tab_name="dummy", workflow_names=["Spam"])
            ]
        )
def test_get_startup_tasks_includes_global_config_file_task():
    config_backend = Mock()
    config_file_locations = Mock()
    logger = Mock()
    tasks = gui_startup.get_startup_tasks(
        config_backend,
        config_file_locations,
        logger
    )
    assert any([isinstance(a, system_tasks.EnsureGlobalConfigFiles) for a in tasks])