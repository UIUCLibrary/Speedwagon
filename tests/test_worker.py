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

    @pytest.mark.filterwarnings("ignore:Don't use the dialog")
    def test_abort_worth_with_no_callback(self, qtbot):
        with worker.WorkRunnerExternal3(QtWidgets.QWidget()) as r:
            r.abort_callback = None
            r.abort()

    @pytest.mark.filterwarnings("ignore:Don't use the dialog")
    def test_someone_resetting_dialog_throws_error(self, qtbot):
        with pytest.raises(AttributeError) as e:
            work_runner = worker.WorkRunnerExternal3(QtWidgets.QWidget())
            with work_runner as r:
                r.dialog = None
        assert "dialog" in str(e.value)
