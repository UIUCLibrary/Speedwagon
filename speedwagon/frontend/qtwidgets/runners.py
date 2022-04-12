"""Qt based runners."""

from __future__ import annotations

import abc
import logging
import tempfile
import typing
import warnings
from types import TracebackType
from typing import Optional, Type, Dict, Any, List, Callable
import contextlib

from PySide6 import QtWidgets, QtCore

import speedwagon
from speedwagon import frontend
from speedwagon import runner_strategies
from speedwagon.frontend import qtwidgets
from speedwagon.job import AbsWorkflow


class QtDialogProgress(frontend.reporter.RunnerDisplay):
    """Qt based dialog box showing progress."""

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
    ) -> None:
        """Create a new Qt based progress dialog box."""
        super().__init__()
        self.dialog = qtwidgets.dialog.WorkProgressBar(parent=parent)
        self.dialog.setMaximum(0)
        self.dialog.setValue(0)

    @property
    def details(self) -> str:
        """Get dialog details."""
        return self.dialog.labelText()

    @details.setter
    def details(self, value: str) -> None:
        if self._details == value:
            return

        self._details = value
        self.dialog.setLabelText(value)
        QtWidgets.QApplication.processEvents()

    @property
    def user_canceled(self) -> bool:
        """Get status of job cancellation."""
        return self.dialog.wasCanceled()

    @property
    def current_task_progress(self) -> typing.Optional[int]:
        """Get the current task number."""
        return super().current_task_progress

    @current_task_progress.setter
    def current_task_progress(self, value: typing.Optional[int]) -> None:
        self._current_task_progress = value
        dialog_value = value or 0
        self.dialog.setValue(dialog_value)

    @property
    def total_tasks_amount(self) -> typing.Optional[int]:
        """Get the total estimated tasks."""
        return super().total_tasks_amount

    @total_tasks_amount.setter
    def total_tasks_amount(self, value: typing.Optional[int]) -> None:
        self._total_tasks_amount = value
        if value is None:
            self.dialog.setMaximum(0)
            return

        self.dialog.setMaximum(value)

    @property
    def title(self) -> str:
        """Get the window title."""
        return self.dialog.windowTitle()

    @title.setter
    def title(self, value: str) -> None:
        self.dialog.setWindowTitle(value)

    def refresh(self) -> None:
        """Process Qt events."""
        QtWidgets.QApplication.processEvents()

        self.current_task_progress = self._current_task_progress
        if (
            self.task_runner is not None
            and self.task_runner.current_task is not None
        ):
            self._update_window_task_info(self.task_runner.current_task)
        if self.task_scheduler is not None:
            self._update_progress(self.task_scheduler)
        QtWidgets.QApplication.processEvents()

    def __enter__(self) -> "QtDialogProgress":
        """Show dialog box."""
        self.dialog.show()
        return self

    def __exit__(self, __exc_type: Optional[Type[BaseException]],
                 __exc_value: Optional[BaseException],
                 __traceback: Optional[TracebackType]):
        """Clean up dialog."""
        self.dialog.accept()
        self.close()
        return super().__exit__(__exc_type, __exc_value, __traceback)

    def close(self) -> None:
        """Close dialog box."""
        self.dialog.close()

    def _update_window_task_info(
            self,
            current_task: speedwagon.tasks.Subtask
    ) -> None:
        self.details = "Processing" \
            if current_task.name is None \
            else current_task.name

    def _update_progress(
            self,
            task_scheduler:
            "speedwagon.runner_strategies.TaskScheduler"
    ) -> None:
        self.total_tasks_amount = task_scheduler.total_tasks
        self.current_task_progress = task_scheduler.current_task_progress


USER_ABORTED_MESSAGE = "User Aborted"


class TaskFailed(Exception):
    """Task has failed."""


class AbsRunner(metaclass=abc.ABCMeta):
    """Abstract base class for running workflows."""

    @abc.abstractmethod
    def run(self, parent: QtWidgets.QWidget, job: AbsWorkflow, options: dict,
            logger: logging.Logger, completion_callback=None) -> None:
        """Run the workflow."""


class UsingExternalManagerForAdapter(AbsRunner):
    """Runner that uses external manager."""

    def __init__(self, manager: speedwagon.worker.ToolJobManager) -> None:
        """Create a new runner."""
        warnings.warn(
            "Use UsingExternalManagerForAdapter2 instead",
            DeprecationWarning
        )
        self._manager = manager

    @staticmethod
    def _update_progress(
            runner: WorkRunnerExternal3,
            current: int,
            total: int) -> None:
        if runner.dialog is not None:
            dialog_box = runner.dialog
            if total != dialog_box.maximum():
                dialog_box.setMaximum(total)
            if current != dialog_box.value():
                dialog_box.setValue(current)

            if current == total:
                dialog_box.accept()

    def run(self,
            parent: QtWidgets.QWidget,
            job: AbsWorkflow,
            options: Dict[str, Any],
            logger: logging.Logger,
            completion_callback=None
            ) -> None:
        """Run adapted."""
        results: List[Any] = []

        temp_dir = tempfile.TemporaryDirectory()
        with temp_dir as build_dir:
            if isinstance(job, AbsWorkflow):
                try:
                    pre_results = self._run_pre_tasks(parent, job, options,
                                                      build_dir, logger)

                    results += pre_results

                    additional_data = \
                        self._get_additional_data(job,
                                                  options,
                                                  parent,
                                                  pre_results)
                    if additional_data:
                        options = {**options, **additional_data}

                except speedwagon.exceptions.JobCancelled:
                    return

                except TaskFailed as error:

                    logger.error(
                        f"Job stopped during pre-task phase. Reason: {error}"
                    )

                    return

                try:
                    results += self._run_main_tasks(parent,
                                                    job,
                                                    options,
                                                    pre_results,
                                                    additional_data,
                                                    build_dir,
                                                    logger)

                except TaskFailed as error:

                    logger.error(
                        f"Job stopped during main tasks phase. Reason: {error}"
                    )

                    return

                try:
                    results += self._run_post_tasks(parent, job, options,
                                                    results, build_dir,
                                                    logger)

                except TaskFailed as error:

                    logger.error(
                        f"Job stopped during post-task phase. Reason: {error}"
                    )

                    return

                logger.debug("Generating report")
                report = job.generate_report(results, **options)
                if report:
                    logger.info(report)

    def _get_additional_data(
            self,
            job: AbsWorkflow,
            options: Dict[str, Any],
            parent: QtWidgets.QWidget,
            pre_results: typing.List[speedwagon.tasks.Result]
    ) -> Dict[str, Any]:
        if isinstance(job, speedwagon.job.Workflow):
            return self._get_additional_options(
                parent,
                job,
                options,
                pre_results.copy()
            )

        return {}

    def _run_main_tasks(self,
                        parent: QtWidgets.QWidget,
                        job: AbsWorkflow,
                        options: Dict[str, Any],
                        pretask_results,
                        additional_data: Dict[str, Any],
                        working_dir: str,
                        logger: logging.Logger
                        ) -> list:

        with self._manager.open(parent=parent,
                                runner=WorkRunnerExternal3) as runner:

            runner.abort_callback = self._manager.abort
            i = -1
            runner.dialog.setRange(0, 0)
            runner.dialog.setWindowTitle(job.name)

            results = []

            try:
                logger.addHandler(runner.progress_dialog_box_handler)

                # Run the main tasks. Keep track of the progress
                metadata_tasks = \
                    job.discover_task_metadata(pretask_results,
                                               additional_data,
                                               **options) or []

                for new_task_metadata in metadata_tasks:

                    main_task_builder = speedwagon.tasks.TaskBuilder(
                        speedwagon.tasks.MultiStageTaskBuilder(working_dir),
                        working_dir
                    )

                    job.create_new_task(main_task_builder, **new_task_metadata)

                    new_task = main_task_builder.build_task()
                    for subtask in new_task.subtasks:
                        i += 1

                        adapted_tool = speedwagon.worker.SubtaskJobAdapter(
                            subtask
                        )

                        self._manager.add_job(adapted_tool,
                                              adapted_tool.settings)

                logger.info("Found %d jobs", i + 1)
                runner.dialog.setMaximum(i)
                self._manager.start()

                runner.dialog.show()

                main_results = self._manager.get_results(
                    lambda x, y: self._update_progress(runner, x, y)
                )

                for result in main_results:
                    if result is not None:
                        results.append(result)
                if runner.was_aborted:
                    raise TaskFailed(USER_ABORTED_MESSAGE)
            finally:
                logger.removeHandler(runner.progress_dialog_box_handler)
            return results

    def _run_post_tasks(self,
                        parent: QtWidgets.QWidget,
                        job: AbsWorkflow,
                        options: Dict[str, Any],
                        results: typing.List[speedwagon.tasks.Result],
                        working_dir: str,
                        logger: logging.Logger) -> list:
        _results = []
        with self._manager.open(parent=parent,
                                runner=frontend.qtwidgets.runners) as runner:

            runner.dialog.setRange(0, 0)
            try:
                logger.addHandler(runner.progress_dialog_box_handler)

                finalization_task_builder = speedwagon.tasks.TaskBuilder(
                    speedwagon.tasks.MultiStageTaskBuilder(working_dir),
                    working_dir
                )

                job.completion_task(finalization_task_builder,
                                    results,
                                    **options)

                task = finalization_task_builder.build_task()
                for subtask in task.main_subtasks:
                    adapted_tool = speedwagon.worker.SubtaskJobAdapter(subtask)
                    self._manager.add_job(adapted_tool, adapted_tool.settings)
                self._manager.start()

                post_results = self._manager.get_results(
                    lambda x, y: self._update_progress(runner, x, y)
                )

                for post_result in post_results:
                    if post_result is not None:
                        _results.append(post_result)

                runner.dialog.accept()
                runner.dialog.close_dialog()
                if runner.was_aborted:
                    raise TaskFailed(USER_ABORTED_MESSAGE)
                return _results
            finally:
                logger.removeHandler(runner.progress_dialog_box_handler)

    def _run_pre_tasks(
            self,
            parent: QtWidgets.QWidget,
            job: AbsWorkflow,
            options: Dict[str, Any],
            working_dir: str,
            logger: logging.Logger
    ) -> List[Any]:

        with self._manager.open(
                parent=parent,
                runner=WorkRunnerExternal3
        ) as runner:

            runner.dialog.setRange(0, 0)
            logger.addHandler(runner.progress_dialog_box_handler)

            results = []

            try:
                task_builder = speedwagon.tasks.TaskBuilder(
                    speedwagon.tasks.MultiStageTaskBuilder(working_dir),
                    working_dir
                )

                job.initial_task(task_builder, **options)

                task = task_builder.build_task()
                for subtask in task.main_subtasks:
                    adapted_tool = speedwagon.worker.SubtaskJobAdapter(subtask)
                    self._manager.add_job(adapted_tool, adapted_tool.settings)

                self._manager.start()

                post_results = self._manager.get_results(
                    lambda x, y: self._update_progress(runner, x, y)
                )

                for post_result in post_results:
                    if post_result is not None:
                        results.append(post_result)

                runner.dialog.accept()
                runner.dialog.close_dialog()
                if runner.was_aborted:
                    raise TaskFailed(USER_ABORTED_MESSAGE)
                return results
            finally:
                logger.removeHandler(runner.progress_dialog_box_handler)

    @staticmethod
    def _get_additional_options(
            parent: QtWidgets.QWidget,
            job: speedwagon.job.Workflow,
            options: Dict[str, Any],
            pretask_results: typing.List[speedwagon.tasks.Result]
    ) -> Dict[str, Any]:

        return job.get_additional_info(parent, options, pretask_results)


class QtRunner(speedwagon.runner.AbsRunner2):
    """Job runner for Qt Widgets."""

    def __init__(self,
                 parent: QtWidgets.QWidget = None) -> None:
        """Create a new runner."""
        self.parent = parent

    @staticmethod
    def update_progress(
            runner: WorkRunnerExternal3,
            current: int,
            total: int) -> None:
        """Update the current job progress."""
        if runner.dialog is None:
            return

        dialog_box = runner.dialog
        if total != dialog_box.maximum():
            dialog_box.setMaximum(total)
        if current != dialog_box.value():
            dialog_box.setValue(current)

        if current == total:
            dialog_box.accept()

    def request_more_info(
            self,
            workflow: speedwagon.job.Workflow,
            options: Dict[str, Any],
            pretask_results: typing.List[speedwagon.tasks.Result]
    ) -> Dict[str, Any]:
        """Request more information from the user."""
        if self.parent is not None and \
                hasattr(workflow, "get_additional_info"):
            return workflow.get_additional_info(
                self.parent, options, pretask_results.copy()
            )
        return {}

    def run(self,
            job: AbsWorkflow,
            options: typing.Dict[str, Any],
            logger: logging.Logger = None,
            completion_callback=None
            ) -> None:
        """Execute run."""
        with tempfile.TemporaryDirectory() as build_dir:
            task_scheduler = \
                speedwagon.runner_strategies.TaskScheduler(
                    working_directory=build_dir
                )

            task_scheduler.reporter = QtDialogProgress(parent=self.parent)

            task_scheduler.logger = logger or logging.getLogger(__name__)

            if isinstance(job, speedwagon.job.Workflow):
                self.run_abs_workflow(
                    task_scheduler=task_scheduler,
                    job=job,
                    options=options,
                    logger=logger
                )

    def run_abs_workflow(
        self,
        task_scheduler: speedwagon.runner_strategies.TaskScheduler,
        job: speedwagon.job.Workflow,
        options: typing.Dict[str, Any],
        logger: logging.Logger = None
    ) -> None:
        """Run workflow."""
        task_scheduler.logger = logger or logging.getLogger(__name__)
        task_scheduler.request_more_info = self.request_more_info
        task_scheduler.run(job, options)


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
                self,
                parent: qtwidgets.dialog.dialogs.WorkflowProgress
        ) -> None:
            """Create a new workprogress callback object."""
            super().__init__(parent)
            self.dialog_box = parent
            self.status_changed.connect(self.set_banner_text)
            self.progress_changed.connect(
                self.dialog_box.set_current_progress
            )
            self.finished.connect(self._finished)
            self.total_jobs_changed.connect(
                self.dialog_box.set_total_jobs)
            self.error.connect(self._error_message)
            self.cancel_complete.connect(
                self.dialog_box.cancel_completed)

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
                traceback: Optional[str] = None
        ) -> None:
            if message is not None:
                self.dialog_box.write_to_console(message)
            self.dialog_box.write_to_console(str(exc), level=logging.ERROR)
            error = QtWidgets.QMessageBox()
            error.setWindowTitle("Workflow Failed")
            error.setIcon(QtWidgets.QMessageBox.Critical)
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
                self,
                result: runner_strategies.JobSuccess
        ) -> None:
            """Signal that job is finished."""
            self.finished.emit(result)
            self.dialog_box.flush()

        def cancelling_complete(self) -> None:
            """Signal that canceling is completed."""
            self.cancel_complete.emit()
            self.dialog_box.flush()

        def update_progress(self, current: Optional[int],
                            total: Optional[int]) -> None:
            """Update the progress completed."""
            if total is not None:
                self.total_jobs_changed.emit(total)
            if current is not None:
                self.progress_changed.emit(current)

        def submit_error(
                self,
                message: Optional[str] = None,
                exc: Optional[BaseException] = None,
                traceback_string: Optional[str] = None
        ) -> None:
            """Submit an error or exception."""
            self.error.emit(message, exc, traceback_string)

    def __init__(
            self,
            dialog_box: qtwidgets.dialog.dialogs.WorkflowProgress
    ) -> None:
        """Create a new callback for a dialog box."""
        super().__init__()

        self.signals = WorkflowProgressCallbacks.WorkflowSignals(dialog_box)

        self.log_handler = \
            qtwidgets.logging_helpers.SignalLogHandler(
                signal=self.signals.message
            )

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
            traceback_string: Optional[str] = None
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

    def update_progress(self, current: Optional[int],
                        total: Optional[int]) -> None:
        """Update the progress."""
        self.signals.update_progress(current, total)

    def status(self, text: str) -> None:
        """Set the status."""
        self.signals.set_status(text)


class WorkRunnerExternal3(contextlib.AbstractContextManager):
    """Work runner that uses external manager."""

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
    ) -> None:
        """Create a work runner."""
        self.results: typing.List[speedwagon.tasks.Result] = []
        self._parent = parent
        self.abort_callback: Optional[Callable[[], None]] = None
        self.was_aborted = False
        self._dialog: Optional[
            frontend.qtwidgets.dialog.WorkProgressBar
        ] = None
        # self.progress_dialog_box_handler: \
        #     Optional[ProgressMessageBoxLogHandler] = None

    @property
    def dialog(self) -> Optional[frontend.qtwidgets.dialog.WorkProgressBar]:
        """Get the progress bar dialog."""
        warnings.warn("Don't use the dialog", DeprecationWarning)
        return self._dialog

    @dialog.setter
    def dialog(
            self,
            value: Optional[frontend.qtwidgets.dialog.WorkProgressBar]
    ) -> None:
        self._dialog = value

    def __enter__(self) -> WorkRunnerExternal3:
        """Start worker."""
        self.dialog = \
            speedwagon.frontend.qtwidgets.dialog.WorkProgressBar(self._parent)

        self.dialog.close()
        return self

    def abort(self) -> None:
        """Abort on any running tasks."""
        self.was_aborted = True
        if callable(self.abort_callback):
            self.abort_callback()  # pylint: disable=not-callable

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_value: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None:
        """Close runner."""
        if self.dialog is None:
            raise AttributeError("dialog was set to None before closing")

        self.dialog.close()
