from collections import OrderedDict
from unittest.mock import Mock, MagicMock

import pytest

from speedwagon import tabs, exceptions, job


class TestWorkflowsTab:
    def test_exception_calls_message_box(self, qtbot, monkeypatch):
        from PyQt5 import QtWidgets
        mock_log_manager = Mock()
        workflows = MagicMock()

        selection_tab = tabs.WorkflowsTab(
            None, workflows=workflows, log_manager=mock_log_manager
        )
        selection_tab.get_item_options_model = \
            Mock(
                side_effect=exceptions.SpeedwagonException(
                    "something wrong happened")
            )
        index = Mock()
        selection_tab.item_selection_model = Mock()

        mock_message_box_exec = MagicMock()
        monkeypatch.setattr(QtWidgets.QMessageBox, "exec", mock_message_box_exec)
        with pytest.raises(exceptions.SpeedwagonException) as e:
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
    def test_is_ready_to_start(self, qtbot, number_of_indexes_selected, is_validate):
        log_manager = Mock()
        work_manager = Mock()
        selection_tab = tabs.WorkflowsTab(
            parent=None,
            workflows=MagicMock(),
            log_manager=log_manager,
            work_manager=work_manager
        )
        selection_tab.item_selector_view.selectedIndexes = \
            Mock(return_value=[Mock() for _ in range(number_of_indexes_selected)])
        assert selection_tab.is_ready_to_start() is is_validate

    def test_init_selects_first_workflow(self, qtbot):
        log_manager = Mock()
        work_manager = Mock(user_settings={})
        workflows = OrderedDict()
        workflows["Spam"] = MagicMock()
        workflows["Bacon"] = MagicMock()

        selection_tab = tabs.WorkflowsTab(
            parent=None,
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

        class MockWorkflow(job.AbsWorkflow):
            def discover_task_metadata(self, initial_results, additional_data, **user_args):
                pass

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
        assert isinstance(mock_runner.call_args_list[0][0][1], MockWorkflow)
