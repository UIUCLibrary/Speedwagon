"""Consumer of tasks."""
import abc
import concurrent.futures
import contextlib
import logging
import multiprocessing
import queue
import sys
import traceback
import typing
from abc import ABC
from typing import Callable, Optional, Any, Dict
from collections import namedtuple

from PyQt5 import QtWidgets  # type: ignore

from .dialog.dialogs import WorkProgressBar
from .tasks import AbsSubtask, QueueAdapter, Result
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
        except Exception as e:
            print("Failed {}".format(e), file=sys.stderr)
            self.successful = False
            raise

    @abc.abstractmethod
    def process(self, *args, **kwargs) -> None:
        pass

    @abc.abstractmethod
    def log(self, message: str) -> None:
        pass

    def on_completion(self, *args, **kwargs) -> None:
        pass

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


class ProgressMessageBoxLogHandler(logging.Handler):
    """Log handler for progress dialog box."""

    def __init__(self, dialog_box: QtWidgets.QProgressDialog,
                 level: int = logging.NOTSET) -> None:
        """Create a log handler for progress message box."""
        super().__init__(level)
        self.dialog_box = dialog_box

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.dialog_box.setLabelText(self.format(record))
        except RuntimeError as e:
            print(self.format(record), file=sys.stderr)
            traceback.print_tb(e.__traceback__)


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


class GuiLogHandler(logging.Handler):
    def __init__(
            self,
            callback: typing.Callable[[str], None],
            level: int = logging.NOTSET
    ) -> None:
        """Create a gui log handler."""
        super().__init__(level)
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        self.callback(logging.Formatter().format(record))


class WorkRunnerExternal3(contextlib.AbstractContextManager):
    """Work runner that uses external manager."""

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        """Create a work runner."""
        self.results: typing.List[Result] = []
        self._parent = parent
        self.abort_callback: Optional[Callable[[], None]] = None
        self.was_aborted = False
        self.dialog: Optional[WorkProgressBar] = None
        self.progress_dialog_box_handler: \
            Optional[ProgressMessageBoxLogHandler] = None

    def __enter__(self) -> "WorkRunnerExternal3":
        """Start worker."""
        self.dialog = WorkProgressBar(self._parent)
        self.dialog.setLabelText("Initializing")
        self.dialog.setMinimumDuration(100)

        self.progress_dialog_box_handler = \
            ProgressMessageBoxLogHandler(self.dialog)

        self.dialog.canceled.connect(self.abort)
        return self

    def abort(self) -> None:

        if self.dialog is not None and \
                self.dialog.result() == QtWidgets.QProgressDialog.Rejected:
            self.was_aborted = True
            if callable(self.abort_callback):
                self.abort_callback()  # pylint: disable=not-callable

    def __exit__(self, exc_type, exc_value, tb) -> None:
        """Close runner."""
        if self.dialog is None:
            raise AttributeError("dialog was set to None before closing")
        self.dialog.close()


class AbsJobManager(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def add_job(self, new_job, settings) -> None:
        pass

    @abc.abstractmethod
    def start(self) -> None:
        pass

    @abc.abstractmethod
    def flush_message_buffer(self) -> None:
        pass

    @abc.abstractmethod
    def abort(self) -> None:
        pass


class ToolJobManager(contextlib.AbstractContextManager, AbsJobManager):
    """Tool job manager."""

    def __init__(self, max_workers: int = 1) -> None:
        """Create a tool job manager."""
        self.settings_path: Optional[str] = None
        self.manager = multiprocessing.Manager()
        self._max_workers = max_workers
        self.active = False
        self._pending_jobs: queue.Queue[JobPair] = queue.Queue()
        self.futures: typing.List[concurrent.futures.Future] = []
        self.logger = logging.getLogger(__name__)
        self.user_settings: Optional["speedwagon.config.AbsConfig"] = None
        self.configuration_file: Optional[str] = None

    def __enter__(self) -> "ToolJobManager":
        """Startup job management and load a worker pool."""
        self._message_queue = self.manager.Queue()

        self._executor = concurrent.futures.ProcessPoolExecutor(
            self._max_workers
        )

        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Clean up manager and show down the executor."""
        self._cleanup()
        self._executor.shutdown()

    def open(self, parent, runner, *args, **kwargs):
        return runner(*args, **kwargs, parent=parent)

    def add_job(self,
                new_job: ProcessJobWorker,
                settings: Dict[str, Any]) -> None:

        self._pending_jobs.put(JobPair(new_job, settings))

    def start(self) -> None:
        """Start jobs."""
        self.active = True
        while not self._pending_jobs.empty():
            job_, settings = self._pending_jobs.get()
            job_.set_message_queue(self._message_queue)
            fut = self._executor.submit(job_.execute, **settings)

            fut.add_done_callback(fn=lambda x: self._pending_jobs.task_done())
            self.futures.append(fut)

    def abort(self) -> None:
        """Abort jobs."""
        self.active = False
        still_running: typing.List[concurrent.futures.Future] = []

        dialog_box = WorkProgressBar("Canceling", None, 0, 0)

        for future in reversed(self.futures):
            if not future.cancel and future.running():
                still_running.append(future)
            self.futures.remove(future)

        dialog_box.setRange(0, len(still_running))
        dialog_box.setLabelText("Please wait")
        dialog_box.show()
        # TODO: set cancel dialog to force the cancellation of the future

        while True:

            try:
                QtWidgets.QApplication.processEvents()

                futures = concurrent.futures.as_completed(still_running,
                                                          timeout=.1)

                for i, future in enumerate(futures):
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

        total_jobs = len(self.futures)
        completed = 0
        futures = [(i, False) for i in self.futures]
        while self.active:
            try:
                for completed_futures in concurrent.futures.as_completed(
                        self.futures,
                        timeout=0.01):
                    self.flush_message_buffer()
                    if not completed_futures.cancel() and \
                            completed_futures.done():

                        completed += 1
                        self.futures.remove(completed_futures)
                        if timeout_callback:
                            timeout_callback(completed, total_jobs)
                        for i, (future, reported) in enumerate(futures):

                            if not reported and future.done():
                                result = future.result()
                                yield result
                                futures[i] = future, True
                    if timeout_callback:
                        timeout_callback(completed, total_jobs)

                self.active = False
                self.futures.clear()
                self.flush_message_buffer()

            except concurrent.futures.TimeoutError:
                self.flush_message_buffer()
                if timeout_callback:
                    timeout_callback(completed, total_jobs)
                QtWidgets.QApplication.processEvents()
                if self.active:
                    continue
            except concurrent.futures.process.BrokenProcessPool as e:
                traceback.print_tb(e.__traceback__)
                print(e, file=sys.stderr)
                print(completed_futures.exception(), file=sys.stderr)
                raise
            self.flush_message_buffer()

    def flush_message_buffer(self) -> None:
        while not self._message_queue.empty():
            self.logger.info(self._message_queue.get())
            self._message_queue.task_done()

    def _cleanup(self) -> None:
        if self._pending_jobs.unfinished_tasks > 0:
            self.logger.warning("Pending jobs has unfinished tasks")
        self._pending_jobs.join()


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

    def __init__(self, adaptee: AbsSubtask) -> None:
        """Create a sub-task job adapter."""
        AbsJobAdapter.__init__(self, adaptee)
        ProcessJobWorker.__init__(self)
        self.adaptee.parent_task_log_q = QueueAdapter()

    @property
    def queue_adapter(self) -> QueueAdapter:
        return QueueAdapter()

    def process(self, *args, **kwargs) -> None:
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
        return self.adaptee.name
