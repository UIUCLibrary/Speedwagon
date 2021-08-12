import logging
import os
import tempfile
from typing import List, Any, Dict

import pytest
from unittest.mock import Mock, MagicMock

from speedwagon import runner_strategies, tasks
import speedwagon


def test_job_call_order(monkeypatch):

    manager = Mock(name="manager")
    manager.get_results = Mock(return_value=["dddd"])
    manager.open = MagicMock(name="manager.opena")

    manager.open.return_value.__enter__.return_value = Mock(was_aborted=False)
    runner = runner_strategies.UsingExternalManagerForAdapter(manager)
    parent = Mock()
    parent.name = "parent"
    job = Mock()
    job.__class__ = speedwagon.job.AbsWorkflow
    options = {}
    logger = Mock()
    call_order = []

    job.initial_task = Mock(
        side_effect=lambda _: call_order.append("initial_task")
    )

    job.discover_task_metadata = Mock(
        side_effect=lambda *_: call_order.append("discover_task_metadata")
    )

    job.completion_task = Mock(
        side_effect=lambda *_: call_order.append("completion_task")
    )

    job.generate_report = Mock(
        side_effect=lambda _: call_order.append("generate_report")
    )

    runner.run(
        parent=parent,
        job=job,
        options=options,
        logger=logger
    )

    assert logger.error.called is False, ".".join(logger.error.call_args.args)
    assert job.initial_task.called is True and \
           job.discover_task_metadata.called is True and \
           job.completion_task.called is True and \
           job.generate_report.called is True

    assert call_order == [
        'initial_task',
        'discover_task_metadata',
        'completion_task',
        'generate_report'
    ]


@pytest.mark.parametrize("step", [
    "initial_task",
    'discover_task_metadata',
    'completion_task'
])
def test_task_exception_logs_error(step):
    manager = Mock(name="manager")
    manager.get_results = Mock(return_value=["dddd"])
    manager.open = MagicMock(name="manager.opena")

    manager.open.return_value.__enter__.return_value = Mock(
        was_aborted=False
    )

    runner = runner_strategies.UsingExternalManagerForAdapter(manager)
    parent = Mock()
    parent.name = "parent"
    job = Mock()
    job.__class__ = speedwagon.job.AbsWorkflow
    options = {}
    logger = Mock()
    job.discover_task_metadata = Mock(return_value=[])

    setattr(
        job,
        step,
        Mock(
            side_effect=runner_strategies.TaskFailed("error")
        )
    )

    runner.run(
        parent=parent,
        job=job,
        options=options,
        logger=logger
    )
    assert logger.error.called is True


@pytest.mark.parametrize("step", [
    "initial_task",
    'discover_task_metadata',
    'completion_task'
])
def test_task_aborted(caplog, step, monkeypatch):
    manager = Mock(name="manager")
    manager.get_results = Mock(return_value=[])
    manager.open = MagicMock(name="manager.open")
    runner = Mock(name="runner", was_aborted=False)
    manager.open.return_value.__enter__.return_value = runner

    runner_strategy = runner_strategies.UsingExternalManagerForAdapter(manager)
    parent = Mock(name="parent")
    job = Mock(name="job")
    job.__class__ = speedwagon.job.AbsWorkflow

    options = {}
    logger = logging.getLogger(__name__)
    job.discover_task_metadata = Mock(
        return_value=[MagicMock(name="new_task_metadata")])

    setattr(
        job,
        step,
        Mock(
            side_effect=lambda *_: setattr(runner, "was_aborted", True)
        )
    )

    def build_task(_):
        mock_task = Mock(name="task")
        mock_task.subtasks = [
            MagicMock()
        ]
        mock_task.main_subtasks = [
            MagicMock()
        ]
        return mock_task

    with monkeypatch.context() as mp:
        mp.setattr(
            runner_strategies.tasks.TaskBuilder,
            "build_task",
            build_task
        )

        runner_strategy.run(
            parent=parent,
            job=job,
            options=options,
            logger=logger
        )

        assert caplog.messages, "No logs recorded"
        assert "Reason: User Aborted" in caplog.text

# todo: make tests for UsingExternalManagerForAdapter2


class TestQtRunner:
    def test_run_abstract_workflow_calls_run_abs_workflow(self, qtbot):
        runner = runner_strategies.QtRunner(None)
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

        runner = runner_strategies.QtRunner(None)
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
        runner = runner_strategies.QtRunner(manager)
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
        runner = runner_strategies.QtRunner(manager)
        job = Mock()
        job.__class__ = speedwagon.job.AbsWorkflow

        task_runner = MagicMock()

        task_runner.run = Mock(
            side_effect=runner_strategies.TaskFailed("my bad")
        )
        with pytest.raises(runner_strategies.TaskFailed) as error:
            runner.run_abs_workflow(
                task_scheduler=task_runner,
                job=job,
                options={},
            )

        assert "my bad" in str(error.value)

    def test_update_progress(self):
        runner = Mock()

        runner_strategies.QtRunner.update_progress(
            runner=runner,
            current=3,
            total=10
        )
        runner.dialog.setMaximum.assert_called_with(10)
        runner.dialog.setValue.assert_called_with(3)

    def test_update_progress_accepted_on_finish(self):
        runner = Mock()

        runner_strategies.QtRunner.update_progress(
            runner=runner,
            current=10,
            total=10
        )
        assert runner.dialog.accept.called is True

    def test_update_progress_no_dialog(self):
        runner = Mock()
        runner.dialog = None
        runner_strategies.QtRunner.update_progress(
            runner=runner,
            current=3,
            total=10
        )

class TestTaskGenerator:

    @pytest.fixture()
    def workflow(self):
        workflow = MagicMock()
        workflow.__class__ = speedwagon.job.AbsWorkflow
        workflow.discover_task_metadata = Mock(
            return_value=[
                {"Input": "fakedata"}
            ]
        )
        return workflow

    def test_tasks_call_init_task(self, workflow):
        task_generator = runner_strategies.TaskGenerator(
            workflow=workflow,
            options={},
            working_directory=os.path.join("some", "real", "directory")
        )

        for subtask in task_generator.tasks():
            assert isinstance(subtask, speedwagon.tasks.Subtask)

        assert workflow.initial_task.called is True

    def test_tasks_runs_discover_metadata(self, workflow):
        task_generator = runner_strategies.TaskGenerator(
            workflow=workflow,
            options={},
            working_directory=os.path.join("some", "real", "directory")
        )

        for subtask in task_generator.tasks():
            assert isinstance(subtask, speedwagon.tasks.Subtask)
        assert workflow.discover_task_metadata.called is True

    def test_tasks_runs_create_new_task(self, workflow):
        task_generator = runner_strategies.TaskGenerator(
            workflow=workflow,
            options={},
            working_directory=os.path.join("some", "real", "directory")
        )

        for subtask in task_generator.tasks():
            assert isinstance(subtask, speedwagon.tasks.Subtask)
        assert workflow.create_new_task.called is True

    def test_tasks_runs_completion_task(self, workflow):
        task_generator = runner_strategies.TaskGenerator(
            workflow=workflow,
            options={},
            working_directory=os.path.join("some", "real", "directory")
        )

        for subtask in task_generator.tasks():
            assert isinstance(subtask, speedwagon.tasks.Subtask)
        assert workflow.completion_task.called is True

    def test_tasks_request_more_info(self, workflow):
        caller = Mock()
        task_generator = runner_strategies.TaskGenerator(
            workflow=workflow,
            options={},
            working_directory=os.path.join("some", "real", "directory"),
            caller=caller
        )
        for subtask in task_generator.tasks():
            assert isinstance(subtask, speedwagon.tasks.Subtask)
        assert caller.request_more_info.called is True

    def test_pretask_calls_initial_task(self, workflow):
        caller = Mock()
        task_generator = runner_strategies.TaskGenerator(
            workflow=workflow,
            options={},
            working_directory=os.path.join("some", "real", "directory"),
            caller=caller
        )
        list(task_generator.get_pre_tasks("dummy"))
        assert workflow.initial_task.called is True

    def test_main_task(self, workflow):
        caller = Mock()
        task_generator = runner_strategies.TaskGenerator(
            workflow=workflow,
            options={},
            working_directory=os.path.join("some", "real", "directory"),
            caller=caller
        )
        list(task_generator.get_main_tasks("dummy", [], {}))
        assert workflow.create_new_task.called is True

    def test_get_post_tasks(self, workflow):
        caller = Mock()
        task_generator = runner_strategies.TaskGenerator(
            workflow=workflow,
            options={},
            working_directory=os.path.join("some", "real", "directory"),
            caller=caller
        )
        list(task_generator.get_post_tasks("dummy", []))
        assert workflow.completion_task.called is True


class TestRunnerDisplay:

    @pytest.fixture()
    def dummy_runner(self):
        class DummyRunner(runner_strategies.RunnerDisplay):
            def refresh(self):
                pass

            def user_canceled(self):
                return False
        return DummyRunner()

    def test_basic_setters_and_getters_progress(self, dummy_runner):

        dummy_runner.total_tasks_amount = 10
        dummy_runner.current_task_progress = 5
        assert dummy_runner.total_tasks_amount == 10
        assert dummy_runner.current_task_progress == 5

    def test_basic_setters_and_getters_details(self, dummy_runner):
        dummy_runner.details = "some detail"
        assert dummy_runner.details == "some detail"

    def test_details_defaults_to_none(self, dummy_runner):
        assert dummy_runner.details is None

    def test_context_manager(self, dummy_runner):
        with dummy_runner as runner:
            assert dummy_runner == runner


class TestQtDialogProgress:
    def test_initialized(self, qtbot):
        dialog_box = runner_strategies.QtDialogProgress()

        assert dialog_box.dialog.value() == 0 and \
               dialog_box.dialog.maximum() == 0

    def test_total_tasks_amount_affects_dialog(self, qtbot):
        dialog_box = runner_strategies.QtDialogProgress()
        dialog_box.total_tasks_amount = 10
        assert dialog_box.dialog.maximum() == 10 and \
               dialog_box.total_tasks_amount == 10

    def test_current_tasks_progress_affects_dialog(self, qtbot):
        dialog_box = runner_strategies.QtDialogProgress()
        dialog_box.total_tasks_amount = 10
        dialog_box.current_task_progress = 5
        assert dialog_box.dialog.value() == 5 and \
               dialog_box.current_task_progress == 5

    def test_title_affects_dialog(self, qtbot):
        dialog_box = runner_strategies.QtDialogProgress()
        dialog_box.title = "spam"
        assert dialog_box.dialog.windowTitle() == "spam" and \
               dialog_box.title == "spam"

    def test_details_affects_dialog(self, qtbot):
        dialog_box = runner_strategies.QtDialogProgress()
        dialog_box.details = "spam"
        assert dialog_box.dialog.labelText() == "spam" and \
               dialog_box.details == "spam"


class TestTaskDispatcher:
    def test_stop_is_noop_if_not_started(self):
        queue = Mock()
        dispatcher = runner_strategies.TaskDispatcher(
            job_queue=queue
        )
        assert dispatcher.active is False and \
               dispatcher.stop() is None
