from unittest.mock import Mock, MagicMock

import pytest

from speedwagon import tabs, exceptions


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