import time
from unittest.mock import Mock

import pytest
from PyQt5 import QtWidgets

from speedwagon import worker


class TestWorkRunnerExternal3:
    def test_abort_calls_callback(self, qtbot):
        with worker.WorkRunnerExternal3(QtWidgets.QWidget()) as r:
            r.abort_callback = Mock()
            r.abort()
        assert r.abort_callback.called is True

    def test_abort_worth_with_no_callback(self, qtbot):
        with worker.WorkRunnerExternal3(QtWidgets.QWidget()) as r:
            r.abort_callback = None
            r.abort()

    def test_someone_resetting_dialog_throws_error(self, qtbot):
        with pytest.raises(AttributeError) as e:
            work_runner = worker.WorkRunnerExternal3(QtWidgets.QWidget())
            with work_runner as r:
                r.dialog = None
        assert "dialog" in str(e.value)


class TestProgressMessageBoxLogHandler:
    def test_flush_first_time(self):
        handler = worker.ProgressMessageBoxLogHandler()
        checker = worker.NeverBeenFlushed(handler)
        assert checker.should_be_flush() is True

    def test_flush_if_time_greater_than_refresh_rate(self):
        handler = worker.ProgressMessageBoxLogHandler()
        checker = worker.FlushWaitedLongEnough(handler)

        handler.last_flushed_time = 0
        assert checker.should_be_flush() is True

    def test_no_flush_if_timer_thread_already_set(self):
        handler = worker.ProgressMessageBoxLogHandler()
        handler.update_thread = Mock(name="Mock thread")
        checker = worker.TimerThreadAlreadyRunning(handler)
        assert checker.should_be_flush() is False

    @pytest.mark.parametrize("checker_value, expected", [
        (False, False),
        (True, True),
        (None, False),
    ]
                             )
    def test_ready_to_flush_checks_return_value(self, checker_value, expected):
        handler = worker.ProgressMessageBoxLogHandler()
        mock_checker = Mock()
        mock_checker.should_be_flush.return_value = checker_value
        checks = [
            mock_checker
        ]
        assert handler.ready_to_flush(checks=checks) is expected
