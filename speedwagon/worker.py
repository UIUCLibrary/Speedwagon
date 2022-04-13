"""Consumer of tasks."""
from __future__ import annotations

import abc
import concurrent.futures
import logging
import multiprocessing
import queue
import sys
import typing
from typing import Optional, Any, Dict
from collections import namedtuple

from speedwagon.tasks import QueueAdapter
if typing.TYPE_CHECKING:
    from speedwagon.tasks.tasks import AbsSubtask

__all__ = [
    "SubtaskJobAdapter"
]

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
            print(f"Failed {error}", file=sys.stderr)
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


# pylint: disable=too-few-public-methods
class AbsObserver(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def emit(self, value) -> None:
        pass


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
