import logging

import pytest
from unittest.mock import Mock, MagicMock

from speedwagon import runner_strategies
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


class TestUsingExternalManagerForAdapter2:
    def test_run_abstract_workflow_calls_run_abs_workflow(self):
        manager = Mock()
        runner = runner_strategies.UsingExternalManagerForAdapter2(manager)
        job = Mock()
        job.__class__ = speedwagon.job.AbsWorkflow
        runner.run_abs_workflow = Mock()
        runner.run(
            job=job,
            options={}
        )

        assert runner.run_abs_workflow.called is True

    def test_run_non_abstract_workflow_doesnt_call_run_abs_workflow(self):
        manager = Mock()
        runner = runner_strategies.UsingExternalManagerForAdapter2(manager)
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
        runner = runner_strategies.UsingExternalManagerForAdapter2(manager)
        job = Mock()
        job.__class__ = speedwagon.job.AbsWorkflow

        task_runner = MagicMock()

        runner.run_abs_workflow(
            task_runner=task_runner,
            job=job,
            options={}
        )

        assert task_runner.run_pre_tasks.called is True and \
               task_runner.run_main_tasks.called is True and \
               task_runner.run_post_tasks.called is True

    def test_run_abs_workflow_pretask_failed(self, caplog):
        manager = Mock()
        runner = runner_strategies.UsingExternalManagerForAdapter2(manager)
        job = Mock()
        job.__class__ = speedwagon.job.AbsWorkflow

        task_runner = MagicMock()
        task_runner.run_pre_tasks = Mock(side_effect=runner_strategies.TaskFailed())
        runner.run_abs_workflow(
            task_runner=task_runner,
            job=job,
            options={},
        )
        assert "Job stopped during pre-task phase" in caplog.text

    def test_run_abs_workflow_run_main_tasks_failed(self, caplog):
        manager = Mock()
        runner = runner_strategies.UsingExternalManagerForAdapter2(manager)
        job = Mock()
        job.__class__ = speedwagon.job.AbsWorkflow

        task_runner = MagicMock()
        task_runner.run_main_tasks = Mock(side_effect=runner_strategies.TaskFailed("dddd"))
        runner.run_abs_workflow(
            task_runner=task_runner,
            job=job,
            options={},
        )
        assert "Job stopped during main tasks phase" in caplog.text

    def test_run_abs_workflow_run_post_tasks_failed(self, caplog):
        manager = Mock()
        runner = runner_strategies.UsingExternalManagerForAdapter2(manager)
        job = Mock()
        job.__class__ = speedwagon.job.AbsWorkflow

        task_runner = MagicMock()

        task_runner.run_post_tasks = Mock(
            side_effect=runner_strategies.TaskFailed()
        )

        runner.run_abs_workflow(
            task_runner=task_runner,
            job=job,
            options={},
        )
        assert "Job stopped during post-task phase" in caplog.text

    def test_run_abs_workflow_pre_task_canceled(self):
        manager = Mock()
        runner = runner_strategies.UsingExternalManagerForAdapter2(manager)
        job = Mock()
        job.__class__ = speedwagon.job.AbsWorkflow

        task_runner = MagicMock()
        task_runner.run_pre_tasks = Mock(
            side_effect=runner_strategies.JobCancelled()
        )
        runner.run_abs_workflow(
            task_runner=task_runner,
            job=job,
            options={},
        )
        assert task_runner.run_main_tasks.called is False

    def test_update_progress(self):
        runner = Mock()

        runner_strategies.UsingExternalManagerForAdapter2.update_progress(
            runner=runner,
            current=3,
            total=10
        )
        runner.dialog.setMaximum.assert_called_with(10)
        runner.dialog.setValue.assert_called_with(3)

    def test_update_progress_accepted_on_finish(self):
        runner = Mock()

        runner_strategies.UsingExternalManagerForAdapter2.update_progress(
            runner=runner,
            current=10,
            total=10
        )
        assert runner.dialog.accept.called is True

    def test_update_progress_no_dialog(self):
        runner = Mock()
        runner.dialog = None
        runner_strategies.UsingExternalManagerForAdapter2.update_progress(
            runner=runner,
            current=3,
            total=10
        )
