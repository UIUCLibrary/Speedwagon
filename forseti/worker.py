import concurrent.futures
# from abc import ABCMeta, abstractmethod
import queue
import typing
import abc
import sys
from abc import abstractmethod, ABCMeta

from PyQt5 import QtCore, QtWidgets
from collections import namedtuple
import multiprocessing

JobPair = namedtuple("JobPair", ("job", "args", "message_queue"))


class QtMeta(type(QtCore.QObject), abc.ABCMeta):  # type: ignore
    pass


class NoWorkError(RuntimeError):
    pass


class AbsJob(metaclass=QtMeta):

    def __init__(self):
        self.result = None

    def execute(self, *args, **kwargs):
        self.process(*args, **kwargs)
        self.on_completion(*args, **kwargs)
        return self.result

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
        # self._jobs: typing.List[JobPair] = []
        self._jobsq = queue.Queue()

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
        self._jobsq.put(new_job)

    def run_all_jobs(self):
        while self._jobsq.qsize() != 0:
            job, args, message_queue = self._jobsq.get()
            self._exec_job(job, args, message_queue)
            self._jobsq.task_done()



class WorkProgressBar(QtWidgets.QProgressDialog):

    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)


class WorkManager(ProcessWorker):
    finished = QtCore.pyqtSignal(object)
    _complete_task = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self._tasks = []
        self._results = []

        self.log_manager = LogManager()
        self.prog = WorkProgressBar(parent)

        self.prog.canceled.connect(self.cancel)

        # Don't let the user play with the main interface while the program is doing work
        self.prog.setModal(True)

        # Update the label to let the user know what is currently being worked on
        self.reporter = SimpleCallbackReporter(self.prog.setLabelText)

        # Update the log information
        self.t = QtCore.QTimer(self)
        self.t.timeout.connect(self._update_log)
        self.t.start(100)

        self._complete_task.connect(self._advance)

    def _advance(self):
        value = self.prog.value()
        self.prog.setValue(value + 1)

    def run(self):
        try:
            self.log_manager.subscribe(self.reporter)
            if self._jobsq.qsize() > 0:

                self.initialize_worker()
                self.prog.setRange(0, self._jobsq.qsize())
                self.prog.setValue(0)
                self.run_all_jobs()
                # self.run_jobs(self._jobs)
                self.prog.show()
            else:
                raise NoWorkError("No Jobs found")
        except Exception:
            self.prog.cancel()
            raise


    def cancel(self, quiet=False):
        self.prog.setAutoClose(False)
        self.prog.canceled.disconnect(self.cancel)
        self._message_queue.put("Called cancel")
        for task in reversed(self._tasks):
            if not task.done():
                task.cancel()
        self.t.stop()
        super().cancel()

        self.prog.close()
        if not quiet:
            QtWidgets.QMessageBox.about(self.prog, "Canceled", "Successfully Canceled")

    def _update_log(self):
        while not self._message_queue.empty():
            log = self._message_queue.get()
            self.log_manager.notify(log)

    def on_completion(self, *args, **kwargs):
        # print(self._results)
        self.finished.emit(self._results)
        self._message_queue.put("Finished")


class WorkManager2(WorkManager):
    finished = QtCore.pyqtSignal(object, object)

    def complete_task(self, fut: concurrent.futures.Future):
        if fut.done():
            if not fut.cancelled():
                result = fut.result()
                if result:
                    self._results.append(result)
                    # message = "task Completed with {} as the result".format(result)
                    # self._message_queue.put(message)

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
        self.finished.emit(self._results, self.completion_callback)
        # super().on_completion(*args, **kwargs)

    def __init__(self, parent):
        super().__init__(parent)
        self.completion_callback: callable = None



class AbsObserver(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def update(self, value):
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
                    observer.update()
                else:
                    observer.update(value)

class LogManager(AbsSubject):
    # def __init__(self, message_queue_):
    #     self.message_queue_ = message_queue_

    def add_reporter(self, reporter):
        self.subscribe(reporter)


class SimpleCallbackReporter(AbsObserver):
    def __init__(self, update_callback):
        self._callback = update_callback

    def update(self, value):
        self._callback(value)


class StdoutReporter(AbsObserver):
    def update(self, value):
        print(value, file=sys.stderr)
