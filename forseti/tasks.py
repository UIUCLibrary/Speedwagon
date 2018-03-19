import abc
import collections
import enum
import pickle
import queue
import sys
import typing

import forseti.worker


class TaskStatus(enum.IntEnum):
    IDLE = 0
    WORKING = 1
    SUCCESS = 2
    FAILED = 3


class AbsSubtask(metaclass=abc.ABCMeta):
    name: str = None

    @abc.abstractmethod
    def work(self) -> bool:
        pass

    @abc.abstractmethod
    def log(self, message) -> None:
        pass

    @property
    def task_result(self):
        return None

    @property
    def results(self):
        return None

    # @task_result.setter  # type: ignore
    # # @abc.abstractmethod
    # def task_result(self, value) -> None:
    #     warnings.warn("Using results instead", PendingDeprecationWarning)
    #     pass

    @abc.abstractmethod
    def exec(self) -> None:
        pass

    @property
    def settings(self):
        return {}


class Result(typing.NamedTuple):
    source: typing.Type[AbsSubtask]
    data: typing.Any


class Subtask(AbsSubtask):

    def __init__(self):
        self._result: Result = None
        # TODO: refactor into state machine
        self.status = TaskStatus.IDLE

        self.parent_task_log_q: typing.Deque[str] = None
        # self.parent_task_log_q: queue.Queue[str] = None

    @property
    def task_result(self):
        return self._result

    # self._result = Result(self.__class__, value)
    # @property
    # def results(self):
    #     pass

    # @task_result.setter
    # def task_result(self, value: typing.Type[typing.Any]):
    #     warnings.warn("Using results instead", PendingDeprecationWarning)
    #     self._result = Result(self.__class__, value)

    @property
    def results(self):
        return self._result.data

    @results.setter
    def results(self, value):
        self._result = Result(self.__class__, value)

    def log(self, message):
        self.parent_task_log_q.append(message)

    def exec(self) -> None:
        self.status = TaskStatus.WORKING

        if not self.work():
            self.status = TaskStatus.FAILED
        else:
            self.status = TaskStatus.SUCCESS


class AbsTask(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def on_completion(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def exec(self, *args, **kwargs):
        pass

    @property
    @abc.abstractmethod
    def status(self) -> TaskStatus:
        pass


class Task(AbsTask):
    def __init__(self) -> None:
        self.log_q: typing.Deque[str] = collections.deque()
        self.result: typing.Any = None


class MultiStageTask(Task):
    name = "Task"

    def __init__(self) -> None:
        super().__init__()
        # Todo: use the results builder from validate
        self.subtasks: typing.List[Subtask] = []

    @property
    def status(self) -> TaskStatus:
        has_failure = False
        still_working = False
        started = False
        all_success = True

        for sub_task in self.subtasks:
            if sub_task.status > TaskStatus.IDLE:
                started = True

            if sub_task.status == TaskStatus.WORKING:
                still_working = True

            if sub_task.status == TaskStatus.FAILED:
                has_failure = True
                all_success = False

            if sub_task.status != TaskStatus.SUCCESS:
                all_success = False

        if has_failure:
            return TaskStatus.FAILED

        if still_working:
            return TaskStatus.WORKING

        if all_success:
            return TaskStatus.SUCCESS

        if not started:
            return TaskStatus.IDLE

        raise Exception("Not all statuses are are taken into account")

    @property
    def progress(self) -> float:
        amount_completed = len([task for task in self.subtasks if task.status > TaskStatus.WORKING])
        return amount_completed / len(self.subtasks)

    def exec(self, *args, **kwargs):

        subtask_results = []
        try:
            for task in self.subtasks:
                task.exec()
                if task.results is not None:
                    subtask_results.append(task.results)
            self.on_completion(*args, **kwargs)
            if subtask_results:
                self.result = self.process_subtask_results(subtask_results)
            return self.result
        except Exception as e:
            print("Failed {}".format(e), file=sys.stderr)
            raise

    def on_completion(self, *args, **kwargs):
        pass

    def process_subtask_results(self, subtask_results: typing.List[typing.Any]) -> typing.Any:
        return subtask_results


class AbsTaskBuilder(metaclass=abc.ABCMeta):

    def __init__(self) -> None:
        self._subtasks: typing.List[Subtask] = []

    @property
    @abc.abstractmethod
    def task(self) -> MultiStageTask:
        pass

    def add_subtask(self, task: Subtask) -> None:
        self._subtasks.append(task)

    def build_task(self) -> MultiStageTask:
        task = self.task
        for subtask in self._subtasks:
            subtask.parent_task_log_q = task.log_q
            task.subtasks.append(subtask)
        return task


class TaskBuilder:
    # The director
    def __init__(self, builder: AbsTaskBuilder) -> None:
        self._builder = builder

    def build_task(self) -> MultiStageTask:
        task = self._builder.build_task()
        return task

    def add_subtask(self, subtask: Subtask):
        self._builder.add_subtask(subtask)

    @staticmethod
    def save(task_obj):
        task_serialized = TaskBuilder._serialize_task(task_obj)
        return pickle.dumps(task_serialized)

    @staticmethod
    def load(data):
        cls, attributes = pickle.loads(data)
        obj = TaskBuilder._deserialize_task(cls, attributes)
        return obj

    @staticmethod
    def _serialize_task(task_obj: MultiStageTask):
        res = task_obj.__class__, task_obj.__dict__
        return res

    @staticmethod
    def _deserialize_task(cls, attributes):
        obj = cls.__new__(cls)
        obj.__dict__.update(attributes)
        return obj


class QueueAdapter:

    def __init__(self) -> None:
        super().__init__()
        self._queue: queue.Queue = None

    def append(self, item):
        self._queue.put(item)

    def set_message_queue(self, value: queue.Queue):
        self._queue = value


class SubtaskJobAdapter(forseti.worker.AbsJobAdapter, forseti.worker.ProcessJobWorker):  # type: ignore

    def __init__(self, adaptee: Subtask) -> None:
        super().__init__(adaptee)
        self.adaptee.parent_task_log_q = QueueAdapter()

    @property
    def queue_adapter(self):
        return QueueAdapter()

    def process(self, *args, **kwargs):
        self.adaptee.exec()
        self.result = self.adaptee.task_result

    def set_message_queue(self, value):
        self.adaptee.parent_task_log_q.set_message_queue(value)

    @property
    def settings(self) -> dict:
        if self.adaptee.settings:
            return self.adaptee.settings
        else:
            return {key: value for key, value in self.adaptee.__dict__.items() if key != "parent_task_log_q"}

    @property
    def name(self) -> str:  # type: ignore
        return self.adaptee.name


class MultiStageTaskBuilder(AbsTaskBuilder):

    @property
    def task(self) -> MultiStageTask:
        return MultiStageTask()
