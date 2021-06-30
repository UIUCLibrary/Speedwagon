from unittest.mock import Mock

from PyQt5 import QtWidgets

from speedwagon import worker


class TestWorkRunnerExternal3:
    def test_abort_calls_callback(self, qtbot):
        work_runner = worker.WorkRunnerExternal3(QtWidgets.QWidget())
        with work_runner as r:
            r.abort_callback = Mock()
            r.abort()
        assert r.abort_callback.called is True
