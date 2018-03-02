import concurrent.futures

import forseti.tools
# from abc import ABCMeta, abstractmethod
import contextlib
import logging
import queue
import typing
import abc
import sys
from abc import abstractmethod, ABCMeta
from PyQt5 import QtCore, QtWidgets
from collections import namedtuple
import multiprocessing

MessageLog = namedtuple("MessageLog", ("message",))


class QtMeta(type(QtCore.QObject), abc.ABCMeta):  # type: ignore
    pass


class NoWorkError(RuntimeError):
    pass


class AbsJob(metaclass=QtMeta):

    def __init__(self):
        self.result = None
        self.successful = None

    def execute(self, *args, **kwargs):
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
    def process(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def log(self, message):
        pass

    def on_completion(self, *args, **kwargs):
        pass

    @classmethod
    def new(cls, job, message_queue, *args, **kwargs):
        new_job = job()
        new_job.set_message_queue(message_queue)
        new_job.execute(*args, **kwargs)
        return new_job.result
        # print(logger_queue)
        # print(task)
        # print("HERER")


class ProcessJob(AbsJob):
    mq = None

    def __init__(self):
        super().__init__()

    #     # self._mq = None

    def process(self, *args, **kwargs):
        pass

    # @classmethod
    def set_message_queue(self, value):
        pass
        self._mq = value
        # cls.mq = value

    def log(self, message):
        if self.mq:
            self.mq.put(message)


class JobPair(typing.NamedTuple):
    task: ProcessJob
    args: dict


class WorkerMeta(type(QtCore.QObject), ABCMeta):  # type: ignore
    pass


class Worker2(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def initialize_worker(cls) -> None:
        """Initialize the executor"""
        pass


class Worker(metaclass=ABCMeta):
    @abstractmethod
    def initialize_worker(self) -> None:
        """Initialize the executor"""
        pass

    @abstractmethod
    def cancel(self) -> None:
        """Shutdown the executor"""
        pass

    @abstractmethod
    def run_all_jobs(self):
        """Execute jobs in loaded in q"""
        pass

    @abstractmethod
    def add_job(self, job: typing.Type[ProcessJob], **job_args):
        """Load jobs into queue"""
        pass


class UIWorker(Worker):
    # class Worker(QtCore.QObject, metaclass=WorkerMeta):
    def __init__(self, parent):
        """Interface for managing jobs. Designed handle loading and executing jobs.

        Args:
            parent: The widget controlling the worker
        """
        super().__init__()
        self.parent = parent
        self._jobs_queue = queue.Queue()


# class ProcessWorker(Worker):
class ProcessWorker(UIWorker, QtCore.QObject, metaclass=WorkerMeta):
    # _message_queue = manager.Queue(maxsize=100)
    # _message_queue = queue.Queue()  # type: ignore
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = multiprocessing.Manager()
        self._message_queue = self.manager.Queue()  # type: ignore
        self._results = None
        # self.manager = multiprocessing.Manager()
        self._tasks = []
        # self.executor = None
        # self._message_queue = self.manager.Queue(maxsize=1)

    @classmethod
    def initialize_worker(cls, max_workers=1):

        # self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)  # TODO: Fix this
        cls.executor = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)  # TODO: Fix this
        # self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)  # TODO: Fix this

    def cancel(self):
        # if hasattr(self, "executor"):
        self.executor.shutdown()

    @classmethod
    def _exec_job(cls, job, args, message_queue):
        new_job = job()
        # new_job.set_message_queue(logger_queue)
        new_job.mq = message_queue
        fut = cls.executor.submit(new_job.execute, **args)

        # fut.add_done_callback(self.complete_task)
        return fut

    def add_job(self, job: typing.Type[ProcessJob], **job_args):
        new_job = JobPair(job, args=job_args)
        self._jobs_queue.put(new_job)

    def run_all_jobs(self):

        while self._jobs_queue.qsize() != 0:
            job, args, message_queue = self._jobs_queue.get()
            fut = self._exec_job(job, args, message_queue)
            self._tasks.append(fut)
        # logging.debug("All jobs have been launched")
        for future in concurrent.futures.as_completed(self._tasks):
            # logging.debug("future finished")
            self.complete_task(future)
        self.on_completion(results=self._results)

    @abstractmethod
    def complete_task(self, fut: concurrent.futures.Future):
        pass

    @abstractmethod
    def on_completion(self, *args, **kwargs):
        pass


class WorkProgressBar(QtWidgets.QProgressDialog):

    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)

    def __init__(self, *__args):
        super().__init__(*__args)


class ProgressMessageBoxLogHandler(logging.Handler):

    def __init__(self, dialog_box: QtWidgets.QProgressDialog, level=logging.NOTSET) -> None:
        super().__init__(level)
        self.dialog_box = dialog_box

    def emit(self, record):
        self.dialog_box.setLabelText(record.msg)


class AbsObserver(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def emit(self, value):
        pass


class AbsSubject(metaclass=abc.ABCMeta):
    lock = multiprocessing.Lock()
    _observers = set()  # type: typing.Set[AbsObserver]

    def subscribe(self, observer: AbsObserver):
        if not isinstance(observer, AbsObserver):
            raise TypeError("Observer not derived from AbsObserver")
        self._observers |= {observer}

    def unsubscribe(self, observer: AbsObserver):
        self._observers -= {observer}

    def notify(self, value=None):
        with self.lock:
            for observer in self._observers:
                if value is None:
                    observer.emit()
                else:
                    observer.emit(value)


class GuiLogHandler(logging.Handler):
    def __init__(self, callback, level=logging.NOTSET):
        super().__init__(level)
        self.callback = callback

    def emit(self, record):
        self.callback(record.msg)


class WorkRunnerExternal2(contextlib.AbstractContextManager):
    def __init__(self, tool, options, parent):
        self.results = []
        self._tool = tool
        self._options = options
        self._parent = parent
        self.abort_callback = None
        # self.jobs: queue.Queue[JobPair] = queue.Queue()

    def __enter__(self):
        self.dialog = QtWidgets.QProgressDialog(self._parent)
        self.dialog.setModal(True)
        self.dialog.setLabelText("Initializing")
        self.dialog.setWindowTitle(self._tool.name)
        self.progress_dialog_box_handler = ProgressMessageBoxLogHandler(self.dialog)
        self.dialog.canceled.connect(self.abort)
        return self

    def abort(self):
        if self.abort_callback is not None:
            self.abort_callback()

    def __exit__(self, exc_type, exc_value, traceback):
        self.dialog.hide()


class ToolJobManager(contextlib.AbstractContextManager):

    def __init__(self, max_workers=1) -> None:
        self.manager = multiprocessing.Manager()
        self._max_workers = max_workers
        self.active = False
        self._pending_jobs: queue.Queue[forseti.tools.AbsTool] = queue.Queue()
        self.futures: typing.List[concurrent.futures.Future] = []
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        self._message_queue = self.manager.Queue()
        self._executor = concurrent.futures.ProcessPoolExecutor(self._max_workers)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._executor.shutdown()

    def open(self, options, tool, parent):
        return WorkRunnerExternal2(tool=tool, options=options, parent=parent)

    def add_job(self, job: ProcessJob, settings: dict) -> None:

        self._pending_jobs.put(JobPair(job, settings))

    def start(self):
        self.active = True
        while not self._pending_jobs.empty():
            job, settings = self._pending_jobs.get()
            # job_type = tool
            # job = job_type()
            job.mq = self._message_queue
            fut = self._executor.submit(job.execute, **settings)
            self.futures.append(fut)

    def abort(self):
        self.active = False
        still_running = []

        dialog = QtWidgets.QProgressDialog()
        dialog.setWindowTitle("Canceling")
        dialog.setModal(True)

        # while not self._pending_jobs.empty():
        #     self._pending_jobs.task_done()

        for future in reversed(self.futures):
            if not future.cancel():
                if future.running():
                    still_running.append(future)
            self.futures.remove(future)

        dialog.setRange(0, len(still_running))
        dialog.setWindowTitle("Canceling")
        dialog.setLabelText("Please wait")
        dialog.show()
        # TODO: set cancel dialog to force the cancellation of the future

        while True:
            try:
                QtWidgets.QApplication.processEvents()
                for i, future in enumerate(concurrent.futures.as_completed(still_running, timeout=.1)):
                    dialog.setValue(i + 1)

                break
            except concurrent.futures.TimeoutError:
                continue
        self.logger.info("Cancelled")
        self.flush_message_buffer()
        dialog.accept()

    def get_results(self, timeout_callback=None) -> typing.Iterable[typing.Any]:
        total_jobs = len(self.futures)
        completed = 0
        while self.active:
            try:
                for f in concurrent.futures.as_completed(self.futures, timeout=0.01):
                    if not f.cancelled():
                        result = f.result()
                        self.futures.remove(f)
                        completed += 1
                        self._pending_jobs.task_done()
                        self.flush_message_buffer()
                        if timeout_callback:
                            timeout_callback(completed, total_jobs)
                        yield result

                if timeout_callback:
                    timeout_callback(completed, total_jobs)

                self.active = False
                self.futures.clear()
                self.flush_message_buffer()

            except concurrent.futures.TimeoutError:
                self.flush_message_buffer()

                if timeout_callback:
                    # completed = [f for f in self.futures if f.done()]
                    timeout_callback(completed, total_jobs)
                QtWidgets.QApplication.processEvents()
                continue
        self.flush_message_buffer()
        # return results

    def flush_message_buffer(self):
        while not self._message_queue.empty():
            self.logger.info(self._message_queue.get())
            self._message_queue.task_done()
