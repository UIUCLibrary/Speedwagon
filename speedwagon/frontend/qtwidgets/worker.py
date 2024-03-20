"""Workers for Qt widgets.

Refactored and extracted from speedwagon/worker.py.

Notes:
    This is intended to be removed. Use at own risk!!!

"""
from __future__ import annotations

import abc
import multiprocessing
import queue
from abc import ABC
from typing import Callable
import typing
import warnings
import concurrent.futures

from PySide6 import QtWidgets

import speedwagon.worker

if typing.TYPE_CHECKING:
    import speedwagon.config


class ToolJobManager(speedwagon.worker.AbsToolJobManager):
    """Tool job manager."""

    def __init__(self) -> None:
        """Don't use this."""
        warnings.warn("Don't use", DeprecationWarning, stacklevel=2)
        super().__init__()

    def flush_message_buffer(self) -> None:
        """Flush any messages in the buffer to the logger."""
        self._job_runtime.flush_message_buffer(self.logger)

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

                futures = concurrent.futures.as_completed(
                    still_running, timeout=0.1
                )

                for i, _ in enumerate(futures):
                    dialog_box.setValue(i + 1)

                break
            except concurrent.futures.TimeoutError:
                continue

        self.logger.info("Cancelled")
        self.flush_message_buffer()
        dialog_box.accept()

    def get_results(
        self,
        timeout_callback: typing.Optional[Callable[[int, int], None]] = None,
    ) -> typing.Generator[typing.Any, None, None]:
        """Process jobs and return results."""
        processor = QtJobProcessor(
            typing.cast(speedwagon.worker.ToolJobManager, self)
        )
        processor.timeout_callback = timeout_callback
        yield from processor.process()


class QtJobProcessor(speedwagon.worker.JobProcessor):
    """Job processor for Qt Widgets."""

    def refresh_events(self):
        """Update any pending Qt events."""
        QtWidgets.QApplication.processEvents()


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
        warnings.warn("Don't use", DeprecationWarning, stacklevel=2)
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
        self, job: speedwagon.worker.ProcessJobWorker, **job_args
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
