"""Qt based runners."""

from __future__ import annotations

import abc
import logging
from typing import Optional, TYPE_CHECKING

from PySide6 import QtWidgets, QtCore

from speedwagon import runner_strategies

if TYPE_CHECKING:
    from speedwagon.job import AbsWorkflow
    from speedwagon.frontend import qtwidgets

USER_ABORTED_MESSAGE = "User Aborted"


class TaskFailed(Exception):
    """Task has failed."""


class AbsRunner(metaclass=abc.ABCMeta):
    """Abstract base class for running workflows."""

    @abc.abstractmethod
    def run(
        self,
        parent: QtWidgets.QWidget,
        job: AbsWorkflow,
        options: dict,
        logger: logging.Logger,
        completion_callback=None,
    ) -> None:
        """Run the workflow."""


class WorkflowProgressCallbacks(runner_strategies.AbsJobCallbacks):
    """Callback class for communicating between Qt and Python."""

    class WorkflowSignals(QtCore.QObject):
        """Signals for communicating with Qt."""

        error = QtCore.Signal(object, object, object)
        progress_changed = QtCore.Signal(int)
        total_jobs_changed = QtCore.Signal(int)
        cancel_complete = QtCore.Signal()
        message = QtCore.Signal(str, int)
        status_changed = QtCore.Signal(str)
        started = QtCore.Signal()
        finished = QtCore.Signal(runner_strategies.JobSuccess)

        def __init__(
            self, parent: qtwidgets.dialog.dialogs.WorkflowProgress
        ) -> None:
            """Create a new workprogress callback object."""
            super().__init__(parent)
            self.dialog_box = parent
            self.status_changed.connect(self.set_banner_text)
            self.progress_changed.connect(self.dialog_box.set_current_progress)
            self.finished.connect(self._finished)
            self.total_jobs_changed.connect(self.dialog_box.set_total_jobs)
            self.error.connect(self._error_message)
            self.cancel_complete.connect(self.dialog_box.cancel_completed)

            self.started.connect(self.dialog_box.show)

            self.status_changed.connect(self.dialog_box.flush)
            self.message.connect(self.dialog_box.write_to_console)

        def log(self, text: str, level: int) -> None:
            """Log a message."""
            self.message.emit(text, level)

        @QtCore.Slot(str)
        def set_banner_text(self, text: str) -> None:
            """Set the banner text."""
            self.dialog_box.banner.setText(text)

        def set_status(self, text: str) -> None:
            """Set the status of the job."""
            self.status_changed.emit(text)

        def _error_message(
            self,
            message: Optional[str] = None,
            exc: Optional[BaseException] = None,
            traceback: Optional[str] = None,
        ) -> None:
            if message is not None:
                self.dialog_box.write_to_console(message)
            self.dialog_box.write_to_console(str(exc), level=logging.ERROR)
            error = QtWidgets.QMessageBox()
            error.setWindowTitle("Workflow Failed")
            error.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            error.setText(message or f"An error occurred: {exc}")
            if traceback is not None:
                error.setDetailedText(traceback)
            error.exec()
            self.dialog_box.failed()

        @QtCore.Slot(object)
        def _finished(self, results) -> None:
            if results in [
                runner_strategies.JobSuccess.SUCCESS,
                runner_strategies.JobSuccess.ABORTED,
            ]:
                self.dialog_box.success_completed()
            elif results in [
                runner_strategies.JobSuccess.FAILURE,
            ]:
                self.dialog_box.reject()

        def finished_called(
            self, result: runner_strategies.JobSuccess
        ) -> None:
            """Signal that job is finished."""
            self.finished.emit(result)
            self.dialog_box.flush()

        def cancelling_complete(self) -> None:
            """Signal that canceling is completed."""
            self.cancel_complete.emit()
            self.dialog_box.flush()

        def update_progress(
            self, current: Optional[int], total: Optional[int]
        ) -> None:
            """Update the progress completed."""
            if total is not None:
                self.total_jobs_changed.emit(total)
            if current is not None:
                self.progress_changed.emit(current)

        def submit_error(
            self,
            message: Optional[str] = None,
            exc: Optional[BaseException] = None,
            traceback_string: Optional[str] = None,
        ) -> None:
            """Submit an error or exception."""
            self.error.emit(message, exc, traceback_string)

    def __init__(
        self, dialog_box: qtwidgets.dialog.dialogs.WorkflowProgress
    ) -> None:
        """Create a new callback for a dialog box."""
        super().__init__()

        self.signals = WorkflowProgressCallbacks.WorkflowSignals(dialog_box)

    def log(self, text: str, level: int = logging.INFO) -> None:
        """Send a log message."""
        self.signals.log(text, level)

    def set_banner_text(self, text: str) -> None:
        """Write a text message on the banner."""
        self.signals.set_banner_text(text)

    def error(
        self,
        message: Optional[str] = None,
        exc: Optional[BaseException] = None,
        traceback_string: Optional[str] = None,
    ) -> None:
        """Signal an error message."""
        self.signals.submit_error(message, exc, traceback_string)

    def start(self) -> None:
        """Signal ready to start."""
        self.signals.started.emit()
        self.signals.dialog_box.start()

    def finished(self, result: runner_strategies.JobSuccess) -> None:
        """Signal that everything is finished."""
        self.signals.finished_called(result)

    def cancelling_complete(self) -> None:
        """Signal that cancel is completed."""
        self.signals.cancelling_complete()

    def refresh(self) -> None:
        """Process Qt events."""
        QtCore.QCoreApplication.processEvents()

    def update_progress(
        self, current: Optional[int], total: Optional[int]
    ) -> None:
        """Update the progress."""
        self.signals.update_progress(current, total)

    def status(self, text: str) -> None:
        """Set the status."""
        self.signals.set_status(text)
