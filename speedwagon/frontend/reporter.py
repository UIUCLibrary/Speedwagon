"""Reporters of jobs."""
from __future__ import annotations
import contextlib
import abc
import typing
from types import TracebackType
from typing import Optional, Type

if typing.TYPE_CHECKING:
    from speedwagon.runner_strategies import TaskDispatcher, TaskScheduler


class RunnerDisplay(contextlib.AbstractContextManager, abc.ABC):
    """Runner display."""

    def __init__(self) -> None:
        """Create a new runner display object."""
        super().__init__()

        self.task_runner: typing.Optional[TaskDispatcher] = None
        self.task_scheduler: typing.Optional[TaskScheduler] = None
        self._total_tasks_amount: typing.Optional[int] = None
        self._current_task_progress: typing.Optional[int] = None
        self._details: typing.Optional[str] = None
        self._title: typing.Optional[str] = None

    @property
    def title(self) -> typing.Optional[str]:
        """Get the title."""
        return self._title

    @title.setter
    def title(self, value: typing.Optional[str]) -> None:
        self._title = value

    @property
    def total_tasks_amount(self) -> typing.Optional[int]:
        """Get total number of tasks."""
        return self._total_tasks_amount

    @total_tasks_amount.setter
    def total_tasks_amount(self, value: typing.Optional[int]) -> None:
        self._total_tasks_amount = value

    @abc.abstractmethod
    def refresh(self) -> None:
        """Refresh the display info."""

    @property
    def current_task_progress(self) -> typing.Optional[int]:
        """Get the current task progress."""
        return self._current_task_progress

    @current_task_progress.setter
    def current_task_progress(self, value: typing.Optional[int]) -> None:
        self._current_task_progress = value

    @property
    @abc.abstractmethod
    def user_canceled(self) -> bool:
        """Check if the user has signaled a canceled."""

    @property
    def details(self) -> typing.Optional[str]:
        """Get the details."""
        return self._details

    @details.setter
    def details(self, value: str) -> None:
        self._details = value

    def __enter__(self) -> "RunnerDisplay":
        """Open."""
        return self

    def __exit__(
        self,
        __exc_type: Optional[Type[BaseException]],
        __exc_value: Optional[BaseException],
        __traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        """Clean up."""
        return None
