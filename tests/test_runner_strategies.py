from __future__ import annotations
import logging
import os

import pytest
from unittest.mock import Mock, MagicMock, create_autospec
from typing import List, Any, Dict, TYPE_CHECKING, Mapping

import speedwagon.exceptions
from speedwagon import runner_strategies, tasks
import speedwagon
# from tasks import TaskBuilder


# @pytest.mark.filterwarnings(
#     "ignore:Use UsingExternalManagerForAdapter2 instead:DeprecationWarning")
# def test_job_call_order(monkeypatch):
#     runners = pytest.importorskip("speedwagon.frontend.qtwidgets.runners")
#     manager = Mock(name="manager")
#     manager.get_results = Mock(return_value=["dddd"])
#     manager.open = MagicMock(name="manager.opena")
#
#     manager.open.return_value.__enter__.return_value = Mock(was_aborted=False)
#     runner = \
#         runners.UsingExternalManagerForAdapter(manager)
#
#     parent = Mock()
#     parent.name = "parent"
#     job = Mock()
#     job.__class__ = speedwagon.job.AbsWorkflow
#     options = {}
#     logger = Mock()
#     call_order = []
#
#     job.initial_task = Mock(
#         side_effect=lambda _: call_order.append("initial_task")
#     )
#
#     job.discover_task_metadata = Mock(
#         side_effect=lambda *_: call_order.append("discover_task_metadata")
#     )
#
#     job.completion_task = Mock(
#         side_effect=lambda *_: call_order.append("completion_task")
#     )
#
#     job.generate_report = Mock(
#         side_effect=lambda _: call_order.append("generate_report")
#     )
#
#     runner.run(
#         parent=parent,
#         job=job,
#         options=options,
#         logger=logger
#     )
#
#     assert logger.error.called is False, ".".join(logger.error.call_args.args)
#     assert job.initial_task.called is True and \
#            job.discover_task_metadata.called is True and \
#            job.completion_task.called is True and \
#            job.generate_report.called is True
#
#     assert call_order == [
#         'initial_task',
#         'discover_task_metadata',
#         'completion_task',
#         'generate_report'
#     ]

# @pytest.mark.parametrize("step", [
#     "initial_task",
#     'discover_task_metadata',
#     'completion_task'
# ])
# @pytest.mark.filterwarnings(
#     "ignore:Use UsingExternalManagerForAdapter2 instead:DeprecationWarning")
# def test_task_exception_logs_error(step):
#     # with pytest.warns():
#     runners = pytest.importorskip("speedwagon.frontend.qtwidgets.runners")
#
#     manager = Mock(name="manager")
#     manager.get_results = Mock(return_value=["dddd"])
#     manager.open = MagicMock(name="manager.opena")
#
#     manager.open.return_value.__enter__.return_value = Mock(
#         was_aborted=False
#     )
#
#     runner = runners.UsingExternalManagerForAdapter(manager)
#
#     parent = Mock()
#     parent.name = "parent"
#     job = Mock()
#     job.__class__ = speedwagon.job.AbsWorkflow
#     options = {}
#     logger = Mock()
#     job.discover_task_metadata = Mock(return_value=[])
#
#     setattr(
#         job,
#         step,
#         Mock(
#             side_effect=speedwagon.frontend.qtwidgets.runners.TaskFailed(
#                 "error"
#             )
#         )
#     )
#
#     runner.run(
#         parent=parent,
#         job=job,
#         options=options,
#         logger=logger
#     )
#     assert logger.error.called is True
#

# @pytest.mark.filterwarnings(
#     "ignore:Use UsingExternalManagerForAdapter2 instead:DeprecationWarning")
# @pytest.mark.parametrize("step", [
#     "initial_task",
#     'discover_task_metadata',
#     'completion_task'
# ])
# def test_task_aborted(caplog, step, monkeypatch):
#     runners = pytest.importorskip("speedwagon.frontend.qtwidgets.runners")
#     manager = Mock(name="manager")
#     manager.get_results = Mock(return_value=[])
#     manager.open = MagicMock(name="manager.open")
#     runner = Mock(name="runner", was_aborted=False)
#     runner.progress_dialog_box_handler = logging.StreamHandler()
#     manager.open.return_value.__enter__.return_value = runner
#
#     runner_strategy = runners.UsingExternalManagerForAdapter(manager)
#
#     parent = Mock(name="parent")
#     job = Mock(name="job")
#     job.__class__ = speedwagon.job.AbsWorkflow
#
#     options = {}
#     logger = logging.getLogger(__name__)
#     logger.setLevel(logging.DEBUG)
#     job.discover_task_metadata = Mock(
#         return_value=[MagicMock(name="new_task_metadata")])
#
#     setattr(
#         job,
#         step,
#         Mock(
#             side_effect=lambda *_: setattr(runner, "was_aborted", True)
#         )
#     )
#
#     def build_task(_):
#         mock_task = Mock(name="task")
#         mock_task.subtasks = [
#             MagicMock()
#         ]
#         mock_task.main_subtasks = [
#             MagicMock()
#         ]
#         return mock_task
#
#     with monkeypatch.context() as mp:
#         mp.setattr(
#             speedwagon.tasks.TaskBuilder,
#             "build_task",
#             build_task
#         )
#
#         runner_strategy.run(
#             parent=parent,
#             job=job,
#             options=options,
#             logger=logger
#         )
#
#         assert caplog.messages, "No logs recorded"
#         assert "Reason: User Aborted" in caplog.text
#
# # todo: make tests for UsingExternalManagerForAdapter2
#
#


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

    @pytest.mark.filterwarnings(
        "ignore:No way to request info from user:UserWarning")
    def test_tasks_call_init_task(self, workflow):
        task_generator = runner_strategies.TaskGenerator(
            workflow=workflow,
            options={},
            working_directory=os.path.join("some", "real", "directory")
        )

        for subtask in task_generator.tasks():
            assert isinstance(subtask, speedwagon.tasks.Subtask)

        assert workflow.initial_task.called is True

    @pytest.mark.filterwarnings(
        "ignore:No way to request info from user:UserWarning")
    def test_tasks_runs_discover_metadata(self, workflow):
        task_generator = runner_strategies.TaskGenerator(
            workflow=workflow,
            options={},
            working_directory=os.path.join("some", "real", "directory")
        )

        for subtask in task_generator.tasks():
            assert isinstance(subtask, speedwagon.tasks.Subtask)
        assert workflow.discover_task_metadata.called is True

    @pytest.mark.filterwarnings(
        "ignore:No way to request info from user:UserWarning")
    def test_tasks_runs_create_new_task(self, workflow):
        task_generator = runner_strategies.TaskGenerator(
            workflow=workflow,
            options={},
            working_directory=os.path.join("some", "real", "directory")
        )

        for subtask in task_generator.tasks():
            assert isinstance(subtask, speedwagon.tasks.Subtask)
        assert workflow.create_new_task.called is True

    @pytest.mark.filterwarnings(
        "ignore:No way to request info from user:UserWarning")
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
        class DummyRunner(speedwagon.frontend.reporter.RunnerDisplay):
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


class TestTaskDispatcher:
    def test_stop_is_noop_if_not_started(self):
        dispatcher = runner_strategies.TaskDispatcher(
            job_queue=Mock()
        )
        assert dispatcher.active is False and \
               dispatcher.stop() is None

    @pytest.mark.parametrize(
        "thread_status, expected_active, state",
        [
            (
                    None,
                    False,
                    runner_strategies.TaskDispatcherIdle
            ),
            (
                    Mock(is_alive=Mock(return_value=False)),
                    False,
                    runner_strategies.TaskDispatcherIdle
            ),
            (
                    Mock(is_alive=Mock(return_value=True)),
                    True,
                    runner_strategies.TaskDispatcherRunning
            )
        ]
    )
    def test_active(self, thread_status, expected_active, state):
        dispatcher = runner_strategies.TaskDispatcher(
            job_queue=Mock()
        )
        dispatcher.current_state = state(dispatcher)
        dispatcher.thread = thread_status
        assert dispatcher.active is expected_active

    def test_start_set_state_to_running(self):
        dispatcher = runner_strategies.TaskDispatcher(
            job_queue=Mock()
        )

        dispatcher.current_state = \
            runner_strategies.TaskDispatcherIdle(dispatcher)

        try:
            dispatcher.start()
            assert dispatcher.current_state.state_name == "Running"
        finally:
            dispatcher.stop()

    def test_stop_set_state(self, monkeypatch):
        dispatcher = runner_strategies.TaskDispatcher(
            job_queue=Mock()
        )

        # ======================================================================
        # This has to happen before the monkey patching so that the method can
        # still manage to run.
        # ======================================================================
        dispatcher.current_state = \
            runner_strategies.TaskDispatcherIdle(dispatcher)

        actual_halt_dispatch = \
            runner_strategies.TaskDispatcherStopping.halt_dispatching

        def halt_dispatching(*args, **kwargs):
            actual_halt_dispatch(*args, **kwargs)

        halt_dispatching_method = Mock()
        halt_dispatching_method.side_effect = halt_dispatching
        # ======================================================================

        with monkeypatch.context() as mp:
            mp.setattr(runner_strategies.TaskDispatcherStopping,
                       "halt_dispatching",
                       lambda caller: halt_dispatching_method(caller)
                       )
            try:
                dispatcher.start()
                assert dispatcher.current_state.state_name == "Running"
            finally:
                dispatcher.stop()
        assert dispatcher.current_state.state_name == "Idle"
        assert halt_dispatching_method.called is True


class TestTaskDispatcherRunning:
    def test_running_on_active_is_noop_warning(self, caplog):
        dispatcher = runner_strategies.TaskDispatcher(
            job_queue=Mock()
        )
        state = runner_strategies.TaskDispatcherRunning(dispatcher)
        state.start()

        assert any(
            "Processing thread is already started"
            in message.message and message.levelname == "WARNING"
            for message in caplog.records
        )


class TestTaskDispatcherStopping:
    def test_running_stop_on_stopping_is_noop_warning(self, caplog):
        dispatcher = runner_strategies.TaskDispatcher(
            job_queue=Mock()
        )
        state = runner_strategies.TaskDispatcherStopping(dispatcher)
        state.stop()

        assert any(
            "Processing thread is currently stopping"
            in message.message and message.levelname == "WARNING"
            for message in caplog.records
        )

    def test_running_starting_on_stopping_is_noop_warning(self, caplog):
        dispatcher = runner_strategies.TaskDispatcher(
            job_queue=Mock()
        )
        state = runner_strategies.TaskDispatcherStopping(dispatcher)
        state.start()

        assert any(
            "Unable to start while processing is stopping"
            in message.message and message.levelname == "WARNING"
            for message in caplog.records
        )


class TestTaskScheduler:
    def test_default_request_more_info_noop(self, capsys):
        scheduler = runner_strategies.TaskScheduler(
            working_directory="some_dir")
        assert scheduler.request_more_info(Mock(), "dummy", "dummy") is None
        captured = capsys.readouterr()
        assert "dummy" not in captured.out

    @pytest.mark.parametrize(
        "reporter",
        [
            None,
            MagicMock()
        ]
    )
    def test_run(self, monkeypatch, reporter):
        scheduler = runner_strategies.TaskScheduler(
            working_directory="some_dir")
        workflow = Mock()
        scheduler.reporter = reporter
        workflow.discover_task_metadata = Mock(return_value=[])
        options = {}
        subtask = speedwagon.tasks.Subtask()
        subtask.exec = Mock()

        monkeypatch.setattr(
            runner_strategies.TaskGenerator,
            "get_main_tasks",
            create_autospec(
                runner_strategies.TaskGenerator.get_main_tasks,
                return_value=[subtask]
            )
        )
        scheduler.run(
            workflow,
            options
        )
        assert subtask.exec.called is True

    def test_task_canceled(self):
        scheduler = runner_strategies.TaskScheduler(
            working_directory="some_dir")
        scheduler.reporter = Mock(user_canceled=True)
        scheduler.iter_tasks = Mock(return_value=[Mock()])

        workflow = Mock()
        workflow.discover_task_metadata = Mock(return_value=[])

        options = {}

        subtask = speedwagon.tasks.Subtask()
        subtask.exec = Mock()
        subtask._task_queue = Mock(unfinished_tasks=1)
        with pytest.raises(speedwagon.exceptions.JobCancelled):
            scheduler.run_workflow_jobs(workflow, options, scheduler.reporter)


class SpamTask(speedwagon.tasks.Subtask):
    name = "Spam"

    def work(self) -> bool:
        return True

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data: Mapping[str, Any],
                               user_args) -> List[dict]:
        return [
            {"dummy": "yes"},
            {"dummy": "yes"},
        ]


class SpamWorkflow(speedwagon.Workflow):
    name = "spam"

    def create_new_task(self, task_builder: speedwagon.tasks.TaskBuilder,
                        job_args) -> None:
        task_builder.add_subtask(SpamTask())

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data: Mapping[str, Any],
                               user_args) -> List[dict]:
        return [
            {"dummy": "yes"},
            {"dummy": "yes"},
        ]


class TestBackgroundJobManager:

    def test_manager_does_nothing(self):
        with runner_strategies.BackgroundJobManager() as manager:
            assert manager is not None

    def test_job_finished_called(self, monkeypatch):
        callbacks = Mock(name="callbacks")

        liaison = runner_strategies.JobManagerLiaison(
            callbacks=callbacks,
            events=Mock()
        )
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            "get_app_data_dir",
            lambda *_: "."
        )
        with runner_strategies.BackgroundJobManager() as manager:
            manager.valid_workflows = {"spam": SpamWorkflow}
            manager.submit_job(
                workflow_name="spam",
                options={},
                app=Mock(),
                liaison=liaison
            )
        assert callbacks.finished.called is True

    @pytest.mark.filterwarnings(
        "ignore::pytest.PytestUnhandledThreadExceptionWarning"
    )
    def test_exception_caught(self, monkeypatch):
        class BadTask(speedwagon.tasks.Subtask):

            def work(self) -> bool:
                raise FileNotFoundError("whoops")

        class BaconWorkflow(speedwagon.Workflow):
            name = "bacon"

            def create_new_task(self, task_builder: tasks.TaskBuilder,
                                job_args) -> None:
                task_builder.add_subtask(BadTask())

            def discover_task_metadata(self, initial_results: List[Any],
                                       additional_data: Mapping[str, Any],
                                       user_args) -> List[dict]:
                return [
                    {"dummy": "yes"}
                ]
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            "get_app_data_dir",
            lambda *_: "."
        )
        with pytest.raises(FileNotFoundError):
            with runner_strategies.BackgroundJobManager() as manager:
                manager.valid_workflows = {"bacon": BaconWorkflow}
                manager.submit_job(
                    workflow_name="bacon",
                    options={},
                    app=Mock(),
                    liaison=runner_strategies.JobManagerLiaison(Mock(), Mock())
                )


class TestThreadedEvents:
    def test_done(self):
        events = runner_strategies.ThreadedEvents()
        assert events.is_done() is False
        events.done()
        assert events.is_done() is True

    def test_stop(self):
        events = runner_strategies.ThreadedEvents()
        assert events.is_stopped() is False
        events.stop()
        assert events.is_stopped() is True

    def test_started(self):
        events = runner_strategies.ThreadedEvents()
        assert events.has_started() is False
        events.started.set()
        assert events.has_started() is True


@pytest.mark.parametrize("method_name", [
    'create_new_task',
    'discover_task_metadata',
    'generate_report',
    'get_additional_info',
    'create_new_task'
])
def test_simple_api_run_workflow_calls_methods(method_name):
    mock_workflow = Mock(
        spec=speedwagon.Workflow,
        name="Workflow",
        get_additional_info=Mock()
    )
    mock_workflow.discover_task_metadata = Mock(return_value=[{}])
    mock_workflow.request_more_info = Mock(return_value={})
    runner_strategies.simple_api_run_workflow(
        mock_workflow, workflow_options={}
    )

    assert getattr(mock_workflow, method_name).called is True


def test_simple_api_calls_exec_on_task(monkeypatch):
    mock_workflow = Mock(
        spec=speedwagon.Workflow,
        name="Workflow",
        get_additional_info=Mock()
    )
    mock_task = Mock(spec=speedwagon.tasks.Subtask)
    mock_workflow.discover_task_metadata = Mock(return_value=[{}])
    mock_workflow.request_more_info = Mock(return_value={})

    monkeypatch.setattr(
        runner_strategies.TaskGenerator,
        "get_main_tasks",
        create_autospec(
            runner_strategies.TaskGenerator.get_main_tasks, 
            return_value=[mock_task]
        )
    )

    runner_strategies.simple_api_run_workflow(
        mock_workflow, workflow_options={}
    )
    assert mock_task.exec.called is True
