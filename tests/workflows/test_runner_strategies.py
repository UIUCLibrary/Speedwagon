import pytest
from typing import List, Any, Dict
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
    assert call_order == ['initial_task', 'discover_task_metadata', 'completion_task', 'generate_report']


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
    setattr(job, step, Mock(
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
