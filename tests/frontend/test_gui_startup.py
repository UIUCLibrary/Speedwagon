import argparse
import json
import logging
import os
import pathlib

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open, ANY, call
import io

try:  # pragma: no cover
    from importlib.metadata import PackageMetadata
except ImportError:  # pragma: no cover
    from importlib_metadata import PackageMetadata  # type: ignore

from speedwagon.workflow import FileSelectData
import speedwagon.config
gui_startup = pytest.importorskip("speedwagon.frontend.qtwidgets.gui_startup")

from PySide6 import QtWidgets, QtCore, QtGui
from speedwagon.frontend.qtwidgets.dialog import dialogs
from speedwagon.frontend.qtwidgets.dialog.settings import SettingsDialog, TabEditor
from speedwagon.frontend.qtwidgets.models.tabs import AbsLoadTabDataModelStrategy
from speedwagon.frontend.qtwidgets.gui_startup import save_workflow_config, TabsEditorApp
from speedwagon.frontend.qtwidgets.models import tabs as tab_models
from speedwagon.config import StandardConfigFileLocator
import speedwagon.workflows.builtin

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
        startup = gui_startup.StartQtThreaded(app)
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
        monkeypatch.setattr(SettingsDialog, "exec", exec_)
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
        def load(_, model):
            data = {"All": []}
            for tab_name, workflows in data.items():
                model.append_workflow_tab(tab_name, workflows)
        monkeypatch.setattr(
            tab_models.TabDataModelConfigLoader,
            "load",
            load
        )

        monkeypatch.setattr(
            speedwagon.config.config.pathlib.Path,
            "home",
            lambda *_: pathlib.Path("/usr/home")
        )

        monkeypatch.setattr(
            speedwagon.config.config.WindowsConfig,
            "get_app_data_directory",
            lambda *_: "app_data_dir"
        )

        start = gui_startup.StartQtThreaded(Mock())
        workflow = Mock(
            name="workflow instance",
            workflow_options=Mock(return_value=[])
        )
        workflow.name = "Zip Packages"

        workflow_klass = Mock(return_value=workflow)
        monkeypatch.setattr(
            speedwagon.job,
            "available_workflows",
            lambda: {"Zip Packages": workflow_klass}
        )
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            'get_tabs_file',
            lambda *_: 'dummy.yml'
        )
        start.request_settings()
        assert exec_.called is True

    def test_run_opens_window(self, qtbot, monkeypatch, starter):

        main_window3 = speedwagon.frontend.qtwidgets.gui.MainWindow3()
        main_window3.show = Mock()
        main_window3.config_strategy = Mock()
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
            lambda: {"Zip Packages": workflow_klass}
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

    def test_load_help_no_package_info(
            self,
            qtbot,
            monkeypatch,
            caplog,
            starter
    ):
        main_window3 = speedwagon.frontend.qtwidgets.gui.MainWindow3()
        main_window3.show = Mock()
        main_window3.config_strategy = Mock()
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
            lambda: {"Zip Packages": workflow_klass}
        )
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            'get_tabs_file',
            lambda *_: 'dummy.yml'
        )
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
        starter.windows.action_help_requested.triggered.emit()
        assert any("No help link available" in m for m in caplog.messages)

    def test_load_help(self, qtbot, monkeypatch, starter):
        main_window3 = speedwagon.frontend.qtwidgets.gui.MainWindow3()
        main_window3.show = Mock()
        main_window3.config_strategy = Mock()
        MainWindow3 = Mock(
            name="MainWindow3",
            return_value=main_window3,
        )
        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.gui,
            "MainWindow3",
            MainWindow3
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
            lambda: {"Zip Packages": workflow_klass}
        )
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            'get_tabs_file',
            lambda *_: 'dummy.yml'
        )
        starter.run()
        open_new = Mock()

        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.gui_startup,
            "get_help_url",
            lambda: "https://www.fake.com"
        )

        monkeypatch.setattr(
            speedwagon.frontend.qtwidgets.gui_startup.webbrowser,
            "open_new",
            open_new
        )

        qtbot.addWidget(starter.windows)
        starter.windows.action_help_requested.triggered.emit()
        assert open_new.called is True

    def test_resolve_settings_calls_get_settings(
            self,
            qtbot,
            monkeypatch,
            starter
    ):
        starter.load_custom_tabs = Mock()
        starter.load_all_workflows_tab = Mock()

        main_window3 = speedwagon.frontend.qtwidgets.gui.MainWindow3()
        main_window3.show = Mock()
        main_window3.config_strategy = Mock()
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
            starter.settings_resolver,
            "get_settings",
            Mock(
                name="get_settings",
                return_value={}
            )
        )
        starter.resolve_settings()
        assert starter.settings_resolver.get_settings.called is True

    # def test_read_settings_file(self, qtbot, monkeypatch, starter):
    #     read = Mock()
    #
    #     monkeypatch.setattr(
    #         speedwagon.config.configparser.ConfigParser,
    #         "read",
    #         read
    #     )
    #
    #     starter.read_settings_file("somefile")
    #     read.assert_called_with("somefile")

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
        start = gui_startup.StartQtThreaded(Mock())
        speedwagon.config.config.ensure_settings_files = Mock(name="ensure_settings_files")
        start.resolve_settings = Mock(name="resolve_settings")
        monkeypatch.setattr(
            speedwagon.config.WorkflowSettingsYamlExporter,
            "write_data_to_file",
            Mock()
        )
        monkeypatch.setattr(
            StandardConfigFileLocator,
            "get_config_file",
            lambda _ : "dummy.ini"
        )
        monkeypatch.setattr(
            speedwagon.workflows.builtin,
            "EnsureBuiltinWorkflowConfigFiles",
            Mock(speedwagon.workflows.builtin.AbsSystemTask)
        )
        start.initialize()

        expected = {
            "ensure_settings_files was called": True,
            "resolve_settings was called": True,
        }
        actual = {
            "ensure_settings_files was called":
                speedwagon.config.config.ensure_settings_files.called,
            "resolve_settings was called": start.resolve_settings.called,
        }
        assert actual == expected

    def test_load_all_workflows_tab(self, qtbot):
        start = gui_startup.StartQtThreaded(Mock())
        main_window = Mock('MainWindow3', add_tab=Mock())
        loaded_workflows = {}
        start.load_all_workflows_tab(main_window, loaded_workflows)

        # Flushing because qt quits before the logging qt signals are
        # propagated to the log widget. This should be fixed but for now,
        # it's managed here in the tests
        for handler in start.logger.handlers:
            handler.flush()

        main_window.add_tab.assert_called_with("All", {})

    def test_ensure_settings_files(self, qtbot, monkeypatch):
        start = gui_startup.StartQtThreaded(Mock())
        monkeypatch.setattr(
            speedwagon.config.config,
            "ensure_settings_files",
            Mock(name="ensure_settings_files")
        )
        start.ensure_settings_files()
        assert speedwagon.config.config.ensure_settings_files.called is True


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
            spec_set=PackageMetadata,
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
            spec_set=PackageMetadata,
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
            spec_set=PackageMetadata,
            return_value=pkg_metadata
        )
    )
    with pytest.raises(ValueError) as error:
        gui_startup.get_help_url()
    assert "malformed" in str(error)
