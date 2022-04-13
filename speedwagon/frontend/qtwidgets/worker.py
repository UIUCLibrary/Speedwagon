"""Workers for Qt widgets.

Refactored and extracted from speedwagon/worker.py.

Notes:
    This is intended to be removed. Use at own risk!!!

"""
from __future__ import annotations

import abc
import contextlib
import multiprocessing
import queue
import sys
import traceback
from abc import ABC
from types import TracebackType
from typing import Optional, Type, Dict, Any, Callable
import typing
import warnings
import logging
import concurrent.futures

from PySide6 import QtWidgets

import speedwagon.worker

if typing.TYPE_CHECKING:
    import speedwagon.config


class ToolJobManager(
    contextlib.AbstractContextManager,
    speedwagon.worker.AbsJobManager
):
    """Tool job manager."""

    def __init__(self) -> None:
        """Create a tool job manager."""
        self.settings_path: Optional[str] = None
        self._job_runtime = speedwagon.worker.JobExecutor()
        self.logger = logging.getLogger(__name__)
        self.user_settings: Optional["speedwagon.config.AbsConfig"] = None
        self.configuration_file: Optional[str] = None

    @property
    def active(self) -> bool:
        """Check if a job is active."""
        return self._job_runtime.active

    @active.setter
    def active(self, value: bool) -> None:
        warnings.warn("don't use directly", DeprecationWarning)
        self._job_runtime.active = value

    @property
    def futures(self) -> typing.List[concurrent.futures.Future]:
        """Get the futures."""
        return self._job_runtime.futures

    def __enter__(self) -> "ToolJobManager":
        """Startup job management and load a worker pool."""
        self._job_runtime._message_queue = self._job_runtime.manager.Queue()

        self._job_runtime._executor = concurrent.futures.ProcessPoolExecutor(1)

        return self

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_value: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None:
        """Clean up manager and show down the executor."""
        self._job_runtime.cleanup(self.logger)
        self._job_runtime.shutdown()

    def open(self, parent, runner, *args, **kwargs):
        """Open a runner with the a given job arguments."""
        return runner(*args, **kwargs, parent=parent)

    def add_job(self,
                new_job: speedwagon.worker.ProcessJobWorker,
                settings: Dict[str, Any]) -> None:
        """Add job to the run queue."""
        self._job_runtime.add_job(new_job, settings)

    def start(self) -> None:
        """Start jobs."""
        self._job_runtime.start()

    def abort(self) -> None:
        """Abort jobs."""
        still_running: typing.List[concurrent.futures.Future] = []

        dialog_box = speedwagon.frontend.qtwidgets.dialog.WorkProgressBar()
        dialog_box.setWindowTitle("Canceling")
        self._job_runtime.abort()

        dialog_box.setRange(0, len(still_running))
        dialog_box.setLabelText("Please wait")
        dialog_box.show()
        # TODO: set cancel dialog to force the cancellation of the future

        while True:

            try:
                QtWidgets.QApplication.processEvents()

                futures = concurrent.futures.as_completed(still_running,
                                                          timeout=.1)

                for i, _ in enumerate(futures):
                    dialog_box.setValue(i + 1)

                break
            except concurrent.futures.TimeoutError:
                continue

        self.logger.info("Cancelled")
        self.flush_message_buffer()
        dialog_box.accept()

    # TODO: refactor to use an overloaded method instead of a callback
    def get_results(self,
                    timeout_callback: Callable[[int, int], None] = None
                    ) -> typing.Generator[typing.Any, None, None]:
        """Process jobs and return results."""
        processor = JobProcessor(self)
        processor.timeout_callback = timeout_callback
        yield from processor.process()

    def flush_message_buffer(self) -> None:
        """Flush any messages in the buffer to the logger."""
        self._job_runtime.flush_message_buffer(self.logger)

    def _cleanup(self) -> None:
        self._job_runtime.cleanup(self.logger)


class JobProcessor:
    """Job processor for Qt Widgets."""

    def __init__(self, parent: "ToolJobManager"):
        """Create a Job Processor object."""
        warnings.warn("Don't use", DeprecationWarning)
        self._parent = parent
        self.completed = 0
        self._total_jobs = None
        self.timeout_callback: Optional[Callable[[int, int], None]] = None

    @staticmethod
    def report_results_from_future(futures):
        """Get the results from the futures."""
        for i, (future, reported) in enumerate(futures):

            if not reported and future.done():
                result = future.result()
                yield result
                futures[i] = future, True

    def process(self):
        """Process job in queue."""
        self._total_jobs = len(self._parent.futures)
        total_jobs = self._total_jobs
        futures = [(i, False) for i in self._parent.futures]

        while self._parent.active:
            try:
                yield from self._process_all_futures(futures)

                self._parent.active = False
                futures.clear()
                self._parent.flush_message_buffer()

            except concurrent.futures.TimeoutError:
                self._parent.flush_message_buffer()
                if callable(self.timeout_callback):
                    self.timeout_callback(self.completed, total_jobs)
                QtWidgets.QApplication.processEvents()
                if self._parent.active:
                    continue
            except concurrent.futures.process.BrokenProcessPool as error:
                traceback.print_tb(error.__traceback__)
                print(error, file=sys.stderr)
                raise
            self._parent.flush_message_buffer()

    def _process_all_futures(self, futures):
        for completed_futures in concurrent.futures.as_completed(
                self._parent.futures,
                timeout=0.01):
            self._parent.flush_message_buffer()
            if not completed_futures.cancel() and \
                    completed_futures.done():
                self.completed += 1
                if completed_futures in self._parent.futures:
                    self._parent.futures.remove(completed_futures)
                if self.timeout_callback:
                    self.timeout_callback(self.completed, self._total_jobs)
                yield from self.report_results_from_future(futures)

            if self.timeout_callback:
                self.timeout_callback(self.completed, self._total_jobs)


class UIWorker(speedwagon.worker.Worker, ABC):
    """QtWidgets base class for making workers."""

    def __init__(self, parent) -> None:
        """Interface for managing jobs.

        Designed handle loading and executing jobs.

        Args:
            parent: The widget controlling the worker
        """
        super().__init__()
        self.parent = parent
        self._jobs_queue: queue.Queue[typing.Any] = queue.Queue()


class ProcessWorker(UIWorker):
    """Process based worker for QtWidgets."""

    executor = concurrent.futures.ProcessPoolExecutor(max_workers=1)

    def __init__(self, *args, **kwargs) -> None:
        """Create a process worker."""
        super().__init__(*args, **kwargs)
        warnings.warn("Don't use", DeprecationWarning)
        self.manager = multiprocessing.Manager()
        self._message_queue = self.manager.Queue()
        self._results = None
        self._tasks: typing.List[concurrent.futures.Future] = []

    @classmethod
    def initialize_worker(cls, max_workers: int = 1) -> None:
        """Initialize the work pool."""
        cls.executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        )  # TODO: Fix this

    def cancel(self) -> None:
        """Cancel the job."""
        self.executor.shutdown()

    @classmethod
    def _exec_job(cls, job, args, message_queue) -> concurrent.futures.Future:
        new_job = job()
        new_job.mq = message_queue
        fut = cls.executor.submit(new_job.execute, **args)
        return fut

    def add_job(
            self,
            job: speedwagon.worker.ProcessJobWorker,
            **job_args
    ) -> None:
        """Add job to job queue."""
        new_job = speedwagon.worker.JobPair(job, args=job_args)
        self._jobs_queue.put(new_job)

    def run_all_jobs(self) -> None:
        """Run all jobs."""
        while self._jobs_queue.qsize() != 0:
            job_, args, message_queue = self._jobs_queue.get()
            fut = self._exec_job(job_, args, message_queue)
            self._tasks.append(fut)
        for future in concurrent.futures.as_completed(self._tasks):
            self.complete_task(future)
        self.on_completion(results=self._results)

    @abc.abstractmethod
    def complete_task(self, fut: concurrent.futures.Future) -> None:
        """Complete task."""

    @abc.abstractmethod
    def on_completion(self, *args, **kwargs) -> None:
        """Run the subtask designed to be run after main task."""
