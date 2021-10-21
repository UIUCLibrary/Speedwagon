import logging
import os
import queue
import threading

import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Any, Dict
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
    runner.progress_dialog_box_handler = logging.StreamHandler()
    manager.open.return_value.__enter__.return_value = runner

    runner_strategy = runner_strategies.UsingExternalManagerForAdapter(manager)
    parent = Mock(name="parent")
    job = Mock(name="job")
    job.__class__ = speedwagon.job.AbsWorkflow

    options = {}
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
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
            speedwagon.tasks.TaskBuilder,
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

        dialog_box = runner_strategies.QtDialogProgress()
        dialog_box.task_scheduler = task_scheduler
        processEvents = Mock()

        with monkeypatch.context() as mp:

            mp.setattr(
                runner_strategies.QtWidgets.QApplication,
                "processEvents",
                processEvents
            )

            dialog_box.refresh()

        assert processEvents.called is True


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
            lambda *args, **kwargs: [subtask]
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
        with pytest.raises(speedwagon.job.JobCancelled):
            scheduler.run_workflow_jobs(workflow, options, scheduler.reporter)

#
# class TestJobManager:
#     def test_d(self):
#         with runner_strategies.JobManager() as job_manager:
#             pass
#
#     def test_manages_creations(self):
#         with runner_strategies.JobManager() as job_manager:
#             job_manager.valid_workflows = {"spam": SpamWorkflow}
#             new_worker = job_manager.submit_job(
#                 workflow_name="spam",
#                 working_directory="working_dir",
#             )
#             assert new_worker in job_manager
#
#     def test_current_progress_defaults_to_none(self):
#         with runner_strategies.JobManager() as job_manager:
#             job_manager.valid_workflows = {"spam": Mock()}
#             new_worker = job_manager.submit_job(
#                 workflow_name="spam",
#                 working_directory="working_dir"
#             )
#             assert new_worker.current_task_progress is None
#
#     def test_submit_job_name_matches(self):
#         class SpamWorkflow(speedwagon.Workflow):
#             # name = "spam"
#
#             def discover_task_metadata(self, initial_results: List[Any],
#                                        additional_data: Dict[str, Any],
#                                        **user_args) -> List[dict]:
#                 return []
#
#         with runner_strategies.JobManager() as job_manager:
#             job_manager.valid_workflows = {"spam": SpamWorkflow}
#             new_worker = job_manager.submit_job(
#                 workflow_name="spam",
#                 working_directory="working_dir",
#             )
#             assert new_worker.workflow_name == "spam"
#
#     def test_join_status_joined(self):
#         class DummyWorkflow(speedwagon.Workflow):
#
#             def discover_task_metadata(self, initial_results: List[Any],
#                                        additional_data: Dict[str, Any],
#                                        **user_args) -> List[dict]:
#                 return []
#
#         with runner_strategies.JobManager() as job_manager:
#             job_manager.valid_workflows = {"spam": DummyWorkflow}
#             new_worker = job_manager.submit_job(
#                 workflow_name="spam",
#                 working_directory="working_dir",
#             )
#             new_worker.start()
#             assert new_worker.status.status_name == "idle"
#             new_worker.run()
#             new_worker.join()
#             assert new_worker.status.status_name == "joined"
#
#     def test_job_manager_closed_status_joined(self):
#         class DummyWorkflow(speedwagon.Workflow):
#
#             def discover_task_metadata(self, initial_results: List[Any],
#                                        additional_data: Dict[str, Any],
#                                        **user_args) -> List[dict]:
#                 return []
#
#         with runner_strategies.JobManager() as job_manager:
#             job_manager.valid_workflows = {"spam": DummyWorkflow}
#             new_worker = job_manager.submit_job(
#                 workflow_name="spam",
#                 working_directory="working_dir",
#             )
#             new_worker.start()
#             assert new_worker.status.status_name == "idle"
#             new_worker.run()
#         assert new_worker.status.status_name == "joined"
#
#     @pytest.fixture(scope="module")
#     def task_queue(self):
#         return queue.Queue(maxsize=1)
#
#     @pytest.fixture(scope="module")
#     def task_ready_condition(self):
#         return threading.Condition()
#
#     @pytest.fixture()
#     def producer(self, task_queue):
#         task_producer = runner_strategies.ThreadedTaskProducer(
#             task_queue
#         )
#
#         yield task_producer
#         task_producer.shutdown()
#
#     # def test_join_status_single_step(self):
#     #     class DummyTask(speedwagon.tasks.Subtask):
#     #
#     #         def work(self) -> bool:
#     #             pass
#     #
#     #     class DummyWorkflow(speedwagon.Workflow):
#     #         name = "spam"
#     #         def create_new_task(self, task_builder: tasks.TaskBuilder,
#     #                             **job_args) -> None:
#     #             dummy_task = DummyTask()
#     #             task_builder.add_subtask(dummy_task)
#     #
#     #         def discover_task_metadata(self, initial_results: List[Any],
#     #                                    additional_data: Dict[str, Any],
#     #                                    **user_args) -> List[dict]:
#     #             return [
#     #                 {"dummy": "yes"},
#     #                 {"dummy": "yes"},
#     #             ]
#     #
#     #     with runner_strategies.JobManager() as job_manager:
#     #         job_manager.valid_workflows = {"spam": DummyWorkflow}
#     #         new_worker = job_manager.submit_job(
#     #             workflow_name="spam",
#     #             working_directory="working_dir",
#     #         )
#     #         new_worker.run_next_task()
#     #         # assert new_worker.total_tasks == 2
#     #         # assert new_worker.status.status_name == "working"
#     #         # new_worker.join()
#     #     assert new_worker.status.status_name == "joined"
#     def test_job_error_propagates(self):
#         # FIXME: There is a race condition
#
#         class DummyTask(speedwagon.tasks.Subtask):
#             def work(self) -> bool:
#                 raise ValueError("I did something wrong")
#
#         class DummyWorkflow(speedwagon.Workflow):
#             name = "spam"
#
#             def create_new_task(self,
#                                 task_builder: speedwagon.tasks.TaskBuilder,
#                                 **job_args) -> None:
#                 dummy_task = DummyTask()
#                 task_builder.add_subtask(dummy_task)
#
#             def discover_task_metadata(self, initial_results: List[Any],
#                                        additional_data: Dict[str, Any],
#                                        **user_args) -> List[dict]:
#                 return [
#                     {"dummy": "yes"},
#                     {"dummy": "yes"},
#                 ]
#
#         with pytest.raises(ValueError):
#             with runner_strategies.JobManager() as job_manager:
#                 job_manager.valid_workflows = {"spam": DummyWorkflow}
#                 new_worker = job_manager.submit_job(
#                     workflow_name="spam",
#                     working_directory="working_dir",
#                 )
#                 new_worker.start()
#                 new_worker.run()
#                 new_worker.join()
#
#     def test_failed_task_propagates(self,
#                                     task_queue,
#                                     producer):
#
#         class FailingTask(speedwagon.tasks.Subtask):
#             def work(self) -> bool:
#                 raise ValueError("I did something wrong")
#
#         task_consumer = runner_strategies.ThreadedTaskConsumer(
#             task_queue
#         )
#         producer.workflow = Mock()
#         producer.working_directory = "somewhere"
#         producer.submit_task(FailingTask())
#         producer.start()
#         task_consumer.start()
#         with pytest.raises(ValueError) as e:
#             task_consumer.shutdown()
#         assert "I did something wrong" in str(e.value)
#
#
#     def test_spam(self):
#         class Spam:
#             def __init__(self):
#                 self.exc = None
#
#             def payload(self):
#                 print("running")
#                 try:
#                     raise Exception("noooo")
#                 except Exception as e:
#                     self.exc = e
#                     raise
#
#         p = Spam()
#
#         t = threading.Thread(target=p.payload)
#         t.start()
#         # def join():
#         #     t.join()
#         #     if p.exc is not None:
#         #         raise p.exc
#
#
#         with pytest.raises(Exception):
#             t.join()
#             if p.exc is not None:
#                 raise p.exc

# class TestTaskSchedulerStates:
#     def test_starting_init_changes_status_to_idle(self):
#         job_manager = Mock()
#
#         # This makes sure that the task producer returns that it's ready
#         job_manager.task_producer.start = lambda await_event: await_event.set()
#         state = runner_strategies.TaskSchedulerInit(job_manager)
#         state.start(None)
#         try:
#             assert job_manager.status.status_name == "idle"
#         finally:
#             state.join()
#
#     def test_running_in_idle_changes_to_working(self):
#         class DummyWorkflow(speedwagon.Workflow):
#             name = "spam"
#
#             def create_new_task(self,
#                                 task_builder: speedwagon.tasks.TaskBuilder,
#                                 **job_args) -> None:
#                 task_builder.add_subtask(Mock())
#
#             def discover_task_metadata(self, initial_results: List[Any],
#                                        additional_data: Dict[str, Any],
#                                        **user_args) -> List[dict]:
#                 return [
#                     {"dummy": "yes"},
#                     {"dummy": "yes"},
#                 ]
#
#         context = Mock(name="context")
#
#         task_scheduler = runner_strategies.TaskScheduler2(context, "")
#         task_scheduler.valid_workflows = {"spam": DummyWorkflow}
#         state = runner_strategies.TaskSchedulerIdle(task_scheduler)
#         state.context.workflow_name = "spam"
#         state.run()
#         try:
#             assert task_scheduler.status.status_name == "working"
#         finally:
#             task_scheduler.join()
#
#     def test_joining_in_working_changes_status_to_joining(self):
#         job_manager = Mock()
#         state = runner_strategies.TaskSchedulerWorking(job_manager)
#         state.join()
#         assert job_manager.status.status_name == "joined"
#
#     @pytest.mark.parametrize("state", [
#         runner_strategies.TaskSchedulerIdle,
#         runner_strategies.TaskSchedulerWorking,
#         runner_strategies.TaskSchedulerJoined,
#     ])
#     def test_starting_in_invalid_state_results_in_error(self, state):
#         job_manager = Mock()
#         with pytest.raises(RuntimeError):
#             state(job_manager).start(None)
#
#     @pytest.mark.parametrize("state", [
#         runner_strategies.TaskSchedulerInit,
#         runner_strategies.TaskSchedulerWorking,
#         runner_strategies.TaskSchedulerJoined,
#     ])
#     def test_running_in_invalid_state_results_in_error(self, state):
#         job_manager = Mock()
#         with pytest.raises(RuntimeError):
#             state(job_manager).run()
#
#     # def test_s(self):
#     #     with runner_strategies.JobManager() as job_manager:
#     #         job_manager.start()

#
# class TestExecuteTaskPacket:
#     def test_done_raises_terminate(self):
#         task_consumer = runner_strategies.ThreadedTaskConsumer(queue.Queue())
#         with pytest.raises(runner_strategies.TerminateConsumerThread):
#             task_consumer.execute_task_packet(
#                 packet=runner_strategies.TaskPacket(
#                     runner_strategies.TaskPacket.PacketType.COMMAND,
#                     "done"
#                 )
#             )
#
#     def test_task_calls_exec(self):
#         task = Mock()
#         task_consumer = runner_strategies.ThreadedTaskConsumer(queue.Queue())
#         task_consumer.execute_task_packet(
#             packet=runner_strategies.TaskPacket(
#                 runner_strategies.TaskPacket.PacketType.TASK,
#                 task
#             )
#         )
#         assert task.exec.called is True
#
#     def test_error_fails_only_with_a_log(self, caplog):
#         task_consumer = runner_strategies.ThreadedTaskConsumer(queue.Queue())
#         task_consumer.execute_task_packet(
#             packet=runner_strategies.TaskPacket(
#                 "something_invalid",
#                 1
#             )
#         )
#
#         assert any(
#             "Unknown packet type"
#             in message.message and message.levelname == "ERROR"
#             for message in caplog.records
#         )
#

class SpamTask(speedwagon.tasks.Subtask):
    name = "Spam"
    def work(self) -> bool:
        return True
    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data: Dict[str, Any],
                               **user_args) -> List[dict]:
        return [
            {"dummy": "yes"},
            {"dummy": "yes"},
        ]


class SpamWorkflow(speedwagon.Workflow):
    name = "spam"

    def create_new_task(self, task_builder: speedwagon.tasks.TaskBuilder,
                        **job_args) -> None:
        task_builder.add_subtask(SpamTask())

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data: Dict[str, Any],
                               **user_args) -> List[dict]:
        return [
            {"dummy": "yes"},
            {"dummy": "yes"},
        ]


class TestBackgroundJobManager:

    def test_manager_does_nothing(self):
        with runner_strategies.BackgroundJobManager() as manager:
            assert manager is not None

    def test_job_finished_called(self):
        callbacks = Mock(name="callbacks")
        liaison = runner_strategies.JobManagerLiaison(callbacks=callbacks, events=Mock())
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
    def test_exception_caught(self):
        class BadTask(speedwagon.tasks.Subtask):

            def work(self) -> bool:
                raise FileNotFoundError("whoops")

        class BaconWorkflow(speedwagon.Workflow):
            name = "bacon"

            def create_new_task(self, task_builder: tasks.TaskBuilder,
                                **job_args) -> None:
                task_builder.add_subtask(BadTask())

            def discover_task_metadata(self, initial_results: List[Any],
                                       additional_data: Dict[str, Any],
                                       **user_args) -> List[dict]:
                return [
                    {"dummy": "yes"}
                ]

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
