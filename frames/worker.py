import concurrent.futures
import time
from abc import ABCMeta, abstractmethod

from PyQt5 import QtCore, QtWidgets

from multiprocessing import Queue


message_queue = Queue()


class QtMeta(type(QtCore.QObject), ABCMeta):
    pass


class AbsJob(metaclass=QtMeta):

    @abstractmethod
    def run(self, *args, **kwargs):
        pass

    @abstractmethod
    def log(self, message):
        pass


class ProcessJob(AbsJob):

    def run(self, *args, **kwargs):
        pass

    def log(self, message):
        message_queue.put(message, block=True)


class DummyJob(ProcessJob):
    def run(self, num, *args):
        self.log("{} ---STarting something".format(num))
        time.sleep(.1)
        self.log("---ending something".format(num))
        return "My result"


class Worker(QtCore.QObject):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self._jobs = []

    def initialize_worker(self):
        raise NotImplemented

    def cancel(self):
        raise NotImplemented

    def run_jobs(self, jobs):
        raise NotImplemented

    def add_job(self, job: ProcessJob):
        self._jobs.append(job)


class ProcessWorker(Worker):

    def initialize_worker(self, max_workers=1):
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)  # TODO: Fix this

    def cancel(self):
        self.executor.shutdown()

    def run_jobs(self, jobs):
        for i, j in zip(range(len(jobs)), jobs):
            fut = self.executor.submit(j.run, i)
            fut.add_done_callback(self.complete_task)
            self._tasks.append(fut)


class WorkManager(ProcessWorker):
    _complete_task = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self._tasks = []
        self.t = QtCore.QTimer()
        self.t.timeout.connect(self._update_log)
        self.t.start(100)
        self.prog = QtWidgets.QProgressDialog(parent)
        self.prog.canceled.connect(self.cancel)
        self.prog.setModal(True)
        self._complete_task.connect(self._advance)

    def _advance(self):
        value = self.prog.value()
        self.prog.setValue(value + 1)

    def run(self):
        if self._jobs:
            self.initialize_worker()
            self.prog.setRange(0, len(self._jobs))
            self.prog.setValue(0)
            self.run_jobs(self._jobs)
            self.prog.show()

    def complete_task(self, fut: concurrent.futures.Future):
        if fut.done():
            if not fut.cancelled():
                message = "task Completed with {} as the result".format(fut.result())
                message_queue.put(message)

            self._complete_task.emit()

    def cancel(self):
        message_queue.put("Called cancel")
        for task in self._tasks:
            task.cancel()
        super().cancel()

    # TODO: refactor into observer pattern so that messages can be subscribed to
    def _update_log(self):
        while not message_queue.empty():
            log = message_queue.get()
            self.prog.setLabelText(log)