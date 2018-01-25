import concurrent.futures

# from abc import ABCMeta, abstractmethod
import contextlib
import logging
import queue
import typing
import abc
import sys
import warnings
from abc import abstractmethod, ABCMeta

from PyQt5 import QtCore, QtWidgets, QtGui
from collections import namedtuple
import multiprocessing

PROCESS_LOGGING_REFRESH_RATE = 200

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
        self._tasks = []
        self._message_queue = self.manager.Queue()

    def initialize_worker(self, max_workers=1):
        logging.debug("Setting up the executer")
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)  # TODO: Fix this

    def cancel(self):
        if hasattr(self, "executor"):
            self.executor.shutdown()
            # TODO: emit a cancel signal

    def _exec_job(self, job, args, message_queue):
        new_job = job()
        new_job.set_message_queue(message_queue)
        fut = self.executor.submit(new_job.execute, **args)

        # FIXME: What class is complete_task from???
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

    def __init__(self, *__args):
        super().__init__(*__args)
        print("NEW ONE")


class ProgressMessageBoxLogHandler(logging.Handler):

    def __init__(self, dialog_box: QtWidgets.QProgressDialog, level=logging.NOTSET) -> None:
        super().__init__(level)
        self.dialog_box = dialog_box

    def emit(self, record):
        self.dialog_box.setLabelText(record.msg)


class MessageRefresher(contextlib.AbstractContextManager):

    def __init__(self, callback, rate=20, parent=None) -> None:
        self._timer = QtCore.QTimer(parent)
        self._rate = rate
        self.callback = callback
        # super().__init__()

    def __enter__(self):
        print("entering")
        self._timer.timeout.connect(self.callback)
        self._timer.start(self._rate)
        return self
        # return super().__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        print("Exiting")
        self._timer.timeout.disconnect(self.callback)
        super().__exit__(exc_type, exc_value, traceback)


class WorkManager(ProcessWorker):
    _complete_task = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(object, object)
    failed = QtCore.pyqtSignal(Exception)

    def __init__(self, parent):
        super().__init__(parent)

        self._results = []

        # Update the log information

        # self._log_manager = LogManager()
        self.process_logger = logging.getLogger(__name__)
        self.process_logger.setLevel(logging.DEBUG)

        self.completion_callback: callable = None

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
                    self.failed.emit(e)
                    raise
            # logging.debug("Completed task")
            self._complete_task.emit()

            # check if there are more tasks to do.
            for f in self._tasks:
                if not f.done():
                    break

            # If all tasks are on_success, run the on completion method
            else:

                # Flush the log buffer before running on_completion
                # self._update_log()

                # self.log_manager.

                self.on_completion(results=self._results)

    def on_completion(self, *args, **kwargs):
        self._jobs_queue.join()
        self.finished.emit(self._results, self.completion_callback)
        # self.t.stop()
        # super().on_completion(*args, **kwargs)

    #
    # def on_failure(self, reason):
    #     msg = "Failed, {}".format(reason)
    #     print(msg)
    #     self._message_queue.put(msg)
    #     self.failed.emit(msg)

    # # TODO: Rename run() method to start() since it's non blocking
    # def run(self):
    #     t = QtCore.QTimer(self)
    #     t.timeout.connect(self._update_log)
    #     t.start(PROCESS_LOGGING_REFRESH_RATE)
    #     try:
    #         # self.log_manager.subscribe(self.reporter)
    #         if self._jobs_queue.qsize() > 0:
    #             self.initialize_worker()
    #             self.progress_window.setRange(0, self._jobs_queue.qsize())
    #             self.progress_window.setValue(0)
    #             self.run_all_jobs()
    #             # self.run_jobs(self._jobs)
    #             self.progress_window.show()
    #
    #         else:
    #             raise NoWorkError("No Jobs found")
    #     except Exception as e:
    #         print(e)
    #         self.progress_window.cancel()
    #         raise
    #     finally:
    #         t.timeout.disconnect(self._update_log)
    #         t.stop()
    #     self.t.stop()
    def cancel(self, quiet=False):
        # self.progress_window.setAutoClose(False)
        # self.progress_window.canceled.disconnect(self.cancel)
        self._message_queue.put("Called cancel")
        for task in reversed(self._tasks):
            if not task.done():
                task.cancel()
        super().cancel()

        # self.progress_window.close()
        # if not quiet:
        #     QtWidgets.QMessageBox.about(self.progress_window, "Canceled", "Successfully Canceled")

    def _update_log(self):
        print("Updating log with a size of {}".format(self._message_queue.qsize()))
        while not self._message_queue.empty():
            # print(self._message_queue.qsize())
            log = self._message_queue.get()
            # self.log_manager.notify(log)
            self.process_logger.info(log)
        # print("done updating log")


class WorkDisplay(WorkManager):

    def __init__(self, parent):
        super().__init__(parent)
        self.progress_window = WorkProgressBar(parent)

        self.progress_window.canceled.connect(self.cancel)

        # Don't let the user play with the main interface while the program is doing work
        self.progress_window.setModal(True)

        # Update the label to let the user know what is currently being worked on
        self.process_logger.addHandler(ProgressMessageBoxLogHandler(self.progress_window))

        self._complete_task.connect(self._advance)

    def _advance(self):
        value = self.progress_window.value()
        self.progress_window.setValue(value + 1)

    # TODO: Rename run() method to start() since it's non blocking
    def run(self):
        t = QtCore.QTimer(self)
        t.timeout.connect(self._update_log)
        t.start(PROCESS_LOGGING_REFRESH_RATE)
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
        finally:
            t.timeout.disconnect(self._update_log)
            t.stop()

    def complete_task(self, fut: concurrent.futures.Future):
        try:
            super().complete_task(fut)
        except Exception:
            if self.progress_window.isActiveWindow():
                self.progress_window.cancel()
            raise

    def cancel(self, quiet=False):
        super().cancel(quiet)
        self.progress_window.setAutoClose(False)
        self.progress_window.canceled.disconnect(self.cancel)
        self.progress_window.close()
        if not quiet:
            QtWidgets.QMessageBox.about(self.progress_window, "Canceled", "Successfully Canceled")


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


#
# class LogManager(AbsSubject):
#     def __init__(self) -> None:
#         super().__init__()
#         warnings.warn("Use default logging instead", DeprecationWarning)
#
#     # def __init__(self, message_queue_):
#     #     self.message_queue_ = message_queue_
#
#     def add_reporter(self, reporter):
#         self.subscribe(reporter)
#
#
# class SimpleCallbackReporter(AbsObserver):
#     def __init__(self, update_callback):
#         warnings.warn("Don't use", DeprecationWarning)
#         self._callback = update_callback
#
#     def emit(self, value):
#         self._callback(value)

#
# class StdoutReporter(AbsObserver):
#     def emit(self, value):
#         print(value, file=sys.stderr)


class GuiLogger(logging.Handler):
    def __init__(self, callback, level=logging.NOTSET):
        super().__init__(level)
        self.callback = callback

    def emit(self, record):
        self.callback(record.msg)
