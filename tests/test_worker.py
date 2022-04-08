import time
from unittest.mock import Mock

import pytest
from PySide6 import QtWidgets

from speedwagon import worker, frontend


class TestWorkRunnerExternal3:
    @pytest.mark.filterwarnings(
        "ignore:Don't use the dialog:DeprecationWarning")
    def test_abort_calls_callback(self, qtbot):
        with frontend.qtwidgets.runners.WorkRunnerExternal3(QtWidgets.QWidget()) as r:
            r.abort_callback = Mock()
            r.abort()
        assert r.abort_callback.called is True

    @pytest.mark.filterwarnings(
        "ignore:Don't use the dialog:DeprecationWarning")
    def test_abort_worth_with_no_callback(self, qtbot):
        with frontend.qtwidgets.runners.WorkRunnerExternal3(QtWidgets.QWidget()) as r:
            r.abort_callback = None
            r.abort()

    @pytest.mark.filterwarnings(
        "ignore:Don't use the dialog:DeprecationWarning")
    def test_someone_resetting_dialog_throws_error(self, qtbot):
        with pytest.raises(AttributeError) as e:
            work_runner = frontend.qtwidgets.runners.WorkRunnerExternal3(QtWidgets.QWidget())
            with work_runner as r:
                r.dialog = None
        assert "dialog" in str(e.value)
