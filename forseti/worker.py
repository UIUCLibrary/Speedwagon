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

from PyQt5 import QtCore, QtWidgets
from collections import namedtuple
import multiprocessing

PROCESS_LOGGING_REFRESH_RATE = 200

JobPair = namedtuple("JobPair", ("job", "args"))

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
            return None

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
        # print(message_queue)
        # print(job)
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
        # new_job.set_message_queue(message_queue)
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


# class MessageRefresher(contextlib.AbstractContextManager):
#
#     def __init__(self, callback, rate=20, parent=None) -> None:
#         print("creating timer at {}".format(rate))
#         self._timer = QtCore.QTimer(parent)
#         self._rate = rate
#         self.callback = callback
#         # super().__init__()
#
#     def __enter__(self):
#         self._timer.timeout.connect(self.callback)
#         self._timer.start(self._rate)
#         print("timing started")
#         return self
#         # return super().__enter__()
#
#     def __exit__(self, exc_type, exc_value, traceback):
#         self._timer.timeout.disconnect(self.callback)
#         super().__exit__(exc_type, exc_value, traceback)


# class WorkManager(ProcessWorker):
#     _complete_task = QtCore.pyqtSignal()
#     finished = QtCore.pyqtSignal(object, object)
#     failed = QtCore.pyqtSignal(Exception)
#
#     def __init__(self, parent):
#         warnings.warn("Don't use", DeprecationWarning)
#         super().__init__(parent)
#
#         self._results = []
#
#         # Update the log information
#
#         # self._log_manager = LogManager()
#         self.process_logger = logging.getLogger(__name__)
#         self.process_logger.setLevel(logging.DEBUG)
#
#         self.completion_callback: callable = None
#
#     @property
#     def results(self):
#         return self._results
#
#     @results.setter
#     def results(self, value):
#         self._results = value
#
#     def complete_task(self, fut: concurrent.futures.Future):
#         # self._complete_task.emit()
#
#         #
#         if fut.done():
#             # ex = fut.exception()
#             # if ex:
#             #     raise ex
#             # return
#             self._jobs_queue.task_done()
#             if not fut.cancelled():
#                 try:
#                     result = fut.result()
#                     if result:
#                         self.results.append(result)
#                 except Exception as e:
#                     print(e)
#                     self.failed.emit(e)
#                     raise
#             # logging.debug("Completed task")
#             self._complete_task.emit()
#
#         # # check if there are more tasks to do.
#         # for f in self._tasks:
#         #     if not f.done():
#         #         break
#         #
#         # # If all tasks are on_success, finish the on completion method
#         # else:
#         #
#         #     # Flush the log buffer before running on_completion
#         #     # self._update_log()
#         #
#         #     # self.log_manager.
#         #
#         #     self.on_completion(results=self.results)
#
#     def on_completion(self, *args, **kwargs):
#         # self._jobs_queue.get_results()
#         self.finished.emit(self.results, self.completion_callback)
#         # self.t.stop()
#         # super().on_completion(*args, **kwargs)
#
#     #
#     # def on_failure(self, reason):
#     #     msg = "Failed, {}".format(reason)
#     #     print(msg)
#     #     self._message_queue.put(msg)
#     #     self.failed.emit(msg)
#
#     # # TODO: Rename finish() method to start() since it's non blocking
#     # def finish(self):
#     #     t = QtCore.QTimer(self)
#     #     t.timeout.connect(self._update_log)
#     #     t.start(PROCESS_LOGGING_REFRESH_RATE)
#     #     try:
#     #         # self.log_manager.subscribe(self.reporter)
#     #         if self._jobs_queue.qsize() > 0:
#     #             self.initialize_worker()
#     #             self.progress_window.setRange(0, self._jobs_queue.qsize())
#     #             self.progress_window.setValue(0)
#     #             self.run_all_jobs()
#     #             # self.run_jobs(self._jobs)
#     #             self.progress_window.show()
#     #
#     #         else:
#     #             raise NoWorkError("No Jobs found")
#     #     except Exception as e:
#     #         print(e)
#     #         self.progress_window.cancel()
#     #         raise
#     #     finally:
#     #         t.timeout.disconnect(self._update_log)
#     #         t.stop()
#     #     self.t.stop()
#     def cancel(self, quiet=False):
#         # self.progress_window.setAutoClose(False)
#         # self.progress_window.canceled.disconnect(self.cancel)
#         self._message_queue.put("Called cancel")
#         for task in reversed(self._tasks):
#             if not task.done():
#                 task.cancel()
#         # super().cancel()
#
#         # self.progress_window.close()
#         # if not quiet:
#         #     QtWidgets.QMessageBox.about(self.progress_window, "Canceled", "Successfully Canceled")
#
#     def _update_log(self):
#         print("Updating log with a size of {}".format(self._message_queue.qsize()))
#         # with multiprocessing.Lock():
#         while not self._message_queue.empty():
#             # print(self._message_queue.qsize())
#             log = self._message_queue.get()
#             # self.log_manager.notify(log)
#             self.process_logger.info(log)
#         print("done updating log")

#
# class WorkDisplay(WorkManager):
#
#     def __init__(self, parent):
#         warnings.warn("Don't use", DeprecationWarning)
#         super().__init__(parent)
#         self.progress_window = QtWidgets.QProgressDialog(parent)
#         # self.progress_window = WorkProgressBar(parent)
#
#         self.progress_window.canceled.connect(self.cancel)
#
#         # Don't let the user play with the main interface while the program is doing work
#         self.progress_window.setModal(True)
#
#         # Update the label to let the user know what is currently being worked on
#         self.process_logger.addHandler(ProgressMessageBoxLogHandler(self.progress_window))
#
#         self._complete_task.connect(self._advance)
#         # QtCore.QCoreApplication.processEvents()
#
#     def _advance(self):
#         value = self.progress_window.value()
#         self.progress_window.setValue(value + 1)
#
#     def run(self):
#         self.initialize_worker()
#         t = QtCore.QTimer(self)
#         t.timeout.connect(self._update_log)
#         t.start(PROCESS_LOGGING_REFRESH_RATE)
#         try:
#             # self.log_manager.subscribe(self.reporter)
#             if self._jobs_queue.qsize() > 0:
#                 self.progress_window.setRange(0, self._jobs_queue.qsize())
#                 self.progress_window.setValue(0)
#
#                 # self.progress_window.show()
#
#                 self.run_all_jobs()
#                 # logging.debug("All jobs launched")
#
#                 # self.run_jobs(self._jobs)
#
#             else:
#                 raise NoWorkError("No Jobs found")
#         except Exception as e:
#             self.progress_window.cancel()
#             raise
#         finally:
#             t.timeout.disconnect(self._update_log)
#             t.stop()
#
#     def on_completion(self, *args, **kwargs):
#
#         super().on_completion(*args, **kwargs)
#         print("CALLING HERE")
#         # if self.progress_window.isActiveWindow():
#         # self.progress_window.close()
#
#     def complete_task(self, fut: concurrent.futures.Future):
#         try:
#             super().complete_task(fut)
#         except Exception:
#             if self.progress_window.isActiveWindow():
#                 self.progress_window.cancel()
#             raise
#
#     def cancel(self, quiet=False):
#         super().cancel(quiet)
#         self.progress_window.setAutoClose(False)
#         self.progress_window.canceled.disconnect(self.cancel)
#         self.progress_window.close()
#         if not quiet:
#             QtWidgets.QMessageBox.about(self.progress_window, "Canceled", "Successfully Canceled")


# class WorkWrapper(contextlib.AbstractContextManager):
#
#     def __init__(self, parent, tool, logger: logging.Logger) -> None:
#         warnings.warn("Use WorkerManager instead", DeprecationWarning)
#         self.parent = parent
#         self.worker_display = WorkDisplay(self.parent)
#         self.successful = False
#         self.active_tool = tool()
#         self.logger = logger
#         self.worker_display.finished.connect(self.completed)
#         self._working = None
#         QtCore.QCoreApplication.processEvents()
#
#     def completed(self, *args, **kwargs):
#         # self.worker_display.progress_window.close()
#         self._working = False
#         self.successful = True
#
#     def __enter__(self):
#
#         self.worker_display.completion_callback = self.active_tool.on_completion
#         for handler in self.logger.handlers:
#             self.worker_display.process_logger.addHandler(handler)
#         self._working = True
#
#         return self
#
#     def __exit__(self, exc_type, exc_value, traceback):
#         pass
#         if exc_type:
#             print("exc_type = {}, exc_value = {}, traceback = {}".format(exc_type, exc_value, traceback))
#         # self.worker_display.completion_callback
#         while self._working is False:
#             # print("processing", file=sys.stderr)
#             # self.parent.app.processEvents()
#             QtCore.QCoreApplication.processEvents()
#             print("sleeping", file=sys.stderr)
#             if not self.worker_display.progress_window.isVisible():
#                 break
#             # time.sleep(.01)
#             pass
#         for handler in self.logger.handlers:
#             self.worker_display.process_logger.removeHandler(handler)
#         if self.successful:
#             QtWidgets.QMessageBox.about(self.parent, "Finished", "Finished")
#         # print("Exiting like I should", file=sys.stderr)
#
#     def set_title(self, value):
#         self.worker_display.progress_window.setWindowTitle(value)
#
#     def add_job(self, args):
#         job = self.active_tool.new_job()
#         self.worker_display.add_job(job, **args)
#         # self.worker_display.add_job(job, **args)
#
#     def run(self):
#         self.worker_display.progress_window.setWindowTitle(self.active_tool.name)
#         self._working = True
#         self.worker_display.run()
#         # print("Here")
#
#     def valid_arguments(self, args):
#         self.active_tool.validate_args(**args)


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


class ProcessWorker2(Worker2):
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=1)

    # message_log = manager.Queue()

    @classmethod
    def initialize_worker(cls, max_workers=1) -> None:
        cls.executor.shutdown()
        cls.executor = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)

    @classmethod
    def add_job(cls, job, args, message_queue):
        # job.mq = message_queue

        return cls.executor.submit(job.new, job, message_queue, **args)
        # return cls.executor.submit(new_job.execute, **args)


# class WorkRunner(contextlib.AbstractContextManager):
#
#     def __init__(self, logger: logging.Logger, parent=None, title=None, results_queue=None, ) -> None:
#         warnings.warn("User WorkRunnerExternal instead", DeprecationWarning)
#         self.manager = multiprocessing.Manager()
#         self._log_queue = self.manager.Queue()  # type: ignore
#         # self.logger = logging.getLogger(__name__)
#         self.logger = logger
#         self.parent = parent
#         self.dialog = QtWidgets.QProgressDialog(parent)
#         self.dialog.setMinimumDuration(0)
#
#         # self.dialog.setAutoClose(False)
#         self.handler = ProgressMessageBoxLogHandler(self.dialog)
#         # self.logger.addHandler(ProgressMessageBoxLogHandler(self.dialog))
#         # self.dialog.setVisible(True)
#         self.dialog.setModal(True)
#         # self.dialog.setAutoClose(False)
#         self.dialog.setWindowTitle(title)
#         self.jobs = self.manager.Queue()
#         self.work_manager = ProcessWorker2()
#
#         self.results = self.manager.Queue()
#         self.results = results_queue or self.manager.Queue()
#         self._tasks: typing.List[concurrent.futures.Future] = []
#
#     def __enter__(self):
#         dialog = QtWidgets.QProgressDialog(self.dialog)
#         dialog.setLabelText("Initializing")
#         dialog.setModal(True)
#         self.work_manager.initialize_worker()
#         self.logger.addHandler(self.handler)
#         dialog.close()
#
#         return self
#
#     def __exit__(self, exc_type, exc_value, traceback):
#         self.logger.removeHandler(self.handler)
#         self.dialog.close()
#         self.work_manager.executor.shutdown()
#
#     def start(self):
#         # Load add all jobs to the work manager
#         # self.dialog.canceled.connect(self._refresh_progress)
#         self.logger.info("Initializing {} tasks".format(self.jobs.qsize()))
#         self.dialog.canceled.connect(self._cancel)
#         self.dialog.setValue(0)
#         # self.dialog.setRange(0, self.jobs.qsize())
#         QtWidgets.QApplication.processEvents()
#         while not self.jobs.empty():
#             foo = self.jobs.get()
#             new_job = foo.job()
#             args = foo.args
#             fut = self.work_manager.add_job(new_job, args, self._log_queue)
#             fut.add_done_callback(self._update_progress)
#             self._tasks.append(fut)
#             self.dialog.setMaximum(self._tasks)
#             QtWidgets.QApplication.processEvents()
#
#         # self.dialog.setVisible(True)
#         QtWidgets.QApplication.processEvents()
#         print("HEEEEEEEEEEEEEER")
#
#     def finish(self):
#
#         with MessageRefresher(self._refresh_progress, parent=self.dialog, rate=100):
#             self._run_and_update()
#
#     def _run_and_update(self):
#         try:
#             for res in concurrent.futures.as_completed(self._tasks):
#
#                 try:
#                     if res.cancelled():
#                         continue
#                     result = res.result()
#                     self.results.put(result)
#                     self._update_progress()
#                     # QtWidgets.QApplication.processEvents()
#
#
#
#                 except concurrent.futures.CancelledError:
#                     break
#                 # if self.results.qsize() == self.dialog.maximum():
#                 #     print("HERE")
#                 #     print("sleep")
#                 #     time.sleep(1)
#                 self._update_progress()
#             # for some reason the cancel is being called if it's finished correctly, so if it gets here
#             # simple remove the payload of the cancel slot
#             self.dialog.canceled.disconnect(self._cancel)
#         except concurrent.futures.TimeoutError as e:
#             print(e)
#
#     def _update_progress(self, *args, **kwargs):
#         # self._refresh_progress()
#         QtWidgets.QApplication.processEvents()
#         print("Updating")
#         self.dialog.setValue(self.results.qsize())
#
#         # QtWidgets.QApplication.processEvents()
#
#     def _refresh_progress(self):
#         # Needs to be updated otherwise it hangs
#         QtWidgets.QApplication.processEvents()
#         with self.manager.Lock():
#             while not self._log_queue.empty():
#                 message = self._log_queue.get()
#                 self.logger.info(message)
#                 self._update_progress()
#
#                 # self.dialog.setValue(self.results.qsize())
#
#                 # self.dialog.setLabelText(message)
#             QtWidgets.QApplication.processEvents()
#
#     def _cancel(self):
#         print("Canceling")
#         self._refresh_progress()
#         self.dialog.setEnabled(False)
#         self.logger.removeHandler(self.handler)
#         QtWidgets.QApplication.processEvents()
#
#         for i, task in enumerate(reversed(self._tasks)):
#             print(task.cancel())
#
#         self._refresh_progress()
#         self.dialog.setVisible(False)
#         QtWidgets.QApplication.processEvents()
#
#         QtWidgets.QMessageBox.about(self.parent, "Canceled", "Successfully Canceled")


# class WorkRunnerExternal(contextlib.AbstractContextManager):
#
#     def __init__(self, logger: logging.Logger, process_worker: ProcessWorker2, parent=None, title=None,
#                  results_queue=None) -> None:
#         self.manager = multiprocessing.Manager()
#         self._status = "idle"
#         self._log_queue = self.manager.Queue()  # type: ignore
#         # self._log_queue = queue.Queue()  # type: ignore
#         # self.logger = logging.getLogger(__name__)
#         self.logger = logger
#         self.parent = parent
#         self.dialog = QtWidgets.QProgressDialog(parent)
#
#         # self.dialog.setAutoClose(False)
#         self.handler = ProgressMessageBoxLogHandler(self.dialog)
#         # self.logger.addHandler(ProgressMessageBoxLogHandler(self.dialog))
#         # self.dialog.setVisible(True)
#         self.dialog.setModal(True)
#         # self.dialog.setAutoClose(False)
#         self.dialog.setWindowTitle(title)
#         self.jobs: queue.Queue[JobPair] = queue.Queue()
#         # self.jobs = self.manager.Queue()
#         # self.work_manager = ProcessWorker2()
#
#         # self.results = queue.Queue()
#         self.results = results_queue or self.manager.Queue()
#         self._tasks: typing.List[concurrent.futures.Future] = []
#         self.work_manager = process_worker
#
#     @property
#     def status(self):
#         return self._status
#
#     @status.setter
#     def status(self, value):
#         print("Changing status from {} to {}".format(self._status, value))
#         self._status = value
#
#     def __enter__(self):
#         dialog = QtWidgets.QProgressDialog(self.dialog)
#         dialog.setLabelText("Initializing")
#         dialog.setModal(True)
#         self.work_manager.initialize_worker()
#         self.logger.addHandler(self.handler)
#         dialog.close()
#
#         return self
#
#     def __exit__(self, exc_type, exc_value, traceback):
#         self.logger.removeHandler(self.handler)
#         self.dialog.close()
#         self.work_manager.executor.shutdown()
#
#     def start(self):
#         # Load add all jobs to the work manager
#         # self.dialog.canceled.connect(self._refresh_progress)
#         jobs_size = self.jobs.qsize()
#         self.logger.info("Initializing {} tasks".format(jobs_size))
#         self.dialog.canceled.connect(self._cancel)
#         self.dialog.setValue(0)
#         # self.dialog.setRange(0, jobs_size)
#         # self.dialog.setRange(0, jobs_size)
#         self.dialog.show()
#         QtWidgets.QApplication.processEvents()
#         while not self.jobs.empty():
#             foo = self.jobs.get()
#             new_job = foo.job()
#             args = foo.args
#             fut = self.work_manager.add_job(new_job, args, self._log_queue)
#             fut.add_done_callback(self._update_progress)
#             self._tasks.append(fut)
#             self.dialog.setMaximum(len(self._tasks))
#
#         # self.dialog.setVisible(True)
#         QtWidgets.QApplication.processEvents()
#         self.status = "working"
#
#     def finish(self):
#
#         with MessageRefresher(self._refresh_progress, parent=self.dialog, rate=100):
#             self._run_and_update()
#
#     def _run_and_update(self):
#         try:
#             for res in concurrent.futures.as_completed(self._tasks):
#
#                 try:
#                     if res.cancelled():
#                         continue
#                     result = res.result()
#                     self.results.put(result)
#                     self._update_progress()
#                     # QtWidgets.QApplication.processEvents()
#
#
#
#                 except concurrent.futures.CancelledError:
#                     break
#                 # if self.results.qsize() == self.dialog.maximum():
#                 #     print("HERE")
#                 #     print("sleep")
#                 #     time.sleep(1)
#                 self._update_progress()
#             self.dialog.setValue(self.dialog.maximum())
#             # for some reason the cancel is being called if it's finished correctly, so if it gets here
#             # simple remove the payload of the cancel slot
#             self.dialog.canceled.disconnect(self._cancel)
#         except concurrent.futures.TimeoutError as e:
#             print(e)
#
#     def _update_progress(self, *args, **kwargs):
#         # self._refresh_progress()
#         if not self.dialog.isVisible():
#             QtWidgets.QApplication.processEvents()
#             return
#         self.dialog.setValue(self.results.qsize())
#         QtWidgets.QApplication.processEvents()
#         # QtWidgets.QApplication.processEvents()
#
#     def _refresh_progress(self):
#         # Needs to be updated otherwise it hangs
#         QtWidgets.QApplication.processEvents()
#         with self.manager.Lock():
#             while not self._log_queue.empty():
#                 message = self._log_queue.get()
#                 self.logger.info(message)
#                 self.dialog.setValue(self.results.qsize())
#                 QtWidgets.QApplication.processEvents()
#             self._update_progress()
#         QtWidgets.QApplication.processEvents()
#
#         # self.dialog.setValue(self.results.qsize())
#
#         # self.dialog.setLabelText(message)
#
#     def _cancel(self):
#         print("Canceling")
#         self._refresh_progress()
#         self.dialog.setEnabled(False)
#         self.logger.removeHandler(self.handler)
#         QtWidgets.QApplication.processEvents()
#
#         for i, task in enumerate(reversed(self._tasks)):
#             print(task.cancel())
#
#         self._refresh_progress()
#         self.dialog.setVisible(False)
#         QtWidgets.QApplication.processEvents()
#
#         QtWidgets.QMessageBox.about(self.parent, "Canceled", "Successfully Canceled")


class WorkRunnerExternal2(contextlib.AbstractContextManager):
    def __init__(self, tool, options, parent):
        self.results = []
        self._tool = tool
        self._options = options
        self._parent = parent
        self.abort_callback = None
        # self._message_logger = logger
        self.jobs: queue.Queue[JobPair] = queue.Queue()

    def __enter__(self):
        self.dialog = QtWidgets.QProgressDialog(self._parent)
        self.dialog.setModal(True)
        self.dialog.setLabelText("Initializing")
        self.progress_dialog_box_handler = ProgressMessageBoxLogHandler(self.dialog)
        self.dialog.canceled.connect(self.abort)
        # self.dialog.show()
        # self.dialog.exec_()
        return self

    def abort(self):
        if self.abort_callback:
            self.abort_callback()

    def __exit__(self, exc_type, exc_value, traceback):
        self.dialog.close()


# class WorkerManager:
#     # manager = None
#
#     # _log_manager = manager.Queue()  # type: ignore
#     # _log_manager = queue.Queue()  # type: ignore
#
#     def __init__(self, title, tool, logger, parent=None) -> None:
#
#         # WorkerManager.manager = multiprocessing.Manager()
#         # self._log_manager = WorkerManager.manager.Queue()
#         # self._log_manager = queue.Queue()
#
#         self.logger = logger
#         # self.logger = logging.getLogger(__name__)
#         self.logger.setLevel(logging.DEBUG)
#         self.title = title
#         self._tool = tool
#         self.parent = parent
#         # self._processor = ProcessWorker2()
#         self._job_processor = ProcessWorker2()
#         self._results: typing.List[dict] = []
#         self._results_queue: queue.Queue[dict] = queue.Queue()
#         # self._results_queue: queue.Queue[dict] = queue.Queue()
#         # self._results_queue: queue.Queue[dict] = WorkerManager.manager.Queue()
#
#     def open(self, settings) -> WorkRunnerExternal:
#         if self._tool is None:
#             raise ValueError("Need to have a tool")
#
#         searching_dialog = QtWidgets.QProgressDialog()
#         searching_dialog.setWindowTitle("Locating jobs")
#         runner = WorkRunnerExternal(process_worker=self._job_processor, logger=self.logger, parent=self.parent,
#                                     title=self.title, results_queue=self._results_queue)
#         for i, args in enumerate(self._get_jobs(settings)):
#             searching_dialog.setLabelText("Found {} jobs".format(i + 1))
#             new_job_ = self._tool.new_job
#             new_job = JobPair(new_job_, args=args)
#             # new_job = JobPair(new_job_, args=args, message_queue=self._log_manager)
#             runner.jobs.put(new_job)
#         searching_dialog.close()
#
#         return runner
#
#     def _get_jobs(self, settings) -> typing.Iterable:
#         return self._tool.discover_jobs(**settings)
#
#     @property
#     def results(self):
#         while not self._results_queue.empty():
#             self._results.append(self._results_queue.get())
#         return self._results


class ToolJobManager(contextlib.AbstractContextManager):

    def __init__(self, max_workers=1) -> None:
        self.manager = multiprocessing.Manager()
        self._max_workers = max_workers
        self.active = False
        self._pending_jobs = queue.Queue()
        self.futures = []
        self._results = []
        self.logger = logging.getLogger(__name__)
        # self._message_queue = queue.Queue()

    def __enter__(self):
        self._message_queue = self.manager.Queue()
        self._executor = concurrent.futures.ProcessPoolExecutor(self._max_workers)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("Still have {} unstarted jobs in the queue".format(self._pending_jobs.qsize()))
        self._executor.shutdown()

    def open(self, options, tool, parent):
        return WorkRunnerExternal2(tool=tool, options=options, parent=parent)

    def add_job(self, job, settings):
        self._pending_jobs.put(JobPair(job, settings))

    def start(self):
        self.active = True
        while not self._pending_jobs.empty():
            tool, settings = self._pending_jobs.get()
            job_type = tool.new_job()
            job = job_type()
            job.mq = self._message_queue
            fut = self._executor.submit(job.execute, **settings)
            self.futures.append(fut)

    def abort(self):
        self.active = False
        still_running = []
        dialog = QtWidgets.QProgressDialog()
        dialog.setWindowTitle("Canceling")
        dialog.setModal(True)
        for future in reversed(self.futures):
            if not future.cancel():
                if future.running():
                    still_running.append(future)
        dialog.setRange(0, len(still_running))
        dialog.setLabelText("Canceling".format(len(still_running)))
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
        dialog.accept()
        print("canceled")

    def get_results(self, timeout_callback=None) -> list:
        # results = []
        total_jobs = len(self.futures)
        completed = 0
        while self.active:
            try:
                completed_results = []
                for f in concurrent.futures.as_completed(self.futures, timeout=0.01):
                    if not f.cancelled():
                        result = f.result()
                        self.futures.remove(f)
                        completed += 1
                        yield result
                        # completed_results.append(f.result())

                if timeout_callback:
                    timeout_callback(completed, total_jobs)

                self.active = False
                self.futures.clear()
                self.flush_message_buffer()
                results = completed_results

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
