from collections import OrderedDict
from unittest import mock
from unittest.mock import Mock, MagicMock, patch, call
import yaml
import pytest
import speedwagon.exceptions
import speedwagon.job
from speedwagon.frontend.qtwidgets import tabs
from speedwagon.frontend.qtwidgets.runners import QtRunner

QtCore = pytest.importorskip("PySide6.QtCore")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")


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
                list(tabs.read_tabs_yaml('tabs.yml')
                )
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
