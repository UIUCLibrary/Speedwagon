import abc

import collections
import enum
import pickle
import queue
import sys
from typing import NamedTuple, Type, Optional, List, Deque, Any


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
    def task_result(self) -> Optional['Result']:
        return None

    @property
    def results(self) -> Optional[Any]:
        return None

    @property  # type: ignore
    @abc.abstractmethod
    def status(self) -> TaskStatus:
        pass

    @status.setter  # type: ignore
    @abc.abstractmethod
    def status(self, value: TaskStatus):
        pass

    @abc.abstractmethod
    def exec(self) -> None:
        pass

    @property
    def settings(self):
        return {}

    @property  # type: ignore
    @abc.abstractmethod
    def parent_task_log_q(self) -> Deque[str]:
        pass

    @parent_task_log_q.setter  # type: ignore
    @abc.abstractmethod
    def parent_task_log_q(self, value: Deque[str]):
        pass


class Result(NamedTuple):
    source: Type[AbsSubtask]
    data: Any


class Subtask(AbsSubtask):

    def __init__(self) -> None:
        self._result: Result = None
        # TODO: refactor into state machine
        self._status = TaskStatus.IDLE

        self._parent_task_log_q: Deque[str] = None

    @property  # type: ignore
    def parent_task_log_q(self) -> Deque[str]:
        return self._parent_task_log_q

    @parent_task_log_q.setter
    def parent_task_log_q(self, value: Deque[str]):
        self._parent_task_log_q = value

    @property
    def task_result(self):
        return self._result

    @property
    def status(self) -> TaskStatus:
        return self._status

    @status.setter
    def status(self, value: TaskStatus):
        self._status = value

    def work(self) -> bool:
        return super().work()

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

    def set_results(self, results):
        self._result = Result(self.__class__, results)

    def log(self, message):
        self._parent_task_log_q.append(message)

    def exec(self) -> None:
        self.status = TaskStatus.WORKING

        if not self.work():
            self.status = TaskStatus.FAILED
        else:
            self.status = TaskStatus.SUCCESS


class PreTask(AbsSubtask):

    def __init__(self) -> None:
        self._status = TaskStatus.IDLE
        self._parent_task_log_q: Deque[str] = None
        self._result: Result = None

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def parent_task_log_q(self) -> Deque[str]:
        return self._parent_task_log_q

    @parent_task_log_q.setter
    def parent_task_log_q(self, value):
        self._parent_task_log_q = value

    def exec(self) -> None:
        if not self.work():
            self._status = TaskStatus.FAILED
        else:
            self._status = TaskStatus.SUCCESS

    def log(self, message):
        self._parent_task_log_q.append(message)
    #
    @property
    def task_result(self):
        return self._result

    def pretask_result(self):
        pass

    def work(self) -> bool:
        return super().work()


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


class AbsTaskComponents(metaclass=abc.ABCMeta):

    @property  # type: ignore
    @abc.abstractmethod
    def pretask(self) -> Optional[AbsSubtask]:
        pass

    @pretask.setter  # type: ignore
    @abc.abstractmethod
    def pretask(self, value: AbsSubtask):
        pass

    @property  # type: ignore
    @abc.abstractmethod
    def posttask(self) -> Optional[AbsSubtask]:
        pass

    @posttask.setter  # type: ignore
    @abc.abstractmethod
    def posttask(self, value: AbsSubtask):
        pass


class Task(AbsTask, AbsTaskComponents):
    def __init__(self) -> None:
        self.log_q: Deque[str] = collections.deque()
        self.result: Any = None
        self._pre_task: Optional[AbsSubtask] = None
        self._post_task: Optional[AbsSubtask] = None

    @property
    def pretask(self) -> Optional[AbsSubtask]:
        return self._pre_task

    @pretask.setter
    def pretask(self, value: AbsSubtask):
        self._pre_task = value

    @property
    def posttask(self) -> Optional[AbsSubtask]:
        return self._post_task

    @posttask.setter
    def posttask(self, value: AbsSubtask):
        self._post_task = value

    def on_completion(self, *args, **kwargs):
        return super().on_completion(*args, **kwargs)

    def exec(self, *args, **kwargs):
        return super().exec(*args, **kwargs)

    @property
    def status(self) -> TaskStatus:
        return super().status


class MultiStageTask(Task):
    name = "Task"

    def __init__(self) -> None:
        super().__init__()
        # Todo: use the results builder from validate
        self._main_subtasks: List[AbsSubtask] = []

    @property
    def main_subtasks(self):
        return self._main_subtasks

    @property
    def subtasks(self):
        all_subtasks = []

        if self.pretask:
            all_subtasks.append(self.pretask)

        all_subtasks += self._main_subtasks
        if self.posttask:
            all_subtasks.append(self.posttask)
        return all_subtasks

    @property
    def status(self) -> TaskStatus:
        has_failure = False
        still_working = False
        started = False
        all_success = True

        for sub_task in self.main_subtasks:
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
        amount_completed = len(
            [task for task in self.main_subtasks
             if task.status > TaskStatus.WORKING])
        return amount_completed / len(self.main_subtasks)

    def exec(self, *args, **kwargs):

        subtask_results = []
        try:

            if self.pretask:
                self.pretask.exec()
                if self.pretask.results:
                    subtask_results.append(self.pretask.results)
                else:
                    print("NOOOOP")

            for subtask in self.main_subtasks:
                subtask.exec()
                if subtask.results is not None:
                    subtask_results.append(subtask.results)
            self.on_completion(*args, **kwargs)
            if subtask_results:
                self.result = self.process_subtask_results(subtask_results)
            return self.result
        except Exception as e:
            print("Failed {}".format(e), file=sys.stderr)
            raise

    def on_completion(self, *args, **kwargs):
        pass

    def process_subtask_results(self, subtask_results: List[Any]) -> Any:
        return subtask_results


class AbsTaskBuilder(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def task(self) -> MultiStageTask:
        pass

    @abc.abstractmethod
    def add_subtask(self, task):
        pass

    @abc.abstractmethod
    def build_task(self):
        pass

    @abc.abstractmethod
    def set_pretask(self, subtask: AbsSubtask):
        pass

    @abc.abstractmethod
    def set_posttask(self, subtask: AbsSubtask):
        pass


class BaseTaskBuilder(AbsTaskBuilder):

    def __init__(self) -> None:
        self._main_subtasks: List[AbsSubtask] = []
        self._pretask: Optional[AbsSubtask] = None
        self._posttask: Optional[AbsSubtask] = None

    def add_subtask(self, task: AbsSubtask) -> None:
        self._main_subtasks.append(task)

    def build_task(self) -> MultiStageTask:
        task = self.task

        if self._pretask is not None:
            pretask = self._pretask
            pretask.parent_task_log_q = task.log_q  # type: ignore
            task.pretask = pretask

        for subtask in self._main_subtasks:
            subtask.parent_task_log_q = task.log_q  # type: ignore
            task.main_subtasks.append(subtask)

        if self._posttask is not None:
            post_task = self._posttask
            post_task.parent_task_log_q = task.log_q  # type: ignore
            task.posttask = post_task

        return task

    @property
    def task(self) -> MultiStageTask:
        return super().task

    def set_pretask(self, subtask: AbsSubtask):
        self._pretask = subtask

    def set_posttask(self, subtask: AbsSubtask):
        self._posttask = subtask


class TaskBuilder:
    # The director
    def __init__(self, builder: BaseTaskBuilder) -> None:
        self._builder = builder

    def build_task(self) -> MultiStageTask:
        task = self._builder.build_task()
        return task

    def add_subtask(self, subtask: Subtask):
        self._builder.add_subtask(subtask)

    def set_pretask(self, subtask: Subtask):
        self._builder.set_pretask(subtask)

    def set_posttask(self, subtask):
        self._builder.set_posttask(subtask)

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


class MultiStageTaskBuilder(BaseTaskBuilder):

    @property
    def task(self) -> MultiStageTask:
        return MultiStageTask()
