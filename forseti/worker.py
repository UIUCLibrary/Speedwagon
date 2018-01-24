import concurrent.futures

# from abc import ABCMeta, abstractmethod
import logging
import queue
import typing
import abc
import sys
import warnings
from abc import abstractmethod, ABCMeta

from PyQt5 import QtCore, QtWidgets
from collections import namedtuple
import multiprocessing

PROCESS_LOGGING_REFRESH_RATE = 100

JobPair = namedtuple("JobPair", ("job", "args", "message_queue"))

MessageLog = namedtuple("MessageLog", ("message",))

class QtMeta(type(QtCore.QObject), abc.ABCMeta):  # type: ignore
    pass


class NoWorkError(RuntimeError):
    pass


class AbsJob(metaclass=QtMeta):

    def __init__(self):
        self.result = None

    def execute(self, *args, **kwargs):
        try:
            self.process(*args, **kwargs)
            self.on_completion(*args, **kwargs)
            return self.result
        except Exception as e:
            print("Failed {}".format(e))
            return None

    @abc.abstractmethod
    def process(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def log(self, message):
        pass

    def on_completion(self, *args, **kwargs):
        pass


class ProcessJob(AbsJob):

    def __init__(self):
        super().__init__()
        self._mq = None

    def process(self, *args, **kwargs):
        pass

    def set_message_queue(self, value):
        self._mq = value

    def log(self, message):
        if self._mq:
            self._mq.put(message)


class WorkerMeta(type(QtCore.QObject), ABCMeta):  # type: ignore
    pass


class Worker(QtCore.QObject, metaclass=WorkerMeta):
    def __init__(self, parent):
        """Interface for managing jobs. Designed handle loading and executing jobs.

        Args:
            parent: The widget controlling the worker
        """
        super().__init__()
        self.parent = parent
        self._jobs_queue = queue.Queue()

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


class ProcessWorker(Worker):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.results = None
        self.manager = multiprocessing.Manager()
        self._message_queue = self.manager.Queue()

    def initialize_worker(self, max_workers=1):
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)  # TODO: Fix this

    def cancel(self):
        if hasattr(self, "executor"):
            self.executor.shutdown()
            # TODO: emit a cancel signal

    def _exec_job(self, job, args, message_queue):
        new_job = job()
        new_job.set_message_queue(message_queue)
        fut = self.executor.submit(new_job.execute, **args)
        fut.add_done_callback(self.complete_task)
        self._tasks.append(fut)

    def add_job(self, job: typing.Type[ProcessJob], **job_args):
        new_job = JobPair(job, args=job_args, message_queue=self._message_queue)
        self._jobs_queue.put(new_job)

    def run_all_jobs(self):
        while self._jobs_queue.qsize() != 0:
            job, args, message_queue = self._jobs_queue.get()
            self._exec_job(job, args, message_queue)
            self._jobs_queue.task_done()


class WorkProgressBar(QtWidgets.QProgressDialog):

    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)


class ProgressMessageBoxLogHandler(logging.Handler):

    def __init__(self, dialog_box: QtWidgets.QProgressDialog, level=logging.NOTSET) -> None:
        super().__init__(level)
        self.dialog_box = dialog_box

    def emit(self, record):
        self.dialog_box.setLabelText(record.msg)


class _WorkManager(ProcessWorker):
    finished = QtCore.pyqtSignal(object)
    _complete_task = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self._tasks = []
        self._results = []

        # self._log_manager = LogManager()
        self.process_logger = logging.getLogger(__name__)
        self.process_logger.setLevel(logging.DEBUG)

        self.progress_window = WorkProgressBar(parent)

        self.progress_window.canceled.connect(self.cancel)

        # Don't let the user play with the main interface while the program is doing work
        self.progress_window.setModal(True)

        # Update the label to let the user know what is currently being worked on
        # self._reporter = SimpleCallbackReporter(self.progress_window.setLabelText)
        self.process_logger.addHandler(ProgressMessageBoxLogHandler(self.progress_window))

        # Update the log information
        self.t = QtCore.QTimer(self)
        self.t.timeout.connect(self._update_log)
        self.t.start(PROCESS_LOGGING_REFRESH_RATE)

        self._complete_task.connect(self._advance)


    def _advance(self):
        value = self.progress_window.value()
        self.progress_window.setValue(value + 1)

    def run(self):
        try:
            # self.log_manager.subscribe(self.reporter)
            if self._jobs_queue.qsize() > 0:
                self.initialize_worker()
                self.progress_window.setRange(0, self._jobs_queue.qsize())
                self.progress_window.setValue(0)
                self.run_all_jobs()
                # self.run_jobs(self._jobs)
                self.progress_window.show()

            else:
                raise NoWorkError("No Jobs found")
        except Exception as e:
            print(e)
            self.progress_window.cancel()
            raise

    def cancel(self, quiet=False):
        self.progress_window.setAutoClose(False)
        self.progress_window.canceled.disconnect(self.cancel)
        self._message_queue.put("Called cancel")
        for task in reversed(self._tasks):
            if not task.done():
                task.cancel()
        self.t.stop()
        super().cancel()

        self.progress_window.close()
        if not quiet:
            QtWidgets.QMessageBox.about(self.progress_window, "Canceled", "Successfully Canceled")

    def _update_log(self):
        while not self._message_queue.empty():
            log = self._message_queue.get()
            # self.log_manager.notify(log)
            self.process_logger.info(log)

    def on_completion(self, *args, **kwargs):
        # print(self._results)
        self.finished.emit(self._results)
        self._message_queue.put("Finished")


class WorkManager2(_WorkManager):
    finished = QtCore.pyqtSignal(object, object)
    failed = QtCore.pyqtSignal(Exception)

    def complete_task(self, fut: concurrent.futures.Future):
        if fut.done():
            # ex = fut.exception()
            # if ex:
            #     raise ex
                # return

            if not fut.cancelled():
                try:
                    result = fut.result()
                    if result:
                        self._results.append(result)
                except Exception as e:
                    print(e)

                    if self.progress_window.isActiveWindow():
                        self.progress_window.cancel()
                    # self.cancel(True)
                    self.failed.emit(e)
                    raise
                    # return
                    # self.on_failure(e)

                    # return
                    # raise

            self._complete_task.emit()

            # check if there are more tasks to do.
            for f in self._tasks:
                if not f.done():
                    break

            # If all tasks are on_success, run the on completion method
            else:

                # Flush the log buffer before running on_completion
                self._update_log()
                # self.log_manager.

                self.on_completion(results=self._results)

    def on_completion(self, *args, **kwargs):
        self._jobs_queue.join()
        self.finished.emit(self._results, self.completion_callback)
        # super().on_completion(*args, **kwargs)
    #
    # def on_failure(self, reason):
    #     msg = "Failed, {}".format(reason)
    #     print(msg)
    #     self._message_queue.put(msg)
    #     self.failed.emit(msg)

    def __init__(self, parent):
        super().__init__(parent)
        self.completion_callback: callable = None



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


class LogManager(AbsSubject):
    def __init__(self) -> None:
        super().__init__()
        warnings.warn("Use default logging instead", DeprecationWarning)

    # def __init__(self, message_queue_):
    #     self.message_queue_ = message_queue_

    def add_reporter(self, reporter):
        self.subscribe(reporter)


class SimpleCallbackReporter(AbsObserver):
    def __init__(self, update_callback):
        warnings.warn("Don't use", DeprecationWarning)
        self._callback = update_callback

    def emit(self, value):
        self._callback(value)


class StdoutReporter(AbsObserver):
    def emit(self, value):
        print(value, file=sys.stderr)


class GuiLogger(logging.Handler):
    def __init__(self, callback, level=logging.NOTSET):
        super().__init__(level)
        self.callback = callback

    def emit(self, record):
        self.callback(record.msg)