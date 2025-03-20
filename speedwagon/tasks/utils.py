"""Utility classes for creating tasks."""

from typing import TypeVar, Generic, Callable, List, Iterable

T = TypeVar("T")
_I = TypeVar("_I")


class TaskBuilder(Generic[_I, T]):
    """Builder for creating and configure tasks."""

    def __init__(self, task_configuration_func: Callable[[_I], T]) -> None:
        """Create a new TaskBuilder object.

        Args:
            task_configuration_func: callable that takes a task, configures
                it, and returns it.
        """
        self._config_task = task_configuration_func
        self._tasks: List[_I] = []

    def add(self, task: _I) -> None:
        """Add a task to the builder."""
        self._tasks.append(task)

    def iter_tasks(self) -> Iterable[T]:
        """Iterate over configured tasks."""
        for task in self._tasks:
            yield self._config_task(task)
