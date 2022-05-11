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


class TestQtRunner:
    def test_run_abstract_workflow_calls_run_abs_workflow(self, qtbot):
        runner = speedwagon.frontend.qtwidgets.runners.QtRunner(None)
        job = Mock()
        job.__class__ = speedwagon.job.Workflow
        runner.run_abs_workflow = Mock()
        runner.run(
            job=job,
            options={}
        )

        assert runner.run_abs_workflow.called is True

    def test_run_non_abstract_workflow_doesnt_call_run_abs_workflow(
            self, qtbot):

        runner = speedwagon.frontend.qtwidgets.runners.QtRunner(None)
        job = Mock()
        # NOTE: job.__class__ != speedwagon.job.AbsWorkflow
        runner.run_abs_workflow = Mock()
        runner.run(
            job=job,
            options={}
        )

        assert runner.run_abs_workflow.called is False

    def test_run_abs_workflow_calls_task_runner(self):
        manager = Mock()
        runner = speedwagon.frontend.qtwidgets.runners.QtRunner(manager)
        job = Mock()
        job.__class__ = speedwagon.job.AbsWorkflow

        task_runner = MagicMock()

        runner.run_abs_workflow(
            task_scheduler=task_runner,
            job=job,
            options={}
        )
        assert task_runner.run.called is True

    def test_run_abs_workflow_fails_with_task_failed_exception(self):
        manager = Mock()
        runner = speedwagon.frontend.qtwidgets.runners.QtRunner(manager)
        job = Mock()
        job.__class__ = speedwagon.job.AbsWorkflow

        task_runner = MagicMock()

        task_runner.run = Mock(
            side_effect=speedwagon.frontend.qtwidgets.runners.TaskFailed("my bad")
        )
        with pytest.raises(speedwagon.frontend.qtwidgets.runners.TaskFailed) as error:
            runner.run_abs_workflow(
                task_scheduler=task_runner,
                job=job,
                options={},
            )

        assert "my bad" in str(error.value)

    def test_update_progress(self):
        runner = Mock()

        speedwagon.frontend.qtwidgets.runners.QtRunner.update_progress(
            runner=runner,
            current=3,
            total=10
        )
        runner.dialog.setMaximum.assert_called_with(10)
        runner.dialog.setValue.assert_called_with(3)

    def test_update_progress_accepted_on_finish(self):
        runner = Mock()

        speedwagon.frontend.qtwidgets.runners.QtRunner.update_progress(
            runner=runner,
            current=10,
            total=10
        )
        assert runner.dialog.accept.called is True

    def test_update_progress_no_dialog(self):
        runner = Mock()
        runner.dialog = None
        speedwagon.frontend.qtwidgets.runners.QtRunner.update_progress(
            runner=runner,
            current=3,
            total=10
        )


class TestWorkRunnerExternal3:
    @pytest.mark.filterwarnings(
        "ignore:Don't use the dialog:DeprecationWarning")
    def test_abort_calls_callback(self, qtbot):
        with speedwagon.frontend.qtwidgets.runners.WorkRunnerExternal3(QtWidgets.QWidget()) as r:
            r.abort_callback = Mock()
            r.abort()
        assert r.abort_callback.called is True

    @pytest.mark.filterwarnings(
        "ignore:Don't use the dialog:DeprecationWarning")
    def test_abort_worth_with_no_callback(self, qtbot):
        with speedwagon.frontend.qtwidgets.runners.WorkRunnerExternal3(QtWidgets.QWidget()) as r:
            r.abort_callback = None
            r.abort()

    @pytest.mark.filterwarnings(
        "ignore:Don't use the dialog:DeprecationWarning")
    def test_someone_resetting_dialog_throws_error(self, qtbot):
        with pytest.raises(AttributeError) as e:
            work_runner = \
                speedwagon.frontend.qtwidgets.runners.WorkRunnerExternal3(QtWidgets.QWidget())
            with work_runner as r:
                r.dialog = None
        assert "dialog" in str(e.value)
