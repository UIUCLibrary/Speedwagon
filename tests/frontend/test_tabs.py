from collections import OrderedDict
from typing import List, Any, Dict
from unittest import mock
from unittest.mock import Mock, MagicMock, patch, call
import yaml
import pytest

import speedwagon.exceptions
import speedwagon.job

QtCore = pytest.importorskip("PySide6.QtCore")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from speedwagon.frontend.qtwidgets import tabs
from speedwagon.frontend.qtwidgets.runners import QtRunner
from speedwagon import worker
from speedwagon.workflow import DirectorySelect


class TestWorkflowsTab:
    def test_exception_calls_message_box(self, qtbot, monkeypatch):
        mock_log_manager = Mock()
        workflows = MagicMock()

        selection_tab = tabs.WorkflowsTab(
            None,
            workflows=workflows,
            log_manager=mock_log_manager
        )
        selection_tab.get_item_options_model = \
            Mock(
                side_effect=speedwagon.exceptions.SpeedwagonException(
                    "something wrong happened")
            )
        index = Mock()
        selection_tab.item_selection_model = Mock()

        mock_message_box_exec = MagicMock()

        monkeypatch.setattr(
            QtWidgets.QMessageBox,
            "exec",
            mock_message_box_exec
        )

        with pytest.raises(speedwagon.exceptions.SpeedwagonException) as e:
            selection_tab.item_selected(index)
        assert str(e.value) == "something wrong happened" and \
               mock_message_box_exec.called is True

    @pytest.mark.parametrize(
        "number_of_indexes_selected, is_validate",
        [
            (0, False),
            (1, True),
            (2, False),
        ]
    )
    def test_is_ready_to_start(
            self,
            qtbot,
            number_of_indexes_selected,
            is_validate
    ):
        log_manager = Mock()
        work_manager = Mock()
        selection_tab = tabs.WorkflowsTab(
            parent=None,
            workflows=MagicMock(),
            log_manager=log_manager,
            work_manager=work_manager
        )
        selection_tab.item_selector_view.selectedIndexes = \
            Mock(
                return_value=[
                    Mock() for _ in range(number_of_indexes_selected)
                ]
            )
        assert selection_tab.is_ready_to_start() is is_validate

    def test_init_selects_first_workflow(self, qtbot):
        log_manager = Mock()
        work_manager = Mock(user_settings={})
        workflows = OrderedDict()
        workflows["Spam"] = MagicMock()
        workflows["Bacon"] = MagicMock()

        base_widget = QtWidgets.QWidget()
        selection_tab = tabs.WorkflowsTab(
            parent=base_widget,
            workflows=workflows,
            log_manager=log_manager,
            work_manager=work_manager
        )
        selection_tab.init_selection()
        assert selection_tab.item_selector_view.currentIndex().data() == \
               workflows['Spam'].name

    def test_start_calls_run_on_workflow(self, qtbot, monkeypatch):
        log_manager = Mock()
        work_manager = MagicMock(user_settings={})
        workflows = OrderedDict()

        class MockWorkflow(speedwagon.job.AbsWorkflow):
            name = "Spam"

            def discover_task_metadata(
                    self, initial_results, additional_data, **user_args):
                pass

            def get_user_options(self):
                return []

            def user_options(self):
                return []

        workflows["Spam"] = MockWorkflow

        selection_tab = tabs.WorkflowsTab(
            parent=None,
            workflows=workflows,
            log_manager=log_manager,
            work_manager=work_manager
        )
        from speedwagon.runner_strategies import RunRunner
        mock_runner = Mock()
        monkeypatch.setattr(RunRunner, "run", mock_runner)
        selection_tab.start(workflows["Spam"])
        assert isinstance(mock_runner.call_args_list[0][0][0], MockWorkflow)

    @pytest.mark.parametrize(
        "exception_type",
        [
            ValueError,
            Exception
        ]
    )
    def test_start_creates_a_messagebox_on_value_error(
            self, qtbot, monkeypatch, exception_type):
        work_manager = MagicMock(user_settings={})
        workflows = OrderedDict()

        class MockWorkflow(tabs.AbsWorkflow):
            def discover_task_metadata(
                    self,
                    initial_results,
                    additional_data,
                    **user_args):
                pass

            def get_user_options(self):
                return []

            def user_options(self):
                return []

        workflows["Spam"] = MockWorkflow

        selection_tab = tabs.WorkflowsTab(
            parent=None,
            workflows=workflows,
            work_manager=work_manager
        )

        from speedwagon.runner_strategies import RunRunner

        mock_runner = Mock(
            side_effect=exception_type("something went wrong")
        )

        monkeypatch.setattr(RunRunner, "run", mock_runner)
        mock_message_box_exec = Mock()

        monkeypatch.setattr(
            tabs.WorkflowsTab,
            "_create_error_message_box_from_exception",
            mock_message_box_exec
        )

        selection_tab.start(workflows["Spam"])

        assert mock_message_box_exec.called is True

    @pytest.mark.parametrize("exception_type", [
        speedwagon.exceptions.JobCancelled,
        ValueError,
        TypeError
    ])
    def test_run_dialog_catch_exception(
            self, qtbot, monkeypatch, exception_type):
        workflows = {
            "spam": MagicMock(name="spam")
        }
        workflows['spam'].__class__ = speedwagon.job.AbsWorkflow
        workflows['spam'].name = "Spam"

        log_manager = Mock()
        work_manager = Mock()
        work_manager.user_settings = {}

        def cause_chaos(self, tools, options, logger, completion_callback):
            raise exception_type

        monkeypatch.setattr(QtRunner, "run", cause_chaos)

        exec_ = Mock()

        monkeypatch.setattr(tabs.QtWidgets.QMessageBox, "exec_", exec_)

        selection_tab = tabs.WorkflowsTab(
            parent=None,
            workflows=workflows,
            log_manager=log_manager,
            work_manager=work_manager
        )
        selection_tab.run(workflows['spam'], {})
        assert exec_.called is True

    @pytest.fixture()
    def dummy_workflow_cls_factory(self):
        def _make_workflow(user_options):
            class DummyWorkflow(tabs.Workflow):

                def discover_task_metadata(self, initial_results: List[Any],
                                           additional_data: Dict[str, Any],
                                           **user_args) -> List[dict]:
                    return []

                def get_user_options(self):
                    return user_options
            return DummyWorkflow
        return _make_workflow

    @pytest.fixture()
    def workflow_tab_factory(self, dummy_workflow_cls_factory):
        def _make_workflow_tab(user_options):

            base_widget = QtWidgets.QWidget()
            workflows = {'dummy': dummy_workflow_cls_factory(user_options)}
            log_manager = Mock()
            work_manager = Mock(worker.ToolJobManager, user_settings={})
            selection_tab = tabs.WorkflowsTab(
                parent=base_widget,
                workflows=workflows,
                log_manager=log_manager,
                work_manager=work_manager
            )
            return selection_tab
        return _make_workflow_tab

    @pytest.mark.parametrize(
        "user_options,raises",
        [
            (
                [
                    DirectorySelect("Input", required=True),
                ],
                True
            ),
            (
                [
                    DirectorySelect("Input", required=False),
                    DirectorySelect("Output", required=True),
                ],
                True
            ),
            (
                [
                    DirectorySelect("Input", required=True),
                    DirectorySelect("Output", required=True),
                ],
                True
            ),
            (
                [
                    DirectorySelect("Output", required=False),
                ],
                False
            ),
            (
                [
                    DirectorySelect("Input", required=False),
                    DirectorySelect("Output", required=False),
                ],
                False
            )
        ]
    )
    def test_warn_user_of_invalid_settings(
            self,
            qtbot,
            monkeypatch,
            workflow_tab_factory,
            user_options,
            raises
    ):

        error_message_box = Mock()
        monkeypatch.setattr(
            tabs.QtWidgets, "QMessageBox", Mock(return_value=error_message_box)
        )
        workflow_tab = workflow_tab_factory(user_options)

        def checker(data):
            return "I failed" if data.required else None

        if raises:
            with pytest.raises(speedwagon.exceptions.InvalidConfiguration):
                workflow_tab.warn_user_of_invalid_settings([checker])
            assert error_message_box.exec_.called is True
        else:
            assert workflow_tab.warn_user_of_invalid_settings([checker]) is None

    def test_warn_user_of_invalid_settings_workflow(self, qtbot, workflow_tab_factory, monkeypatch):

        value_widget = DirectorySelect("Input", required=True)
        value_widget.value = "some value"

        workflow_tab = workflow_tab_factory([value_widget])
        workflow = Mock(speedwagon.job.Workflow)

        monkeypatch.setattr(
            tabs,
            'get_workflow_errors',
            Mock(return_value="got some errors")
        )

        monkeypatch.setattr(tabs.QtWidgets.QMessageBox, 'exec_', Mock())

        with pytest.raises(speedwagon.exceptions.InvalidConfiguration):
            workflow_tab.warn_user_of_invalid_settings(checks=[], workflow=workflow)

    def test_start_with_errors_does_not_start(
            self,
            qtbot,
            workflow_tab_factory
    ):
        no_value_widget = DirectorySelect("Input", required=True)
        no_value_widget.value = None

        workflow_tab = workflow_tab_factory([no_value_widget])
        workflow_tab.start = Mock()
        workflow_tab.warn_user_of_invalid_settings = \
            Mock(side_effect=tabs.InvalidConfiguration)
        qtbot.mouseClick(workflow_tab.actions_widgets['start_button'], QtCore.Qt.MouseButton.LeftButton)
        assert workflow_tab.start.called is False

    def test_valid_start_calls_start(
            self,
            qtbot,
            workflow_tab_factory
    ):
        no_value_widget = DirectorySelect("Input", required=True)
        no_value_widget.value = "foo"

        workflow_tab = workflow_tab_factory([no_value_widget])
        workflow_tab.start = Mock()
        workflow_tab.warn_user_of_invalid_settings = Mock()
        qtbot.mouseClick(
            workflow_tab.actions_widgets['start_button'],
            QtCore.Qt.MouseButton.LeftButton
        )
        assert workflow_tab.start.called is True
    def test_invalid_config_starts_open_dialog_box(
            self,
            qtbot,
            workflow_tab_factory,
            monkeypatch
    ):
        no_value_widget = DirectorySelect("Input", required=True)

        workflow_tab = workflow_tab_factory([no_value_widget])
        workflow_tab.is_ready_to_start = Mock(return_value=True)
        workflow_tab.start = Mock(
            side_effect=speedwagon.exceptions.MissingConfiguration("oh no")
        )
        workflow_tab.warn_user_of_invalid_settings = Mock()
        message_box = Mock()
        monkeypatch.setattr(
            tabs.QtWidgets, "QMessageBox", Mock(return_value=message_box)
        )
        qtbot.mouseClick(
            workflow_tab.actions_widgets['start_button'],
            QtCore.Qt.MouseButton.LeftButton
        )
        message_box.setWindowTitle.assert_called_with("Settings Error")

class TestTabsYaml:
    @pytest.mark.parametrize("exception_type", [
        FileNotFoundError,
        AttributeError,
        yaml.YAMLError,
    ])
    def test_read_tabs_yaml_errors(self, monkeypatch, exception_type):
        import os.path
        with patch(
                'speedwagon.frontend.qtwidgets.tabs.open',
                mock.mock_open()
        ):
            monkeypatch.setattr(os.path, "getsize", lambda x: 1)
            monkeypatch.setattr(yaml, "load", Mock(side_effect=exception_type))
            with pytest.raises(exception_type) as e:
                list(tabs.read_tabs_yaml('tabs.yml'))
            assert e.type == exception_type

    def test_read_tabs_yaml(self, monkeypatch):
        sample_text = """my stuff:
- Convert CaptureOne Preservation TIFF to Digital Library Access JP2
- Convert CaptureOne TIFF to Digital Library Compound Object
- Convert CaptureOne TIFF to Digital Library Compound Object and HathiTrust
- Convert CaptureOne TIFF to Hathi TIFF package
        """
        import os
        monkeypatch.setattr(os.path, 'getsize', lambda x: 1)
        with patch('speedwagon.frontend.qtwidgets.tabs.open',
                   mock.mock_open(read_data=sample_text)):
            tab_data = list(tabs.read_tabs_yaml('tabs.yml'))
            assert len(tab_data) == 1 and \
                   len(tab_data[0][1].workflows) == 4

    def test_write_tabs_yaml(self):
        sample_tab_data = [tabs.TabData("dummy_tab", MagicMock())]
        with patch(
                'speedwagon.frontend.qtwidgets.tabs.open',
                mock.mock_open()
        ) as m:
            tabs.write_tabs_yaml("tabs.yml", sample_tab_data)
            assert m.called is True
        handle = m()
        handle.write.assert_has_calls([call('dummy_tab')])


def test_get_workflow_errors_returns_none_if_found_nothing():
    workflow = Mock()
    options = {"someoption": "somevalue"}
    assert tabs.get_workflow_errors(options, workflow) is None


def test_get_workflow_errors_returns_string_if_found_something():
    workflow = Mock(
        validate_user_options=Mock(side_effect=ValueError('something wrong'))
    )

    options = {"someoption": "some invalid value"}

    assert tabs.get_workflow_errors(options, workflow) == "something wrong"
