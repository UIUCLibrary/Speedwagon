"""Tasks."""
from __future__ import annotations
import abc
import collections
import enum
import os
import sys
import queue
import pickle
import typing
from typing import Optional, Any, Deque, Type, List, Generic, TypeVar
from dataclasses import dataclass

__all__ = [
    "QueueAdapter",
    "MultiStageTaskBuilder",
    "TaskBuilder",
    "Result",
    "AbsSubtask",
    "Subtask",
    "TaskStatus",
]

import speedwagon.exceptions


class TaskStatus(enum.IntEnum):
    """Task Status."""

    IDLE = 0
    WORKING = 1
    SUCCESS = 2
    FAILED = 3


_T = TypeVar("_T")


class AbsSubtask(Generic[_T], metaclass=abc.ABCMeta):
    """Abstract subclass for subtasks."""

    name: Optional[str] = None

    @abc.abstractmethod
    def work(self) -> bool:
        """Perform work."""

    @abc.abstractmethod
    def log(self, message: str) -> None:
        """Log a message to the console on the main window."""

    @property
    def task_result(self) -> Optional[Result[_T]]:
        """Get the results of the subtask."""
        return None

    @property
    def results(self) -> Optional[_T]:
        """Get the results of the subtask."""
        return None

    @property  # type: ignore
    @abc.abstractmethod
    def status(self) -> TaskStatus:
        """Get that status of the subtask."""

    @status.setter  # type: ignore
    @abc.abstractmethod
    def status(self, value: TaskStatus) -> None:
        pass

    @abc.abstractmethod
    def exec(self) -> None:
        """Execute subtask."""

    @property
    def settings(self) -> typing.Dict[str, str]:
        """Get the settings for the subtask."""
        return {}

    @property  # type: ignore
    @abc.abstractmethod
    def parent_task_log_q(self) -> Deque[str]:  # noqa: D102
        pass

    @parent_task_log_q.setter  # type: ignore
    @abc.abstractmethod
    def parent_task_log_q(self, value: Deque[str]) -> None:
        pass


@dataclass
class Result(Generic[_T]):
    """Subtask result.

    Attributes:
        source: Class Type used to provide the results
        data: Payload of the result data.
    """

    source: Type[AbsSubtask]
    data: _T


class Subtask(AbsSubtask, Generic[_T]):
    """Base class for defining a new task for a :py:class:`Workflow` to create.

    Subclass this generate a new task
    """

    def task_description(self) -> Optional[str]:
        """Get user readable information about what the subtask is doing."""
        return None

    def __init__(self) -> None:
        """Create a new sub-task."""
        self._result: Optional[Result[_T]] = None
        # TODO: refactor into state machine
        self._status = TaskStatus.IDLE
        self._working_dir = ""
        self.task_working_dir = ""

        self._parent_task_log_q: Optional[Deque[str]] = None

    @property
    def subtask_working_dir(self) -> str:
        """Get the subtask working directory.

        Notes:
            This has the side effect of creating the working directory if it
            does not already exist.
        """
        if not os.path.exists(self._working_dir):
            os.makedirs(self._working_dir)
        return self._working_dir

    @subtask_working_dir.setter
    def subtask_working_dir(self, value: str) -> None:
        self._working_dir = value

    @property
    def parent_task_log_q(self) -> Deque[str]:
        """Log queue of the parent."""
        if self._parent_task_log_q is None:
            raise RuntimeError("Property parent_task_log_q has not be set")
        return self._parent_task_log_q

    @parent_task_log_q.setter
    def parent_task_log_q(self, value: Deque[str]) -> None:
        self._parent_task_log_q = value

    @property
    def task_result(self) -> Optional[Result[_T]]:
        """Get the result of the subtask."""
        return self._result

    @property
    def status(self) -> TaskStatus:
        """Get the status of the subtask."""
        return self._status

    @status.setter
    def status(self, value: TaskStatus) -> None:
        self._status = value

    def work(self) -> bool:
        """Perform work.

        This method is called when the task's work should be done.

        Override this method to accomplish the task.

        Note:
            Currently expects to return a boolean value to indicate if the task
            has succeeded or failed. However, this is likely to change.
        """
        raise NotImplementedError()

    @property
    def results(self) -> Optional[_T]:
        """Get the results of the subtask."""
        if self._result is None:
            return None
        return self._result.data

    def set_results(self, results: _T) -> None:
        """Set the results of the subtask."""
        self._result = Result(self.__class__, results)

    def log(self, message: str) -> None:
        """Generate text message for the subtask."""
        if self._parent_task_log_q is not None:
            self._parent_task_log_q.append(message)

    def exec(self) -> None:
        """Execute subtask."""
        self.status = TaskStatus.WORKING
        try:
            self.status = (
                TaskStatus.FAILED if not self.work() else TaskStatus.SUCCESS
            )
        except speedwagon.exceptions.SpeedwagonException as e:
            self.status = TaskStatus.FAILED
            raise e


class PreTask(AbsSubtask):
    """Pre-task subtask."""

    def __init__(self) -> None:
        """Create a new pre-task."""
        self._status = TaskStatus.IDLE
        self._parent_task_log_q: Optional[Deque[str]] = None
        self._result: Optional[Result] = None

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def parent_task_log_q(self) -> Deque[str]:
        if self._parent_task_log_q is None:
            raise RuntimeError("Property parent_task_log_q has not be set")
        return self._parent_task_log_q

    @parent_task_log_q.setter
    def parent_task_log_q(self, value: Deque[str]) -> None:
        self._parent_task_log_q = value

    def exec(self) -> None:
        self._status = (
            TaskStatus.FAILED if not self.work() else TaskStatus.SUCCESS
        )

    def log(self, message: str) -> None:
        if self._parent_task_log_q is not None:
            self._parent_task_log_q.append(message)

    def work(self) -> bool:
        raise NotImplementedError()

    @property
    def task_result(self):
        return self._result

    def pretask_result(self):
        """Get pretask results.

        Defaults to none.
        """


class AbsTask(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def on_completion(self, *args, **kwargs) -> None:
        """Call when task is finished."""

    @abc.abstractmethod
    def exec(self, *args, **kwargs):
        """Execute task."""

    @property
    @abc.abstractmethod
    def status(self) -> TaskStatus:
        """Get the status of the subtask."""


class AbsTaskComponents(metaclass=abc.ABCMeta):
    @property  # type: ignore
    @abc.abstractmethod
    def pretask(self) -> Optional[AbsSubtask]:
        """Get the subtask that run prior to the main task."""

    @pretask.setter  # type: ignore
    @abc.abstractmethod
    def pretask(self, value: AbsSubtask) -> None:
        """Set the subtask that run prior to the main task."""

    @property  # type: ignore
    @abc.abstractmethod
    def posttask(self) -> Optional[AbsSubtask]:
        """Get the subtask that run after the main tasks."""

    @posttask.setter  # type: ignore
    @abc.abstractmethod
    def posttask(self, value: AbsSubtask) -> None:
        """Set the subtask that run after the main tasks."""


class Task(AbsTask, AbsTaskComponents):
    """Task."""

    def __init__(self) -> None:
        """Create a new task."""
        self.log_q: Deque[str] = collections.deque()
        self.result: Any = None
        self._pre_task: Optional[AbsSubtask] = None
        self._post_task: Optional[AbsSubtask] = None

    @property
    def pretask(self) -> Optional[AbsSubtask]:
        return self._pre_task

    @pretask.setter
    def pretask(self, value: AbsSubtask) -> None:
        self._pre_task = value

    @property
    def posttask(self) -> Optional[AbsSubtask]:
        return self._post_task

    @posttask.setter
    def posttask(self, value: AbsSubtask) -> None:
        """Set the post-task sub-task."""
        self._post_task = value

    def on_completion(self, *args, **kwargs) -> None:
        """Run task for after main task is completed.

        Default is a Noop.
        """

    def exec(self, *args, **kwargs):
        """Execute task."""
        raise NotImplementedError()

    @property
    def status(self) -> TaskStatus:
        """Get task status."""
        return super().status


class MultiStageTask(Task):
    name = "Task"

    def __init__(self) -> None:
        """Create a new multi-stage task."""
        super().__init__()
        # Todo: use the results builder from validate
        self._main_subtasks: List[Subtask] = []
        self.working_dir = ""

    @property
    def main_subtasks(self) -> List[Subtask]:
        return self._main_subtasks

    @property
    def subtasks(self) -> List[AbsSubtask]:
        """Get all subtasks."""
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

        raise RuntimeError("Not all statuses are are taken into account")

    @property
    def progress(self) -> float:
        amount_completed = len(
            [
                task
                for task in self.main_subtasks
                if task.status > TaskStatus.WORKING
            ]
        )
        return amount_completed / len(self.main_subtasks)

    def exec(self, *args, **kwargs) -> None:
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
        except Exception as error:
            print(f"Failed {error}", file=sys.stderr)
            raise

    def process_subtask_results(self, subtask_results: List[Any]) -> Any:
        return subtask_results


class AbsTaskBuilder(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def task(self) -> MultiStageTask:
        pass

    @abc.abstractmethod
    def add_subtask(self, task) -> None:
        """Add subtask to builder."""

    @abc.abstractmethod
    def build_task(self):
        """Build task."""

    @abc.abstractmethod
    def set_pretask(self, subtask: AbsSubtask) -> None:
        """Set pre-task subtask."""

    @abc.abstractmethod
    def set_posttask(self, subtask: AbsSubtask) -> None:
        """Set the post-task task."""


class BaseTaskBuilder(AbsTaskBuilder):
    """Task builder base class."""

    def __init__(self) -> None:
        """Create base structure of a task builder class."""
        self._main_subtasks: List[Subtask] = []
        self._pretask: Optional[AbsSubtask] = None
        self._posttask: Optional[AbsSubtask] = None

    def add_subtask(self, task: Subtask) -> None:
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

    def set_pretask(self, subtask: AbsSubtask) -> None:
        self._pretask = subtask

    def set_posttask(self, subtask: AbsSubtask) -> None:
        self._posttask = subtask


class TaskBuilder:
    """Task builder."""

    # The director
    _task_counter = 0

    def __init__(self, builder: BaseTaskBuilder, working_dir: str) -> None:
        """Create a new task builder."""
        self._builder = builder
        self._working_dir = working_dir
        self._subtask_counter = 0
        TaskBuilder._task_counter += 1
        self.task_id = TaskBuilder._task_counter

    def build_task(self) -> MultiStageTask:
        """Build Multi stage task."""
        return self._builder.build_task()

    def add_subtask(self, subtask: Subtask) -> None:
        """Add subtask to builder."""
        self._subtask_counter += 1

        if subtask.name is not None:
            task_type = subtask.name
        else:
            task_type = str(subtask.__class__.__name__)

        task_id = str(self.task_id).zfill(3)
        subtask_id = str(self._subtask_counter).zfill(3)

        task_working_dir = self._build_task_working_path(
            self._working_dir, task_id
        )

        subtask_working_dir = self._build_working_path2(
            task_working_dir, task_type, subtask_id
        )

        subtask.subtask_working_dir = subtask_working_dir
        subtask.task_working_dir = task_working_dir
        self._builder.add_subtask(subtask)

    @staticmethod
    def _build_working_path2(
        task_working_path: str, task_type: str, subtask_id: str
    ) -> str:
        return os.path.join(task_working_path, task_type, str(subtask_id))

    @staticmethod
    def _build_task_working_path(temp_path: str, task_id: str) -> str:
        return os.path.join(temp_path, task_id)

    def set_pretask(self, subtask: Subtask) -> None:
        """Set the pre-subtask for the task."""
        self._subtask_counter += 1

        if subtask.name is not None:
            task_type = subtask.name
        else:
            task_type = str(subtask.__class__.__name__)

        task_id = str(self.task_id).zfill(3)
        subtask_id = str(self._subtask_counter).zfill(3)

        task_working_dir = self._build_task_working_path(
            self._working_dir, task_id
        )

        subtask_working_dir = self._build_working_path2(
            task_working_dir, task_type, subtask_id
        )

        subtask.subtask_working_dir = subtask_working_dir
        subtask.task_working_dir = task_working_dir
        self._builder.set_pretask(subtask)

    def set_posttask(self, subtask: Subtask) -> None:
        """Set the post-subtask for the task."""
        self._subtask_counter += 1

        if subtask.name is not None:
            task_type = subtask.name
        else:
            task_type = str(subtask.__class__.__name__)

        task_id = str(self.task_id).zfill(3)
        subtask_id = str(self._subtask_counter).zfill(3)

        task_working_dir = self._build_task_working_path(
            self._working_dir, task_id
        )

        subtask_working_dir = self._build_working_path2(
            task_working_dir, task_type, subtask_id
        )

        subtask.subtask_working_dir = subtask_working_dir
        subtask.task_working_dir = task_working_dir

        self._builder.set_posttask(subtask)

    @staticmethod
    def save(task_obj: AbsTaskBuilder) -> bytes:
        """Pickle data."""
        task_serialized = TaskBuilder._serialize_task(task_obj)
        return pickle.dumps(task_serialized)

    @staticmethod
    def load(data: bytes) -> AbsTaskBuilder:
        """Load pickled data."""
        task_cls, attributes = pickle.loads(data)
        return TaskBuilder._deserialize_task(task_cls, attributes)

    @staticmethod
    def _serialize_task(
        task_obj: AbsTaskBuilder,
    ) -> typing.Tuple[typing.Type, typing.Dict[str, Any]]:
        return task_obj.__class__, task_obj.__dict__

    @staticmethod
    def _deserialize_task(
        task_cls: typing.Type[AbsTaskBuilder],
        attributes: typing.Dict[str, Any],
    ) -> AbsTaskBuilder:
        obj = task_cls.__new__(task_cls)
        obj.__dict__.update(attributes)
        return obj


class QueueAdapter:
    """Queue adapter class."""

    def __init__(self) -> None:
        """Create a new queue adapter."""
        super().__init__()
        self._queue: "Optional[queue.Queue[str]]" = None

    def append(self, item):
        """Append item to the queue."""
        self._queue.put(item)

    def set_message_queue(self, value: "queue.Queue[str]") -> None:
        """Set message queue."""
        self._queue = value


class MultiStageTaskBuilder(BaseTaskBuilder):
    """Multi stage task builder."""

    def __init__(self, working_dir: str) -> None:
        """Create a new multi-stage task builder."""
        super().__init__()
        self._working_dir = working_dir

    @property
    def task(self) -> MultiStageTask:
        """Get the task."""
        task = MultiStageTask()
        task.working_dir = self._working_dir
        return task
