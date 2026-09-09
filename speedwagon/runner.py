"""Job runners."""

from __future__ import annotations
import abc
import contextlib
import enum
import functools
import queue
import tempfile
import threading
import traceback as tb
import typing
import warnings
from typing import (
    Callable,
    Optional,
    List,
    Collection,
    Iterator,
    Type,
    Dict,
    Any,
    Iterable,
    Mapping,
    Protocol,
    TypeVar
)
from types import TracebackType
import dataclasses
import logging

import speedwagon.tasks

if typing.TYPE_CHECKING:
    from speedwagon.job import Workflow
    from speedwagon.tasks import Result
    from speedwagon.tasks.tasks import BaseTask
    from speedwagon.runner_strategies import JobSubmitConfig

__all__ = [
    "TaskScheduler",
]

USER_ABORTED_MESSAGE = "User Aborted"


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


class TaskDispatcher:
    """Task dispatcher for threading."""

    def __init__(
        self,
        job_queue: queue.Queue,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Create a new task dispatcher object."""
        super().__init__()
        self.job_queue = job_queue
        self.signals: Mapping[str, threading.Event] = {
            "stop": threading.Event(),
            "finished": threading.Event(),
        }
        self.thread: Optional[threading.Thread] = None
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


class AbsEvents(abc.ABC):
    @abc.abstractmethod
    def wait_for_started(self) -> None:
        """Wait for the task to start."""

    @abc.abstractmethod
    def start(self) -> None:
        """Start the task."""

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


class ThreadedEvents(AbsEvents):
    def __init__(self) -> None:
        super().__init__()
        self._stopped = threading.Event()
        self._started = threading.Event()
        self._done = threading.Event()

    def wait_for_started(self) -> None:
        self._started.wait()

    def start(self) -> None:
        self._started.set()

    def done(self) -> None:
        self._done.set()

    def stop(self) -> None:
        self._stopped.set()

    def is_stopped(self) -> bool:
        return self._stopped.is_set()

    def has_started(self) -> bool:
        return self._started.is_set()

    def is_done(self) -> bool:
        return self._done.is_set()


# pylint: disable-next=too-few-public-methods
class LoggingProtocol(typing.Protocol):
    def __call__(self, text: str, level: int = logging.INFO) -> None:
        """Log information."""


# pylint: disable-next=too-few-public-methods
class UpdateProgressProtocol(typing.Protocol):
    def __call__(self, current: Optional[int], total: Optional[int]) -> None:
        """Update progress."""


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
        state = TaskDispatcherStopping(self.parent)
        self.parent.current_state = state
        state.halt_dispatching()

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


class TaskGenerator:
    def __init__(
        self,
        workflow: Workflow,
        options: Mapping[str, Any],
        working_directory: str,
        caller: Optional["TaskScheduler"] = None,
    ) -> None:
        self.workflow = workflow
        self.options = options
        self.working_directory = working_directory
        self.current_task: Optional[int] = None
        self.total_task: Optional[int] = None
        self.caller = caller
        self.waiter: Optional[speedwagon.runner.AbsWaiter] = None

    def generate_report(self, results: List[Result]) -> Optional[str]:
        return self.workflow.generate_report(results, **self.options)

    def tasks(self) -> Iterable[BaseTask]:
        pretask_results: List[Result[Any, Any]] = []

        results = []

        for pre_task in self.get_pre_tasks(self.working_directory):
            yield pre_task
            if pre_task.task_result:
                pretask_results.append(pre_task.task_result)

        if (
            self.caller is not None
            and self.caller.request_more_info is not None
        ):
            additional_data = self.caller.request_more_info(
                self.workflow, self.options, pretask_results, self.waiter
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

    def get_pre_tasks(self, working_directory: str) -> Iterable[BaseTask]:
        task_builder = speedwagon.tasks.TaskBuilder(
            speedwagon.tasks.MultiStageTaskBuilder(working_directory),
            working_directory,
        )
        self.workflow.initial_task(
            task_builder=task_builder, user_args=self.options
        )
        yield from task_builder.build_task().main_subtasks

    def get_main_tasks(
        self,
        working_directory: str,
        pretask_results,
        additional_data,
    ) -> Iterable[BaseTask]:
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
        results: List[Result],
    ) -> Iterable[BaseTask]:
        task_builder = speedwagon.tasks.TaskBuilder(
            speedwagon.tasks.MultiStageTaskBuilder(working_directory),
            working_directory,
        )
        self.workflow.completion_task(
            task_builder, results, user_args=self.options
        )
        yield from task_builder.build_task().main_subtasks


@dataclasses.dataclass
class AsyncCommunication:
    events: AbsEvents
    callbacks: JobRunnerCallbacks


class LoggedSignal(typing.NamedTuple):
    message: str
    level: int = logging.INFO


class JobProgress(typing.NamedTuple):
    current: Optional[int]
    total: Optional[int]


def notify_user_of_config_error(
    log: LoggingProtocol,
    config_error: speedwagon.exceptions.MissingConfiguration,
) -> None:
    log(
        text="Unable to start job with missing configurations. "
             f"{config_error}",
        level=logging.INFO,
    )

    if config_error.key and config_error.workflow:
        log(
            text="Unable to start job with missing configurations: "
                 f'"{config_error.key}" from "'
                 f'{config_error.workflow}". '
                 "\nCheck the Workflow Settings section in "
                 "Speedwagon settings.",
            level=logging.DEBUG,
        )
    else:
        log(
            text="Unable to start job with missing configurations. "
                 f"\nReason: {config_error}"
                 "\nCheck the Workflow Settings section in "
                 "Speedwagon settings.",
            level=logging.DEBUG,
        )


class JobSuccess(enum.IntEnum):
    SUCCESS = 0
    FAILURE = 1
    ABORTED = 2


# pylint: disable-next=too-few-public-methods
class ErrorCallbackProtocol(Protocol):
    def __call__(
        self,
        message: Optional[str] = None,
        exc: Optional[BaseException] = None,
        traceback_string: Optional[str] = None
    ) -> None:
        ...


@dataclasses.dataclass
class JobRunnerCallbacks:
    finished: Callable[[JobSuccess], None]
    error: ErrorCallbackProtocol
    cancelling_complete: Callable[[], None]
    update_progress: UpdateProgressProtocol
    log: LoggingProtocol
    status: Callable[[str], None]


class WorkerLogHandler(logging.Handler):
    def __init__(
        self,
        callback: Callable[[logging.LogRecord], None], level: int = 0
    ) -> None:
        super().__init__(level)
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        self.callback(record)


@contextlib.contextmanager
def attach_logger_handlers(
    logger: Optional[logging.Logger],
    handlers: Collection[logging.Handler],
    level: int = logging.INFO,
) -> Iterator[None]:
    attached_handlers: List[logging.Handler] = []
    try:
        if logger:
            for handler in handlers:
                handler.setLevel(level)
                logger.addHandler(handler)
                attached_handlers.append(handler)
        yield
    finally:
        if logger:
            for handler in attached_handlers:
                logger.removeHandler(handler)


class AbsWaiter(contextlib.AbstractContextManager):
    @abc.abstractmethod
    def wait(self) -> None:
        ...

    @abc.abstractmethod
    def notify(self) -> None:
        ...


class ThreadingWaiter(AbsWaiter):
    def __init__(self) -> None:
        self._waiter = threading.Condition()

    def __enter__(self) -> "ThreadingWaiter":
        self._waiter.__enter__()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType]
    ) -> None:
        self._waiter.__exit__(exc_type, exc_value, traceback)

    def wait(self) -> None:
        self._waiter.wait()

    def notify(self) -> None:
        self._waiter.notify()


_T = TypeVar("_T", bound=Mapping[str, object])


# pylint: disable-next=too-few-public-methods
class RequestMoreInfoProtocol(Protocol):
    def __call__(
        self,
        workflow: Workflow[_T],
        options: _T,
        pretask_results: List[Result[Any, Any]],
        wait_condition: Optional[AbsWaiter] = None,
    ) -> Optional[Mapping[str, Any]]:
        ...


# pylint: disable-next=too-few-public-methods
class WorkflowLoaderProtocol(Protocol):
    def __call__(self) -> Dict[str, Type[Workflow]]:
        ...


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
        options: Mapping[str, Any],
        task_scheduler: TaskScheduler,
    ):
        """Generate and iterate tasks."""

    @abc.abstractmethod
    def generate_report(
        self,
        workflow: Workflow,
        options: Mapping[str, Any],
        results: List[Any],
    ) -> Optional[str]:
        """Generate Text Report."""


class TaskGeneratorStrategy(AbsTaskGeneratorStrategy):
    def __init__(self) -> None:
        self._results: List[Any] = []

    def results(self) -> List[Any]:
        return self._results

    def clear_results(self) -> None:
        self._results.clear()

    def generate_report(
        self,
        workflow: Workflow,
        options: Mapping[str, Any],
        results: List[Any],
    ) -> Optional[str]:
        return workflow.generate_report(results, user_args=options)

    def iterate_tasks(
        self,
        workflow: Workflow,
        options: Mapping[str, Any],
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

    task_generator_strategy: AbsTaskGeneratorStrategy = TaskGeneratorStrategy()

    def __init__(self, working_directory: str) -> None:
        """Create a new task scheduler."""
        self.logger = logging.getLogger(__name__)
        self.working_directory = working_directory
        self.reporter: Optional[speedwagon.frontend.reporter.RunnerDisplay] = (
            None
        )

        self.current_task_progress: Optional[int] = None
        self.total_tasks: Optional[int] = None
        self._task_queue: "queue.Queue" = queue.Queue(maxsize=1)

        self._request_more_info: RequestMoreInfoProtocol = (
            lambda *args, **kwargs: None
        )

    @property
    def request_more_info(
        self,
    ) -> RequestMoreInfoProtocol:
        """Request more info from the user about the task."""
        return self._request_more_info

    @request_more_info.setter
    def request_more_info(
        self,
        value: RequestMoreInfoProtocol,
    ) -> None:
        self._request_more_info = value

    def iter_tasks(
        self, workflow: Workflow, options: Mapping[str, Any]
    ) -> Iterable[speedwagon.tasks.Subtask]:
        """Get sub-tasks for a workflow.

        Args:
            workflow: Workflow to run
            options: Options used with workflow

        Yields:
            Yields subtasks for a workflow.

        """
        # breakpoint()
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
        options: Dict[str, Any],
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


class Run(TaskScheduler):
    def __init__(self, working_directory: str) -> None:
        super().__init__(working_directory)
        self.workflow_loader_strategy: WorkflowLoaderProtocol =\
            speedwagon.job.available_workflows

    def get_workflow(self, workflow_name: str) -> Type[Workflow]:
        if workflow_name is None:
            raise AssertionError("workflow_name is not set")

        workflow_class = self.workflow_loader_strategy().get(workflow_name)
        if workflow_class is None:
            raise AssertionError(f'Workflow not found: "{workflow_name}"')
        return workflow_class


def _get_run_callbacks(
    async_communication: Optional[AsyncCommunication] = None
) -> JobRunnerCallbacks:
    if async_communication:
        return async_communication.callbacks

    logger = logging.Logger(__name__)

    def finished_callback(*_, **__) -> None:
        """This is a no-op."""

    def update_progress_callback(*_, **__) -> None:
        """This is a no-op."""

    def _error_callback(
        logger_: logging.Logger,
        message: Optional[str] = None,
        exc: Optional[BaseException] = None,
        traceback_string: Optional[str] = None
    ) -> None:
        if exc is not None:
            if message:
                logger_.error(message)

            else:
                logger_.error(exc)
            if traceback_string:
                warnings.warn(traceback_string, Warning, stacklevel=2)

    def cancelling_complete():
        """no-op."""

    def _logging_callback(
        logger_: logging.Logger,
        text: str,
        level: int = logging.INFO
    ) -> None:
        logger_.log(level, text)

    logging_callback = functools.partial(_logging_callback, logger)

    return JobRunnerCallbacks(
        finished=finished_callback,
        error=functools.partial(_error_callback, logger),
        cancelling_complete=cancelling_complete,
        update_progress=update_progress_callback,
        log=logging_callback,
        status=logging_callback
    )


def _get_run_events(
    async_communication: Optional[AsyncCommunication]
) -> AbsEvents:
    if async_communication:
        return async_communication.events

    # This is to create a no-op version of AbsEvents.
    # pylint: disable-next=abstract-class-instantiated
    return type(
        "events",
        (AbsEvents,),
        {
            "wait_for_started": lambda *_: None,
            "done": lambda *_: None,
            'is_done': lambda: True,
            'is_stopped': lambda: True,
            'start': lambda: None,
            'stop': lambda: None,
        }
    )()


def run(
    workflow_name: str,
    config: JobSubmitConfig,
    workflow_loader_strategy: WorkflowLoaderProtocol,
    request_more_info_strategy: RequestMoreInfoProtocol,
    async_communication: Optional[AsyncCommunication] = None
) -> None:
    callbacks = _get_run_callbacks(async_communication)
    events = _get_run_events(async_communication)

    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            task_scheduler = Run(tmp_dir)
            task_scheduler.workflow_loader_strategy = workflow_loader_strategy
            task_scheduler.request_more_info = request_more_info_strategy

            workflow = task_scheduler.get_workflow(workflow_name)(
                global_settings=config.global_settings
            )
            workflow.set_options_backend(
                speedwagon.config.workflow.ReadOnlyConfigBackend(
                    config.workflow
                )
            )
            events.wait_for_started()
            for task in task_scheduler.iter_tasks(workflow, config.job):
                if async_communication:
                    if async_communication.events.is_stopped() is True:
                        async_communication.callbacks.cancelling_complete()
                        break

                    if task.name is not None:
                        async_communication.callbacks.status(task.name)

                if description := task.task_description():
                    callbacks.log(text=description)

                # HACK: pass the task logger
                task.parent_task_log_q = type(
                    "logger",
                    (object,),
                    {
                        "append": (
                            lambda msg, log=callbacks.log: log(
                                text=msg
                            )
                        )
                    },
                )
                with attach_logger_handlers(
                    task.logger,
                    [
                            WorkerLogHandler(
                                lambda record: callbacks.log(
                                    text=record.message, level=record.levelno
                                )
                            )
                    ],
                ):
                    task.exec()
                callbacks.update_progress(
                    current=task_scheduler.current_task_progress,
                    total=task_scheduler.total_tasks
                )
            callbacks.finished(JobSuccess.SUCCESS)

        except speedwagon.exceptions.JobCancelled as job_cancelled:
            callbacks.finished(JobSuccess.ABORTED)
            callbacks.log(
                text=f"Job canceled: {job_cancelled}",
                level=logging.DEBUG
            )

        except speedwagon.exceptions.MissingConfiguration as config_error:
            callbacks.finished(JobSuccess.ABORTED)
            notify_user_of_config_error(
                callbacks.log,
                config_error
            )
        except BaseException as exception_thrown:
            traceback_info = tb.format_exc()
            callbacks.error(
                exc=exception_thrown,
                traceback_string=traceback_info
            )
            callbacks.finished(JobSuccess.ABORTED)
            raise
        events.done()
