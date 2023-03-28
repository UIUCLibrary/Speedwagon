from unittest.mock import Mock, MagicMock

import pytest


import speedwagon
QtWidgets = pytest.importorskip("PySide6.QtWidgets")


class TestQtDialogProgress:
    def test_initialized(self, qtbot):
        from speedwagon.frontend.qtwidgets.runners import QtDialogProgress
        dialog_box = QtDialogProgress()

        assert dialog_box.dialog.value() == 0 and \
               dialog_box.dialog.maximum() == 0

    def test_total_tasks_amount_affects_dialog(self, qtbot):
        from speedwagon.frontend.qtwidgets.runners import QtDialogProgress
        dialog_box = QtDialogProgress()
        dialog_box.total_tasks_amount = 10
        assert dialog_box.dialog.maximum() == 10 and \
               dialog_box.total_tasks_amount == 10

    def test_current_tasks_progress_affects_dialog(self, qtbot):
        from speedwagon.frontend.qtwidgets.runners import QtDialogProgress
        dialog_box = QtDialogProgress()
        dialog_box.total_tasks_amount = 10
        dialog_box.current_task_progress = 5
        assert dialog_box.dialog.value() == 5 and \
               dialog_box.current_task_progress == 5

    def test_title_affects_dialog(self, qtbot):
        from speedwagon.frontend.qtwidgets.runners import QtDialogProgress
        dialog_box = QtDialogProgress()
        dialog_box.title = "spam"
        assert dialog_box.dialog.windowTitle() == "spam" and \
               dialog_box.title == "spam"

    def test_details_affects_dialog(self, qtbot):
        from speedwagon.frontend.qtwidgets.runners import QtDialogProgress
        dialog_box = QtDialogProgress()
        dialog_box.details = "spam"
        assert dialog_box.dialog.labelText() == "spam" and \
               dialog_box.details == "spam"

    @pytest.mark.parametrize(
        "task_scheduler",
        [
            None,
            Mock(
                total_tasks=2,
                current_task_progress=1
            )
        ]
    )
    def test_refresh_calls_process_events(
            self, qtbot, task_scheduler, monkeypatch):
        from speedwagon.frontend.qtwidgets.runners import QtDialogProgress
        dialog_box = QtDialogProgress()
        dialog_box.task_scheduler = task_scheduler
        processEvents = Mock()

        with monkeypatch.context() as mp:

            mp.setattr(
                QtWidgets.QApplication,
                "processEvents",
                processEvents
            )

            dialog_box.refresh()

        assert processEvents.called is True
