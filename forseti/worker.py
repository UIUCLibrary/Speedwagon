import concurrent.futures
# from abc import ABCMeta, abstractmethod
import typing
import abc
import sys
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
        self.on_completion()
        return self.result

    @abc.abstractmethod
    def process(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def log(self, message):
        pass

    def on_completion(self):
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


class Worker(QtCore.QObject):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self._jobs: typing.List[JobPair] = []

    def initialize_worker(self):
        raise NotImplemented

    def cancel(self):
        raise NotImplemented

    def run_jobs(self, jobs):
        raise NotImplemented


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



    def run_jobs(self, jobs):
        for job, args, message_queue in jobs:
            new_job = job()
            new_job.set_message_queue(message_queue)
            fut = self.executor.submit(new_job.execute, **args)
            fut.add_done_callback(self.complete_task)
            self._tasks.append(fut)

    def add_job(self, job: typing.Type[ProcessJob], **kwargs):
        new_job = JobPair(job, args=kwargs, message_queue=self._message_queue)
        self._jobs.append(new_job)

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
            if self._jobs:

                self.initialize_worker()
                self.prog.setRange(0, len(self._jobs))
                self.prog.setValue(0)
                self.run_jobs(self._jobs)
                self.prog.show()
            else:
                raise NoWorkError("No Jobs found")
        except Exception:
            self.prog.cancel()
            raise

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
                self.on_completion()

    def cancel(self):
        self.prog.setAutoClose(False)
        self.prog.canceled.disconnect(self.cancel)
        self._message_queue.put("Called cancel")
        for task in reversed(self._tasks):
            if not task.done():
                task.cancel()
        print(self._tasks)
        self.t.stop()
        super().cancel()
        # QtWidgets.QMessageBox.about(self.prog, "Canceling", "Canceling")
            # print(f"canceling {task}")
        # QtWidgets.QMessageBox("asdfasdfasdf", "asdfasdfasdf")
        # list(map(lambda task: task.cancel(), self._tasks))
        # self.executor.submit(concurrent.futures.wait, )
        # concurrent.futures.wait(self._tasks,return_when=concurrent.futures.ALL_COMPLETED)

        self.prog.close()
        QtWidgets.QMessageBox.about(self.prog, "Canceled", "Successfully Canceled")

        # for task in self._tasks:
        #     task.cancel()
        # for task in self._tasks:
        #     if not task.done():
        #         task.get()



    def _update_log(self):
        while not self._message_queue.empty():
            log = self._message_queue.get()
            self.log_manager.notify(log)

    def on_completion(self):
        # print(self._results)
        self._message_queue.put("Finished")
        self.finished.emit(self._results)


class AbsObserver(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def update(self, value):
        pass


class AbsSubject(metaclass=abc.ABCMeta):

    _observers = set()  # type: typing.Set[AbsObserver]

    def subscribe(self, observer: AbsObserver):
        if not isinstance(observer, AbsObserver):
            raise TypeError("Observer not derived from AbsObserver")
        self._observers |= {observer}

    def unsubscribe(self, observer: AbsObserver):
        self._observers -= {observer}

    def notify(self, value=None):
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