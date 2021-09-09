"""Consumer of tasks."""
from __future__ import annotations

import abc
import concurrent.futures
import contextlib
import logging
import multiprocessing
import queue
import sys
import traceback
import typing
import warnings
from abc import ABC
from typing import Callable, Optional, Any, Dict, Type
from types import TracebackType
from collections import namedtuple

from PyQt5 import QtWidgets  # type: ignore

from .dialog.dialogs import WorkProgressBar
from .tasks import QueueAdapter
from .tasks.tasks import AbsSubtask, Result

__all__ = [
    "WorkRunnerExternal3",
    "ToolJobManager",
    "SubtaskJobAdapter"
]

if typing.TYPE_CHECKING:
    import speedwagon.config

MessageLog = namedtuple("MessageLog", ("message",))


class NoWorkError(RuntimeError):
    pass


class AbsJobWorker:
    name: typing.Optional[str] = None

    def __init__(self) -> None:
        """Create the base structure for a job worker."""
        self.result = None
        self.successful: typing.Optional[bool] = None

    def execute(self, *args, **kwargs) -> None:
        try:
            self.process(*args, **kwargs)
            self.on_completion(*args, **kwargs)
            self.successful = True
            return self.result
        except Exception as error:
            print("Failed {}".format(error), file=sys.stderr)
            self.successful = False
            raise

    @abc.abstractmethod
    def process(self, *args, **kwargs) -> None:
        pass

    @abc.abstractmethod
    def log(self, message: str) -> None:
        pass

    def on_completion(self, *args, **kwargs) -> None:
        """On completion of main tasks run this.

        Notes:
            Defaults to a no-op.
        """

    @classmethod
    def new(cls, job, message_queue, *args, **kwargs):
        new_job = job()
        new_job.set_message_queue(message_queue)
        new_job.execute(*args, **kwargs)
        return new_job.task_result


class ProcessJobWorker(AbsJobWorker):
    _mq: 'Optional[queue.Queue[str]]' = None

    def process(self, *args, **kwargs) -> None:
        """Process job."""

    def set_message_queue(self, value: 'queue.Queue[str]') -> None:
        """Set message queue."""
        self._mq = value

    def log(self, message: str) -> None:
        """Log message."""
        if self._mq:
            self._mq.put(message)


class JobPair(typing.NamedTuple):
    task: ProcessJobWorker
    args: Dict[str, Any]


class Worker2(metaclass=abc.ABCMeta):
    """Worker."""

    @classmethod
    @abc.abstractmethod
    def initialize_worker(cls) -> None:
        """Initialize the executor."""


class Worker(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def initialize_worker(self) -> None:
        """Initialize the executor."""

    @abc.abstractmethod
    def cancel(self) -> None:
        """Shutdown the executor."""

    @abc.abstractmethod
    def run_all_jobs(self) -> None:
        """Execute jobs in loaded in q."""

    @abc.abstractmethod
    def add_job(self, job: ProcessJobWorker, **job_args) -> None:
        """Load jobs into queue."""


class UIWorker(Worker, ABC):
    def __init__(self, parent) -> None:
        """Interface for managing jobs.

        Designed handle loading and executing jobs.

        Args:
            parent: The widget controlling the worker
        """
        super().__init__()
        self.parent = parent
        self._jobs_queue: queue.Queue[typing.Any] = queue.Queue()


class ProcessWorker(UIWorker):
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=1)

    def __init__(self, *args, **kwargs) -> None:
        """Create a process worker."""
        super().__init__(*args, **kwargs)
        self.manager = multiprocessing.Manager()
        self._message_queue = self.manager.Queue()
        self._results = None
        self._tasks: typing.List[concurrent.futures.Future] = []

    @classmethod
    def initialize_worker(cls, max_workers: int = 1) -> None:

        cls.executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        )  # TODO: Fix this

    def cancel(self) -> None:
        self.executor.shutdown()

    @classmethod
    def _exec_job(cls, job, args, message_queue) -> concurrent.futures.Future:
        new_job = job()
        new_job.mq = message_queue
        fut = cls.executor.submit(new_job.execute, **args)
        return fut

    def add_job(self, job: ProcessJobWorker, **job_args) -> None:
        new_job = JobPair(job, args=job_args)
        self._jobs_queue.put(new_job)

    def run_all_jobs(self) -> None:
        """Run all jobs."""
        while self._jobs_queue.qsize() != 0:
            job_, args, message_queue = self._jobs_queue.get()
            fut = self._exec_job(job_, args, message_queue)
            self._tasks.append(fut)
        for future in concurrent.futures.as_completed(self._tasks):
            self.complete_task(future)
        self.on_completion(results=self._results)

    @abc.abstractmethod
    def complete_task(self, fut: concurrent.futures.Future) -> None:
        pass

    @abc.abstractmethod
    def on_completion(self, *args, **kwargs) -> None:
        """Run the subtask designed to be run after main task."""


# pylint: disable=too-few-public-methods
class AbsObserver(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def emit(self, value) -> None:
        pass
# pylint: enable=too-few-public-methods


class AbsSubject(metaclass=abc.ABCMeta):
    lock = multiprocessing.Lock()
    _observers = set()  # type: typing.Set[AbsObserver]

    def subscribe(self, observer: AbsObserver) -> None:
        if not isinstance(observer, AbsObserver):
            raise TypeError("Observer not derived from AbsObserver")
        self._observers |= {observer}

    def unsubscribe(self, observer: AbsObserver) -> None:
        """Remove observer from getting notifications."""
        self._observers -= {observer}

    def notify(self, value=None):
        """Notify observers of value."""
        with self.lock:
            for observer in self._observers:
                if value is None:
                    observer.emit()
                else:
                    observer.emit(value)


class WorkRunnerExternal3(contextlib.AbstractContextManager):
    """Work runner that uses external manager."""

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
    ) -> None:
        """Create a work runner."""
        self.results: typing.List[Result] = []
        self._parent = parent
        self.abort_callback: Optional[Callable[[], None]] = None
        self.was_aborted = False
        self._dialog: Optional[WorkProgressBar] = None
        # self.progress_dialog_box_handler: \
        #     Optional[ProgressMessageBoxLogHandler] = None

    @property
    def dialog(self) -> Optional[WorkProgressBar]:
        warnings.warn("Don't use the dialog", DeprecationWarning)
        return self._dialog

    @dialog.setter
    def dialog(self, value: Optional[WorkProgressBar]) -> None:
        self._dialog = value

    def __enter__(self) -> "WorkRunnerExternal3":
        """Start worker."""
        self.dialog = WorkProgressBar(self._parent)
        self.dialog.close()
        return self

    def abort(self) -> None:
        """Abort on any running tasks."""
        self.was_aborted = True
        if callable(self.abort_callback):
            self.abort_callback()  # pylint: disable=not-callable

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_value: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None:
        """Close runner."""
        if self.dialog is None:
            raise AttributeError("dialog was set to None before closing")

        self.dialog.close()


class AbsJobManager(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def add_job(self,
                new_job: ProcessJobWorker,
                settings: Dict[str, Any]) -> None:
        """Add job to pending queue."""

    @abc.abstractmethod
    def start(self) -> None:
        """Start job manager."""

    @abc.abstractmethod
    def flush_message_buffer(self) -> None:
        """Flush message buffer."""

    @abc.abstractmethod
    def abort(self) -> None:
        """Abort jobs."""


class JobExecutor:
    def __init__(self) -> None:
        self.manager = multiprocessing.Manager()
        self._pending_jobs: "queue.Queue[JobPair]" = queue.Queue()
        self._message_queue: "Optional[queue.Queue[Any]]" = None
        self._executor: Optional[concurrent.futures.ProcessPoolExecutor] = None
        self.futures: typing.List[concurrent.futures.Future] = []
        self.active = False

    def add_job(self,
                new_job: ProcessJobWorker,
                settings: Dict[str, Any]) -> None:

        self._pending_jobs.put(JobPair(new_job, settings))

    def start(self) -> None:
        """Start jobs."""
        if self._pending_jobs is None or self._executor is None:
            return

        self.active = True
        while not self._pending_jobs.empty():
            job_, settings = self._pending_jobs.get()
            if self._message_queue is not None:
                job_.set_message_queue(self._message_queue)
            fut = self._executor.submit(job_.execute, **settings)

            fut.add_done_callback(fn=lambda x: self._pending_jobs.task_done())
            self.futures.append(fut)

    def abort(self) -> None:
        """Abort jobs."""
        self.active = False
        still_running: typing.List[concurrent.futures.Future] = []

        for future in reversed(self.futures):
            if not future.cancel and future.running():
                still_running.append(future)
            self.futures.remove(future)

    def flush_message_buffer(self, logger: logging.Logger) -> None:
        if self._message_queue is None:
            return
        while not self._message_queue.empty():
            logger.info(self._message_queue.get())
            self._message_queue.task_done()

    def cleanup(self, logger: logging.Logger) -> None:
        if self._pending_jobs.unfinished_tasks > 0:
            logger.warning("Pending jobs has unfinished tasks")
        self._pending_jobs.join()

    def shutdown(self) -> None:
        if self._executor is not None:
            self._executor.shutdown()


class ToolJobManager(contextlib.AbstractContextManager, AbsJobManager):
    """Tool job manager."""

    def __init__(self) -> None:
        """Create a tool job manager."""
        self.settings_path: Optional[str] = None
        self._job_runtime = JobExecutor()
        self.logger = logging.getLogger(__name__)
        self.user_settings: Optional["speedwagon.config.AbsConfig"] = None
        self.configuration_file: Optional[str] = None

    @property
    def active(self) -> bool:
        """Check if a job is active."""
        return self._job_runtime.active

    @active.setter
    def active(self, value: bool) -> None:
        warnings.warn("don't use directly", DeprecationWarning)
        self._job_runtime.active = value

    @property
    def futures(self) -> typing.List[concurrent.futures.Future]:
        """Get the futures."""
        return self._job_runtime.futures

    def __enter__(self) -> "ToolJobManager":
        """Startup job management and load a worker pool."""
        self._job_runtime._message_queue = self._job_runtime.manager.Queue()

        self._job_runtime._executor = concurrent.futures.ProcessPoolExecutor(1)

        return self

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_value: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None:
        """Clean up manager and show down the executor."""
        self._job_runtime.cleanup(self.logger)
        self._job_runtime.shutdown()

    def open(self, parent, runner, *args, **kwargs):
        """Open a runner with the a given job arguments."""
        return runner(*args, **kwargs, parent=parent)

    def add_job(self,
                new_job: ProcessJobWorker,
                settings: Dict[str, Any]) -> None:
        """Add job to the run queue."""
        self._job_runtime.add_job(new_job, settings)

    def start(self) -> None:
        """Start jobs."""
        self._job_runtime.start()

    def abort(self) -> None:
        """Abort jobs."""
        still_running: typing.List[concurrent.futures.Future] = []

        dialog_box = WorkProgressBar("Canceling", None, 0, 0)
        self._job_runtime.abort()

        dialog_box.setRange(0, len(still_running))
        dialog_box.setLabelText("Please wait")
        dialog_box.show()
        # TODO: set cancel dialog to force the cancellation of the future

        while True:

            try:
                QtWidgets.QApplication.processEvents()

                futures = concurrent.futures.as_completed(still_running,
                                                          timeout=.1)

                for i, _ in enumerate(futures):
                    dialog_box.setValue(i + 1)

                break
            except concurrent.futures.TimeoutError:
                continue

        self.logger.info("Cancelled")
        self.flush_message_buffer()
        dialog_box.accept()

    # TODO: refactor to use an overloaded method instead of a callback
    def get_results(self,
                    timeout_callback: Callable[[int, int], None] = None
                    ) -> typing.Generator[typing.Any, None, None]:
        """Process jobs and return results."""
        processor = JobProcessor(self)
        processor.timeout_callback = timeout_callback
        yield from processor.process()

    def flush_message_buffer(self) -> None:
        """Flush any messages in the buffer to the logger."""
        self._job_runtime.flush_message_buffer(self.logger)

    def _cleanup(self) -> None:
        self._job_runtime.cleanup(self.logger)


class JobProcessor:
    def __init__(self, parent: "ToolJobManager"):
        self._parent = parent
        self.completed = 0
        self._total_jobs = None
        self.timeout_callback: Optional[Callable[[int, int], None]] = None

    @staticmethod
    def report_results_from_future(futures):
        for i, (future, reported) in enumerate(futures):

            if not reported and future.done():
                result = future.result()
                yield result
                futures[i] = future, True

    def process(self):
        self._total_jobs = len(self._parent.futures)
        total_jobs = self._total_jobs
        futures = [(i, False) for i in self._parent.futures]

        while self._parent.active:
            try:
                yield from self._process_all_futures(futures)

                self._parent.active = False
                futures.clear()
                self._parent.flush_message_buffer()

            except concurrent.futures.TimeoutError:
                self._parent.flush_message_buffer()
                if callable(self.timeout_callback):
                    self.timeout_callback(self.completed, total_jobs)
                QtWidgets.QApplication.processEvents()
                if self._parent.active:
                    continue
            except concurrent.futures.process.BrokenProcessPool as error:
                traceback.print_tb(error.__traceback__)
                print(error, file=sys.stderr)
                raise
            self._parent.flush_message_buffer()

    def _process_all_futures(self, futures):
        for completed_futures in concurrent.futures.as_completed(
                self._parent.futures,
                timeout=0.01):
            self._parent.flush_message_buffer()
            if not completed_futures.cancel() and \
                    completed_futures.done():
                self.completed += 1
                if completed_futures in self._parent.futures:
                    self._parent.futures.remove(completed_futures)
                if self.timeout_callback:
                    self.timeout_callback(self.completed, self._total_jobs)
                yield from self.report_results_from_future(futures)

            if self.timeout_callback:
                self.timeout_callback(self.completed, self._total_jobs)


class AbsJobAdapter(metaclass=abc.ABCMeta):
    """Job adapter abstract base class."""

    def __init__(self, adaptee) -> None:
        """Create the base structure for a job adapter class."""
        self._adaptee = adaptee

    @property
    def adaptee(self):
        """Get the adaptee."""
        return self._adaptee

    @abc.abstractmethod
    def process(self, *args, **kwargs) -> None:
        """Process the adapter."""

    @abc.abstractmethod
    def set_message_queue(self, value) -> None:
        """Set the message queue used by the job."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass


class SubtaskJobAdapter(AbsJobAdapter,
                        ProcessJobWorker):
    """Adapter class for jobs."""

    def __init__(self, adaptee: AbsSubtask) -> None:
        """Create a sub-task job adapter."""
        AbsJobAdapter.__init__(self, adaptee)
        ProcessJobWorker.__init__(self)
        self.adaptee.parent_task_log_q = QueueAdapter()

    @property
    def queue_adapter(self) -> QueueAdapter:
        """Get the Queue adapter."""
        return QueueAdapter()

    def process(self, *args, **kwargs) -> None:
        """Process the jobs."""
        self.adaptee.exec()
        self.result = self.adaptee.task_result

    def set_message_queue(self, value: 'queue.Queue[str]') -> None:
        """Set message queue."""
        self.adaptee.parent_task_log_q.set_message_queue(value)

    @property
    def settings(self) -> typing.Dict[str, str]:
        """Get the settings for the subtask."""
        if self.adaptee.settings:
            return self.adaptee.settings
        return {key: value for key, value in self.adaptee.__dict__.items()
                if key != "parent_task_log_q"}

    @property
    def name(self) -> str:  # type: ignore
        """Get name of adaptee."""
        return self.adaptee.name
