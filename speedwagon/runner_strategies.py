"""Defining execution of a given workflow steps and processes."""
from __future__ import annotations

import abc
import contextlib
import dataclasses
import enum

import logging
import os
import queue
import sys
import tempfile
import threading
import traceback
import typing
import warnings
from types import TracebackType
from typing import List, Any, Dict, Optional, Type, TypeVar, Mapping, Callable
import functools
import speedwagon.config
import speedwagon.exceptions
from speedwagon import runner

_T = TypeVar("_T", bound=Mapping[str, object])

if typing.TYPE_CHECKING:
    from speedwagon.job import AbsWorkflow, Workflow
    from speedwagon.config import SettingsData
    import speedwagon.tasks

__all__ = [
    "RunRunner",
    "TaskDispatcher",
    "TaskScheduler",
    "simple_api_run_workflow",
]

module_logger = logging.getLogger(__name__)

USER_ABORTED_MESSAGE = "User Aborted"


class AbsEvents(abc.ABC):
    @abc.abstractmethod
    def stop(self) -> None:
        """Stop."""

    @abc.abstractmethod
    def is_done(self) -> bool:
        """Get if it is done."""

    @abc.abstractmethod
    def is_stopped(self) -> bool:
        """Get if it is stopped."""

    @abc.abstractmethod
    def done(self) -> None:
        """Set to done."""


class JobSuccess(enum.IntEnum):
    SUCCESS = 0
    FAILURE = 1
    ABORTED = 2


class AbsJobCallbacks(abc.ABC):
    @abc.abstractmethod
    def error(
        self,
        message: Optional[str] = None,
        exc: Optional[BaseException] = None,
        traceback_string: Optional[str] = None,
    ) -> None:
        """Had an error."""

    @abc.abstractmethod
    def status(self, text: str) -> None:
        """Set status."""

    @abc.abstractmethod
    def log(self, text: str, level: int = logging.INFO) -> None:
        """Log information."""

    def start(self) -> None:  # noqa: B027
        """Start.

        By default, this is a no-op
        """

    def refresh(self) -> None:  # noqa: B027
        """Refresh.

        By default, this is a no-op
        """

    @abc.abstractmethod
    def cancelling_complete(self) -> None:
        """Run when the job has been cancelled."""

    @abc.abstractmethod
    def finished(self, result: JobSuccess) -> None:
        """Job finished."""

    @abc.abstractmethod
    def update_progress(
        self, current: Optional[int], total: Optional[int]
    ) -> None:
        """Update the job's progress."""


class RunRunner:
    """Context for running AbsRunner2 strategies."""

    def __init__(self, strategy: runner.AbsRunner2) -> None:
        """Create a new runner executor."""
        self._strategy = strategy

    def run(
        self,
        tool: AbsWorkflow,
        options: typing.Mapping[str, object],
        logger: logging.Logger,
        completion_callback=None,
    ) -> None:
        """Execute runner job."""
        self._strategy.run(tool, options, logger, completion_callback)


class TaskGenerator:
    def __init__(
        self,
        workflow: Workflow,
        options: typing.Mapping[str, Any],
        working_directory: str,
        caller: typing.Optional["TaskScheduler"] = None,
    ) -> None:
        self.workflow = workflow
        self.options = options
        self.working_directory = working_directory
        self.current_task: typing.Optional[int] = None
        self.total_task: typing.Optional[int] = None
        self.caller = caller

    def generate_report(
        self, results: List[speedwagon.tasks.Result]
    ) -> typing.Optional[str]:
        return self.workflow.generate_report(results, **self.options)

    def tasks(self) -> typing.Iterable[speedwagon.tasks.Subtask]:
        pretask_results: List[speedwagon.tasks.Result[Any]] = []

        results = []

        for pre_task in self.get_pre_tasks(self.working_directory):
            yield pre_task
            if pre_task.task_result:
                pretask_results.append(pre_task.task_result)

        if self.caller is not None:
            additional_data = self.caller.request_more_info(
                self.workflow, self.options, pretask_results
            )
        else:
            warnings.warn("No way to request info from user", stacklevel=2)
            additional_data = {}

        for task in self.get_main_tasks(
            self.working_directory,
            pretask_results=pretask_results,
            additional_data=additional_data,
        ):
            yield task
            if task.task_result:
                results.append(task.task_result)

        yield from self.get_post_tasks(
            working_directory=self.working_directory,
            results=results,
        )

    def get_pre_tasks(
        self, working_directory: str
    ) -> typing.Iterable[speedwagon.tasks.Subtask]:
        task_builder = speedwagon.tasks.TaskBuilder(
            speedwagon.tasks.MultiStageTaskBuilder(working_directory),
            working_directory,
        )
        self.workflow.initial_task(
            task_builder=task_builder,
            user_args=self.options
        )
        yield from task_builder.build_task().main_subtasks

    def get_main_tasks(
        self,
        working_directory: str,
        pretask_results,
        additional_data,
    ) -> typing.Iterable[speedwagon.tasks.Subtask]:
        metadata_tasks = (
            self.workflow.discover_task_metadata(
                pretask_results, additional_data, user_args=self.options
            )
            or []
        )

        subtasks_generated = []
        for task_metadata in metadata_tasks:
            task_builder = speedwagon.tasks.TaskBuilder(
                speedwagon.tasks.MultiStageTaskBuilder(working_directory),
                working_directory,
            )
            self.workflow.create_new_task(task_builder, task_metadata)
            subtasks = task_builder.build_task()
            subtasks_generated += subtasks.main_subtasks

        self.current_task = 0
        self.total_task = len(subtasks_generated)
        for task in subtasks_generated:
            self.current_task += 1
            yield task

    def get_post_tasks(
        self,
        working_directory: str,
        results: typing.List[speedwagon.tasks.Result],
    ) -> typing.Iterable[speedwagon.tasks.Subtask]:
        task_builder = speedwagon.tasks.TaskBuilder(
            speedwagon.tasks.MultiStageTaskBuilder(working_directory),
            working_directory,
        )
        self.workflow.completion_task(
            task_builder, results,
            user_args=self.options
        )
        yield from task_builder.build_task().main_subtasks


class AbsTaskDispatcherState(abc.ABC):
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if not hasattr(cls, "state_name"):
            raise NotImplementedError(
                f"{cls.__name__} requires class property 'state_name' to be "
                f"implemented"
            )

    def __init__(self, context: "TaskDispatcher"):
        self.parent = context

    @abc.abstractmethod
    def active(self) -> bool:
        """Get the active status of the task."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop dispatching tasks to run."""

    @abc.abstractmethod
    def start(self) -> None:
        """Star dispatching tasks from the queue to run."""


class TaskDispatcherIdle(AbsTaskDispatcherState):
    state_name = "Idle"

    def active(self) -> bool:
        return False

    def stop(self) -> None:
        """Do nothing.

        Stopping an idle thread is a no-op.
        """

    def start(self) -> None:
        self.parent.current_state = TaskDispatcherRunning(self.parent)
        self.parent.current_state.run_thread()


class TaskDispatcherRunning(AbsTaskDispatcherState):
    state_name = "Running"

    def run_thread(self) -> None:
        logger = logging.getLogger(__name__)

        logger.debug("Starting processing thread")
        self.parent.thread = threading.Thread(
            name="processing_thread",
            target=self.processing_process,
            kwargs={
                "stop_event": self.parent.signals["stop"],
                "job_finished_event": self.parent.signals["finished"],
            },
        )
        self.parent.thread.start()

    def processing_process(
        self, stop_event: threading.Event, job_finished_event: threading.Event
    ) -> None:
        logger = self.parent.logger
        logger.debug("Processing thread is available")

        while not stop_event.is_set():
            if self.parent.job_queue.empty():
                continue

            task = typing.cast(
                speedwagon.tasks.Subtask, self.parent.job_queue.get()
            )

            task_description = task.task_description()
            if task_description is not None:
                logger.info(task_description)

            logger.debug(
                "Threaded worker received task: [%s](%s)",
                task.name,
                task.task_description(),
            )

            self.parent.current_task = task
            task.log = lambda message: logger.info(msg=message)
            task.exec()
            logger.debug("Threaded worker completed task: [%s]", task.name)

            self.parent.job_queue.task_done()
        job_finished_event.set()

    def active(self) -> bool:
        if self.parent.thread is None:
            return False
        return self.parent.thread.is_alive()

    def stop(self) -> None:
        self.parent.current_state = TaskDispatcherStopping(self.parent)
        self.parent.current_state.halt_dispatching()

    def start(self) -> None:
        self.parent.logger.warning("Processing thread is already started")


class TaskDispatcherStopping(AbsTaskDispatcherState):
    state_name = "Stopping"

    def halt_dispatching(self) -> None:
        self.parent.signals["stop"].set()
        if self.parent.thread is not None:
            self.parent.logger.debug("Processing thread is stopping")
            self.parent.thread.join()
        self.parent.logger.debug("Processing thread has stopped")
        self.parent.current_state = TaskDispatcherIdle(self.parent)

    def active(self) -> bool:
        if self.parent.thread is None:
            return False
        return self.parent.thread.is_alive()

    def stop(self) -> None:
        self.parent.logger.warning("Processing thread is currently stopping")

    def start(self) -> None:
        self.parent.logger.warning(
            "Unable to start while processing is stopping"
        )


class TaskDispatcher:
    """Task dispatcher for threading."""

    def __init__(
        self,
        job_queue: queue.Queue,
        logger: typing.Optional[logging.Logger] = None,
    ) -> None:
        """Create a new task dispatcher object."""
        super().__init__()
        self.job_queue = job_queue
        self.signals: typing.Mapping[str, threading.Event] = {
            "stop": threading.Event(),
            "finished": threading.Event(),
        }
        self.thread: typing.Optional[threading.Thread] = None
        self.current_task: Optional[speedwagon.tasks.Subtask] = None
        self.logger = logger or logging.getLogger(__name__)
        self.current_state: AbsTaskDispatcherState = TaskDispatcherIdle(self)

    @property
    def active(self) -> bool:
        """Get if currently active."""
        return self.current_state.active()

    def stop(self) -> None:
        """Stop dispatching tasks."""
        self.current_state.stop()

    def __enter__(self) -> "TaskDispatcher":
        """Start dispatching tasks."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop dispatching tasks on exiting."""
        self.stop()

    def start(self) -> None:
        """Start the task."""
        self.current_state.start()


class AbsTaskGeneratorStrategy(abc.ABC):
    @abc.abstractmethod
    def results(self) -> List[Any]:
        """Results of the job."""

    @abc.abstractmethod
    def clear_results(self) -> None:
        """Clear results."""

    @abc.abstractmethod
    def iterate_tasks(
        self,
        workflow: Workflow,
        options: typing.Mapping[str, Any],
        task_scheduler: TaskScheduler,
    ):
        """Generate and iterate tasks."""

    @abc.abstractmethod
    def generate_report(
        self,
        workflow: Workflow,
        options: typing.Mapping[str, Any],
        results: List[Any],
    ) -> Optional[str]:
        """Generate Text Report."""


class TaskGeneratorStrategy(AbsTaskGeneratorStrategy):
    def __init__(self):
        self._results: List[Any] = []

    def results(self) -> List[Any]:
        return self._results

    def clear_results(self) -> None:
        self._results.clear()

    def generate_report(
        self,
        workflow: Workflow,
        options: typing.Mapping[str, Any],
        results: List[Any],
    ) -> Optional[str]:
        return workflow.generate_report(results, user_args=options)

    def iterate_tasks(
        self,
        workflow: Workflow,
        options: typing.Mapping[str, Any],
        task_scheduler: TaskScheduler,
    ):
        workflow.workflow_options()
        task_generator = TaskGenerator(
            workflow,
            working_directory=task_scheduler.working_directory,
            options=options,
            caller=task_scheduler,
        )
        for task in task_generator.tasks():
            task_scheduler.total_tasks = task_generator.total_task
            yield task
            if task.task_result:
                self._results.append(task.task_result)
            task_scheduler.current_task_progress = task_generator.current_task


class TaskScheduler:
    """Task scheduler."""

    def __init__(self, working_directory: str) -> None:
        """Create a new task scheduler."""
        self.task_generator_strategy: AbsTaskGeneratorStrategy = (
            TaskGeneratorStrategy()
        )

        self.logger = logging.getLogger(__name__)
        self.working_directory = working_directory
        self.reporter: Optional[
            speedwagon.frontend.reporter.RunnerDisplay
        ] = None

        self.current_task_progress: typing.Optional[int] = None
        self.total_tasks: typing.Optional[int] = None
        self._task_queue: "queue.Queue" = queue.Queue(maxsize=1)

        self._request_more_info: typing.Callable[
            [
                Workflow,
                Mapping[str, object],
                List[speedwagon.tasks.Result[Any]],
            ],
            typing.Optional[Mapping[str, Any]]
        ] = lambda *args, **kwargs: None

    @property
    def request_more_info(
        self,
    ) -> typing.Callable[
        [
            Workflow,
            Mapping[str, object],
            List[speedwagon.tasks.Result[Any]],
        ],
        typing.Optional[Mapping[str, Any]]
    ]:
        """Request more info from the user about the task."""
        return self._request_more_info

    @request_more_info.setter
    def request_more_info(
        self,
        value: typing.Callable[
            [
                Workflow,
                Mapping[str, object],
                List[speedwagon.tasks.Result[Any]],
            ],
            typing.Optional[Mapping[str, Any]]
        ],
    ) -> None:
        self._request_more_info = value

    def iter_tasks(
        self, workflow: Workflow, options: Dict[str, Any]
    ) -> typing.Iterable[speedwagon.tasks.Subtask]:
        """Get sub-tasks for a workflow.

        Args:
            workflow: Workflow to run
            options: Options used with workflow

        Yields:
            Yields subtasks for a workflow.

        """
        self.task_generator_strategy.clear_results()
        yield from self.task_generator_strategy.iterate_tasks(
            workflow, options, self
        )

        report = self.task_generator_strategy.generate_report(
            workflow, options, self.task_generator_strategy.results()
        )
        if report:
            self.logger.info(report)

    def run_workflow_jobs(
        self,
        workflow: Workflow,
        options: typing.Dict[str, Any],
        reporter: Optional[speedwagon.frontend.reporter.RunnerDisplay] = None,
    ) -> None:
        """Add job tasks to queue.

        This blocks until the task finished is called.
        """
        for subtask in self.iter_tasks(workflow, options):
            self._task_queue.put(subtask)
            self.logger.debug("Task added to queue: [%s]", subtask.name)

            while self._task_queue.unfinished_tasks > 0:
                if reporter is not None:
                    reporter.refresh()
                    if reporter.user_canceled is True:
                        raise speedwagon.exceptions.JobCancelled(
                            USER_ABORTED_MESSAGE, expected=True
                        )

    def run(self, workflow: Workflow, options: Dict[str, Any]) -> None:
        """Run workflow with given options."""
        task_dispatcher = TaskDispatcher(self._task_queue, self.logger)
        try:
            with task_dispatcher as task_runner:
                if self.reporter is not None:
                    self.reporter.task_runner = task_runner
                    self.reporter.task_scheduler = self
                    with self.reporter as active_reporter:
                        active_reporter.current_task_progress = 0
                        active_reporter.title = workflow.name
                        self.run_workflow_jobs(
                            workflow, options, active_reporter
                        )
                    active_reporter.refresh()
                else:
                    self.run_workflow_jobs(workflow, options)
        finally:
            self._task_queue.join()


class TerminateConsumerThread(Exception):
    pass


@dataclasses.dataclass
class TaskPacket:
    class PacketType(enum.Enum):
        COMMAND = 2
        TASK = 3
        NOOP = 4

    packet_type: "PacketType"
    data: typing.Any
    finished: threading.Condition = threading.Condition()


@dataclasses.dataclass
class JobManagerLiaison:
    callbacks: AbsJobCallbacks
    events: "ThreadedEvents"


class AbsJobManager2(contextlib.AbstractContextManager):
    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(__name__)

    @abc.abstractmethod
    def submit_job(
        self,
        workflow_name: str,
        app: speedwagon.startup.AbsStarter,
        liaison: JobManagerLiaison,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Submit job to worker."""


class Run(TaskScheduler):
    def __init__(self, working_directory: str) -> None:
        super().__init__(working_directory)
        self.valid_workflows = None

    def get_workflow(self, workflow_name: str) -> typing.Type[Workflow]:
        if self.valid_workflows is None:
            workflow_class = speedwagon.job.available_workflows().get(
                workflow_name
            )
        elif workflow_name is None:
            raise AssertionError("workflow_name is not set")
        else:
            workflow_class = self.valid_workflows.get(workflow_name)

        if workflow_class is None:
            raise AssertionError(f"Workflow not found: {workflow_name}")
        return workflow_class


class BackgroundJobManager(AbsJobManager2):
    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._exec: Optional[BaseException] = None
        self.valid_workflows = None
        self._background_thread: Optional[threading.Thread] = None
        self.request_more_info: Callable[
            [
                Workflow[Any],
                Mapping[str, object],
                List[speedwagon.tasks.Result[Any]],
                Optional[threading.Condition]
            ],
            Optional[Mapping[str, Any]]
        ] = lambda *args, **kwargs: None
        self.global_settings: Optional[SettingsData] = None

    def __enter__(self) -> "BackgroundJobManager":
        self._exec = None
        self._background_thread = None
        return self

    def run_job_on_thread(
        self,
        workflow_name: str,
        options: Dict[str, Dict[str, Any]],
        liaison: JobManagerLiaison,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                task_scheduler = Run(tmp_dir)
                task_scheduler.request_more_info = functools.partial(
                    self.request_more_info
                )

                # Makes testing easier
                if self.valid_workflows is not None:
                    task_scheduler.valid_workflows = self.valid_workflows

                workflow = task_scheduler.get_workflow(workflow_name)(
                    global_settings=options.get("global_settings")
                )
                options_backend = speedwagon.config.YAMLWorkflowConfigBackend()
                strategy = speedwagon.config.StandardConfigFileLocator()
                backend_yaml = os.path.join(
                    strategy.get_app_data_dir(),
                    speedwagon.config.WORKFLOWS_SETTINGS_YML_FILE_NAME,
                )
                options_backend.workflow = workflow
                options_backend.yaml_file = backend_yaml
                workflow.set_options_backend(options_backend)
                liaison.events.started.wait()

                for task in task_scheduler.iter_tasks(
                    workflow, options["options"]
                ):
                    if liaison.events.is_stopped() is True:
                        liaison.callbacks.cancelling_complete()
                        break

                    if task.name is not None:
                        liaison.callbacks.status(task.name)

                    self.logger.info(task.task_description())

                    # HACK: pass the task logger
                    task.parent_task_log_q = type(
                        "logger", (object,), {"append": self.logger.info}
                    )

                    task.exec()
                    liaison.callbacks.update_progress(
                        current=task_scheduler.current_task_progress,
                        total=task_scheduler.total_tasks,
                    )
                liaison.callbacks.finished(JobSuccess.SUCCESS)

            except speedwagon.exceptions.JobCancelled as job_cancelled:
                liaison.callbacks.finished(JobSuccess.ABORTED)
                logging.debug("Job canceled: %s", job_cancelled)

            except speedwagon.exceptions.MissingConfiguration as config_error:
                liaison.callbacks.finished(JobSuccess.ABORTED)
                if config_error.key and config_error.workflow:
                    logging.debug(
                        'Unable to start job with missing configurations: '
                        '"%s" from "%s". '
                        '\nCheck the Workflow Settings section in '
                        'Speedwagon settings.',
                        config_error.key, config_error.workflow
                    )
                else:
                    logging.debug(
                        'Unable to start job with missing configurations. '
                        '\nReason: %s'
                        '\nCheck the Workflow Settings section in '
                        'Speedwagon settings.',
                        config_error
                    )
            except BaseException as exception_thrown:
                traceback_info = traceback.format_exc()

                self._exec = exception_thrown

                liaison.callbacks.finished(JobSuccess.FAILURE)
                liaison.callbacks.error(
                    exc=exception_thrown, traceback_string=traceback_info
                )

                raise
            liaison.events.done()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback_: Optional[TracebackType],
    ) -> None:
        self.clean_up_thread()
        if self._exec is not None:
            raise self._exec
        logging.debug("thread threw no exceptions")

    def clean_up_thread(self) -> None:
        if self._background_thread is not None:
            logging.debug("Background thread joined")
            self._background_thread.join()
            self._background_thread = None

    def submit_job(
        self,
        workflow_name: str,
        app: speedwagon.startup.AbsStarter,
        liaison: JobManagerLiaison,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        if (
            self._background_thread is None
            or self._background_thread.is_alive() is False
        ):
            new_thread = threading.Thread(
                target=self.run_job_on_thread,
                kwargs={
                    "workflow_name": workflow_name,
                    "liaison": liaison,
                    "options": {
                        "options": options,
                        "global_settings": self.global_settings,
                    },
                },
            )
            new_thread.start()
            self._background_thread = new_thread
            liaison.callbacks.start()


class ThreadedEvents(AbsEvents):
    def __init__(self) -> None:
        super().__init__()
        self.stopped = threading.Event()
        self.started = threading.Event()
        self._done = threading.Event()

    def done(self) -> None:
        self._done.set()

    def stop(self) -> None:
        self.stopped.set()

    def is_stopped(self) -> bool:
        return self.stopped.is_set()

    def has_started(self) -> bool:
        return self.started.is_set()

    def is_done(self) -> bool:
        return self._done.is_set()


def simple_api_run_workflow(
    workflow: Workflow,
    workflow_options,
    logger: Optional[logging.Logger] = None,
    request_factory: Optional[
        speedwagon.frontend.interaction.UserRequestFactory
    ] = None,
) -> None:
    """Run a workflow and block until finished.

    This is the simplest API for running a workflow.

    Args:
        workflow: Workflow
        workflow_options: dictionary of options
        logger: file stream handle for logging data
        request_factory: factory for generating the user input mid-job
    """
    task_scheduler = speedwagon.runner_strategies.TaskScheduler(".")
    log_handler = None

    if logger is None:
        logger = logging.getLogger()
        log_handler = logging.StreamHandler(stream=sys.stdout)
        logger.addHandler(log_handler)
    try:
        task_scheduler.logger = logger
        logging.StreamHandler(stream=sys.stdout)
        task_scheduler.logger.setLevel(logging.INFO)

        def request_more_info(
            workflow: Workflow[_T],
            options: _T,
            pretask_results: List[speedwagon.tasks.Result[Any]],
        ) -> typing.Optional[Mapping[str, Any]]:
            factory = (
                request_factory
                or speedwagon.frontend.cli.user_interaction.CLIFactory()
            )

            return workflow.get_additional_info(
                factory, options, pretask_results
            )

        task_scheduler.request_more_info = request_more_info
        for task in task_scheduler.iter_tasks(
            workflow=workflow, options=workflow_options
        ):
            task.parent_task_log_q = type(
                "reporter", (object,), {"append": logger.info}
            )
            logger.info("%s\n", task.task_description())
            task.exec()
    finally:
        if log_handler is not None:
            task_scheduler.logger.removeHandler(log_handler)


class WorkflowNullCallbacks(AbsJobCallbacks):
    def error(
        self,
        message: Optional[str] = None,
        exc: Optional[BaseException] = None,
        traceback_string: Optional[str] = None,
    ) -> None:
        """No-op."""

    def status(self, text: str) -> None:
        """No-op."""

    def log(self, text: str, level: int = logging.INFO) -> None:
        """No-op."""

    def cancelling_complete(self) -> None:
        """No-op."""

    def finished(self, result: JobSuccess) -> None:
        """No-op."""
