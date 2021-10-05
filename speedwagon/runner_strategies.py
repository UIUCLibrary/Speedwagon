"""Defining execution of a given workflow steps and processes."""

import abc
import contextlib
import dataclasses
import enum

import logging
import queue
import tempfile
import threading
import typing
import warnings
from types import TracebackType
from typing import List, Any, Dict, Optional, Type
from PyQt5 import QtWidgets

import speedwagon
import speedwagon.dialog
from speedwagon import worker
from .job import AbsWorkflow, Workflow, JobCancelled, available_workflows

__all__ = [
    "RunRunner",
    "UsingExternalManagerForAdapter"
]

USER_ABORTED_MESSAGE = "User Aborted"

module_logger = logging.getLogger(__name__)


class TaskFailed(Exception):
    pass


class AbsEvents(abc.ABC):

    @abc.abstractmethod
    def stop(self) -> None:
        pass

    @abc.abstractmethod
    def is_stopped(self) -> bool:
        pass


class AbsJobCallbacks(abc.ABC):
    @abc.abstractmethod
    def error(
            self,
            message: Optional[str] = None,
            exc: Optional[BaseException] = None
    ) -> None:
        """Had an error"""

    def refresh(self) -> None:
        """Refresh."""

    @abc.abstractmethod
    def done(self) -> None:
        """Job is done."""

    def update_progress(
            self,
            current: Optional[int],
            total: Optional[int]
    ) -> None:
        """Update the job's progress."""


# pylint: disable=too-few-public-methods
class AbsRunner(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def run(self, parent: QtWidgets.QWidget, job: AbsWorkflow, options: dict,
            logger: logging.Logger, completion_callback=None) -> None:
        pass


# pylint: disable=too-few-public-methods
class AbsRunner2(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def run(self, job: AbsWorkflow,
            options: dict,
            logger: logging.Logger, completion_callback=None) -> None:
        pass


class RunRunner:
    """Context for running AbsRunner2 strategies."""

    def __init__(self, strategy: AbsRunner2) -> None:
        """Create a new runner executor."""
        self._strategy = strategy

    def run(self,
            tool: AbsWorkflow,
            options: typing.Dict[str, Any],
            logger: logging.Logger,
            completion_callback=None) -> None:
        """Execute runner job."""
        self._strategy.run(tool, options, logger, completion_callback)


class UsingExternalManagerForAdapter(AbsRunner):
    """Runner that uses external manager."""

    def __init__(self, manager: "worker.ToolJobManager") -> None:
        """Create a new runner."""
        warnings.warn(
            "Use UsingExternalManagerForAdapter2 instead",
            DeprecationWarning
        )
        self._manager = manager

    @staticmethod
    def _update_progress(
            runner: "worker.WorkRunnerExternal3",
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

                except JobCancelled:
                    return

                except TaskFailed as error:

                    logger.error(
                        "Job stopped during pre-task phase. "
                        "Reason: {}".format(error)
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
                        "Job stopped during main tasks phase. "
                        "Reason: {}".format(error)
                    )

                    return

                try:
                    results += self._run_post_tasks(parent, job, options,
                                                    results, build_dir,
                                                    logger)

                except TaskFailed as error:

                    logger.error(
                        "Job stopped during post-task phase. "
                        "Reason: {}".format(error)
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
        if isinstance(job, Workflow):
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
                                runner=worker.WorkRunnerExternal3) as runner:

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
                                runner=worker.WorkRunnerExternal3) as runner:

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
                runner.dialog.close()
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
                runner=worker.WorkRunnerExternal3
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
                runner.dialog.close()
                if runner.was_aborted:
                    raise TaskFailed(USER_ABORTED_MESSAGE)
                return results
            finally:
                logger.removeHandler(runner.progress_dialog_box_handler)

    @staticmethod
    def _get_additional_options(
            parent: QtWidgets.QWidget,
            job: Workflow,
            options: Dict[str, Any],
            pretask_results: typing.List[speedwagon.tasks.Result]
    ) -> Dict[str, Any]:

        return job.get_additional_info(parent, options, pretask_results)


class TaskGenerator:

    def __init__(
            self,
            workflow: Workflow,
            options: typing.Mapping[str, Any],
            working_directory: str,

            caller: typing.Optional["TaskScheduler"] = None

    ) -> None:
        self.workflow = workflow
        self.options = options
        self.working_directory = working_directory
        self.current_task: typing.Optional[int] = None
        self.total_task: typing.Optional[int] = None
        self.caller = caller

    def generate_report(
            self, results: List[speedwagon.tasks.Result]
    ) -> typing.Optional[str]:
        return self.workflow.generate_report(results, **self.options)

    def tasks(self) -> typing.Iterable[speedwagon.tasks.Subtask]:
        pretask_results = []

        results = []

        for pre_task in self.get_pre_tasks(
            self.working_directory, **self.options
        ):
            yield pre_task
            pretask_results.append(pre_task.task_result)
            results.append(pre_task.task_result)
        if self.caller is not None:
            additional_data = self.caller.request_more_info(
                self.workflow,
                self.options,
                pretask_results
            )
        else:
            warnings.warn("No way to request info from user")
            additional_data = {}

        for task in self.get_main_tasks(
            self.working_directory,
            pretask_results=pretask_results,
            additional_data=additional_data,
            **self.options
        ):
            yield task
            results.append(task.task_result)

        yield from self.get_post_tasks(
            working_directory=self.working_directory,
            results=results,
            **self.options
        )

    def get_pre_tasks(
            self,
            working_directory: str,
            **options: typing.Any
    ) -> typing.Iterable[speedwagon.tasks.Subtask]:

        task_builder = speedwagon.tasks.TaskBuilder(
            speedwagon.tasks.MultiStageTaskBuilder(working_directory),
            working_directory
        )
        self.workflow.initial_task(task_builder=task_builder, **options)
        yield from task_builder.build_task().main_subtasks

    def get_main_tasks(
            self,
            working_directory: str,
            pretask_results,
            additional_data,
            **options: typing.Any
    ) -> typing.Iterable[speedwagon.tasks.Subtask]:
        metadata_tasks = \
            self.workflow.discover_task_metadata(
                pretask_results,
                additional_data,
                **options
            ) or []

        subtasks_generated = []
        for task_metadata in metadata_tasks:
            task_builder = speedwagon.tasks.TaskBuilder(
                speedwagon.tasks.MultiStageTaskBuilder(working_directory),
                working_directory
            )
            self.workflow.create_new_task(task_builder, **task_metadata)
            subtasks = task_builder.build_task()
            subtasks_generated += subtasks.main_subtasks

        self.current_task = 0
        self.total_task = len(subtasks_generated)
        for task in subtasks_generated:
            self.current_task += 1
            yield task

    def get_post_tasks(
            self,
            working_directory: str,
            results: typing.Iterable[typing.Optional[
                speedwagon.tasks.Result]],
            **options: typing.Any
    ) -> typing.Iterable[speedwagon.tasks.Subtask]:
        task_builder = speedwagon.tasks.TaskBuilder(
            speedwagon.tasks.MultiStageTaskBuilder(working_directory),
            working_directory
        )
        self.workflow.completion_task(task_builder, results, **options)
        yield from task_builder.build_task().main_subtasks


class RunnerDisplay(contextlib.AbstractContextManager, abc.ABC):

    def __init__(self) -> None:
        super().__init__()
        self.task_runner: typing.Optional[TaskDispatcher] = None
        self.task_scheduler: typing.Optional[TaskScheduler] = None
        self._total_tasks_amount: typing.Optional[int] = None
        self._current_task_progress: typing.Optional[int] = None
        self._details: typing.Optional[str] = None
        self._title: typing.Optional[str] = None

    @property
    def title(self) -> typing.Optional[str]:
        return self._title

    @title.setter
    def title(self, value: typing.Optional[str]) -> None:
        self._title = value

    @property
    def total_tasks_amount(self) -> typing.Optional[int]:
        return self._total_tasks_amount

    @total_tasks_amount.setter
    def total_tasks_amount(self, value: typing.Optional[int]) -> None:
        self._total_tasks_amount = value

    @abc.abstractmethod
    def refresh(self) -> None:
        """Refresh the display info."""

    @property
    def current_task_progress(self) -> typing.Optional[int]:
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
        return self._details

    @details.setter
    def details(self, value: str) -> None:
        self._details = value

    def __enter__(self) -> "RunnerDisplay":
        return self

    def __exit__(self, __exc_type: Optional[Type[BaseException]],
                 __exc_value: Optional[BaseException],
                 __traceback: Optional[TracebackType]) -> Optional[bool]:
        return None


class QtDialogProgress(RunnerDisplay):

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__()
        self.dialog = speedwagon.dialog.WorkProgressBar(parent=parent)
        self.dialog.setMaximum(0)
        self.dialog.setValue(0)

    @property
    def details(self) -> str:
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
        return self.dialog.wasCanceled()

    @property
    def current_task_progress(self) -> typing.Optional[int]:
        return super().current_task_progress

    @current_task_progress.setter
    def current_task_progress(self, value: typing.Optional[int]) -> None:
        self._current_task_progress = value
        dialog_value = value or 0
        self.dialog.setValue(dialog_value)

    @property
    def total_tasks_amount(self) -> typing.Optional[int]:
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
        return self.dialog.windowTitle()

    @title.setter
    def title(self, value: str) -> None:
        self.dialog.setWindowTitle(value)

    def refresh(self) -> None:
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

        self.dialog.show()
        return self

    def __exit__(self, __exc_type: Optional[Type[BaseException]],
                 __exc_value: Optional[BaseException],
                 __traceback: Optional[TracebackType]):
        self.dialog.accept()
        self.close()
        return super().__exit__(__exc_type, __exc_value, __traceback)

    def close(self) -> None:
        self.dialog.close()

    def _update_window_task_info(
            self,
            current_task: speedwagon.tasks.Subtask
    ) -> None:
        self.details = "Processing" \
            if current_task.name is None \
            else current_task.name

    def _update_progress(self, task_scheduler: "TaskScheduler") -> None:
        self.total_tasks_amount = task_scheduler.total_tasks
        self.current_task_progress = task_scheduler.current_task_progress


class AbsTaskDispatcherState(abc.ABC):
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if not hasattr(cls, "state_name"):
            raise NotImplementedError(
                f"{cls.__name__} requires class property 'state_name' to be "
                f"implemented"
            )

    def __init__(self, context: "TaskDispatcher"):
        self.parent = context

    @abc.abstractmethod
    def active(self) -> bool:
        """Get the active status of the task."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop dispatching tasks to run."""

    @abc.abstractmethod
    def start(self) -> None:
        """Star dispatching tasks from the queue to run."""


class TaskDispatcherIdle(AbsTaskDispatcherState):
    state_name = "Idle"

    def active(self) -> bool:
        return False

    def stop(self) -> None:
        """Do nothing.

        Stopping an idle thread is a no-op.
        """

    def start(self) -> None:
        self.parent.current_state = TaskDispatcherRunning(self.parent)
        self.parent.current_state.run_thread()


class TaskDispatcherRunning(AbsTaskDispatcherState):
    state_name = "Running"

    def run_thread(self) -> None:
        logger = logging.getLogger(__name__)

        logger.debug("Starting processing thread")
        self.parent.thread = threading.Thread(
            name="processing_thread",
            target=self.processing_process,
            kwargs={
                "stop_event": self.parent.signals["stop"],
                "job_finished_event": self.parent.signals['finished']
            }
        )
        self.parent.thread.start()

    def processing_process(
            self,
            stop_event: threading.Event,
            job_finished_event: threading.Event
    ) -> None:
        logger = self.parent.logger
        logger.debug("Processing thread is available")

        while not stop_event.is_set():
            if self.parent.job_queue.empty():
                continue

            task = typing.cast(speedwagon.tasks.Subtask,
                               self.parent.job_queue.get())

            task_description = task.task_description()
            if task_description is not None:
                logger.info(task_description)

            logger.debug(
                "Threaded worker received task: [%s](%s)",
                task.name,
                task.task_description()
            )

            self.parent.current_task = task
            task.log = lambda message: logger.info(msg=message)
            task.exec()
            logger.debug(
                "Threaded worker completed task: [%s]",
                task.name
            )

            self.parent.job_queue.task_done()
        job_finished_event.set()

    def active(self) -> bool:
        if self.parent.thread is None:
            return False
        return self.parent.thread.is_alive()

    def stop(self) -> None:
        self.parent.current_state = TaskDispatcherStopping(self.parent)
        self.parent.current_state.halt_dispatching()

    def start(self) -> None:
        self.parent.logger.warning(
            "Processing thread is already started"
        )


class TaskDispatcherStopping(AbsTaskDispatcherState):
    state_name = "Stopping"

    def halt_dispatching(self) -> None:
        self.parent.signals["stop"].set()
        if self.parent.thread is not None:
            self.parent.logger.debug("Processing thread is stopping")
            self.parent.thread.join()
        self.parent.logger.debug("Processing thread has stopped")
        self.parent.current_state = TaskDispatcherIdle(self.parent)

    def active(self) -> bool:
        if self.parent.thread is None:
            return False
        return self.parent.thread.is_alive()

    def stop(self) -> None:
        self.parent.logger.warning("Processing thread is currently stopping")

    def start(self) -> None:
        self.parent.logger.warning(
            "Unable to start while processing is stopping"
        )


class TaskDispatcher:

    def __init__(self,
                 job_queue: queue.Queue,
                 logger: typing.Optional[logging.Logger] = None) -> None:
        super().__init__()
        self.job_queue = job_queue
        self.signals: typing.Mapping[str, threading.Event] = {
            "stop": threading.Event(),
            "finished": threading.Event()
        }
        self.thread: typing.Optional[threading.Thread] = None
        self.current_task: Optional[speedwagon.tasks.Subtask] = None
        self.logger = logger or logging.getLogger(__name__)
        self.current_state: AbsTaskDispatcherState = TaskDispatcherIdle(self)

    @property
    def active(self) -> bool:
        return self.current_state.active()

    def stop(self) -> None:
        self.current_state.stop()

    def __enter__(self) -> "TaskDispatcher":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    def start(self) -> None:
        self.current_state.start()


class TaskScheduler:

    def __init__(self, working_directory: str) -> None:
        self.logger = logging.getLogger(__name__)
        self.working_directory = working_directory
        self.reporter: Optional[RunnerDisplay] = None

        self.current_task_progress: typing.Optional[int] = None
        self.total_tasks: typing.Optional[int] = None
        self._task_queue: "queue.Queue" = queue.Queue(maxsize=1)

        self._request_more_info: typing.Callable[
            [Workflow, Any, Any], typing.Optional[Dict[str, Any]]
        ] = lambda *args, **kwargs: None

    @property
    def request_more_info(self) -> typing.Callable[
        [Workflow, Any, Any], typing.Optional[Dict[str, Any]]
    ]:
        return self._request_more_info

    @request_more_info.setter
    def request_more_info(
            self,
            value: typing.Callable[
                [Workflow, Any, Any], typing.Optional[Dict[str, Any]]
            ]
    ) -> None:
        self._request_more_info = value

    def iter_tasks(self,
                   workflow: Workflow,
                   options: Dict[str, Any]
                   ) -> typing.Iterable[speedwagon.tasks.Subtask]:
        """Get sub tasks for a workflow.

        Args:
            workflow: Workflow to run
            options:

        Yields:
            Yields subtasks for a workflow.

        """
        results: List[Any] = []

        task_generator = TaskGenerator(
            workflow,
            working_directory=self.working_directory,
            options=options,
            caller=self
        )

        for task in task_generator.tasks():
            self.total_tasks = task_generator.total_task
            yield task
            if task.task_result:
                results.append(task.task_result)
            self.current_task_progress = task_generator.current_task
        report = task_generator.generate_report(results)
        if report is not None:
            self.logger.info(task_generator.generate_report(results))

    def run_workflow_jobs(
            self,
            workflow: Workflow,
            options: typing.Dict[str, Any],
            reporter: Optional[RunnerDisplay] = None
    ) -> None:
        """Add job tasks to queue.

        This blocks until the task finished is called.
        """
        for subtask in self.iter_tasks(workflow, options):
            self._task_queue.put(subtask)
            self.logger.debug(
                "Task added to queue: [%s]",
                subtask.name
            )

            while self._task_queue.unfinished_tasks > 0:
                if reporter is not None:
                    reporter.refresh()
                    if reporter.user_canceled is True:
                        raise JobCancelled(
                            USER_ABORTED_MESSAGE,
                            expected=True
                        )

    def run(self, workflow: Workflow, options: Dict[str, Any]) -> None:

        task_dispatcher = TaskDispatcher(
            self._task_queue,
            self.logger
        )
        try:
            with task_dispatcher as task_runner:
                if self.reporter is not None:
                    self.reporter.task_runner = task_runner
                    self.reporter.task_scheduler = self
                    with self.reporter as active_reporter:
                        active_reporter.current_task_progress = 0
                        active_reporter.title = workflow.name
                        self.run_workflow_jobs(
                            workflow, options, active_reporter
                        )
                    active_reporter.refresh()
                else:
                    self.run_workflow_jobs(workflow, options)
        finally:
            self._task_queue.join()


# class AbsTaskSchedulerState(abc.ABC):
#
#     def __init_subclass__(cls) -> None:
#         super().__init_subclass__()
#         if cls.status_name is None:
#             raise NotImplementedError(
#                 f"You must implement 'status_name' class property "
#                 f"for {cls.__name__}"
#             )
#
#     status_name: str = None  # type: ignore
#
#     def __init__(self, context: "TaskScheduler2") -> None:
#         self.context = context
#         self.details: Optional[str] = None
#
#     @abc.abstractmethod
#     def start(self, await_event: threading.Event = None) -> None:
#         """Start task producer and consumer.
#
#         Args:
#             await_event:
#         """
#
#     @abc.abstractmethod
#     def run_next_task(self):
#         pass
#
#     def join(self, timeout=None) -> None:
#         self.context.task_producer.join(timeout)
#         try:
#             # self.context.task_queue.join()
#             self.context.task_consumer.shutdown()
#             self.context.status = TaskSchedulerJoined(self.context)
#         except BaseException as error:
#             self.context.status = TaskSchedulerFailed(self.context)
#             self.context.status.details = error.__str__()
#             raise
#
#     @abc.abstractmethod
#     def run(self, await_event: Optional[threading.Event]) -> None:
#         """Start the task scheduling."""

#
# class TaskSchedulerInit(AbsTaskSchedulerState):
#     status_name = 'initialized'
#
#     def start(self, await_event: threading.Event = None) -> None:
#         self.context.status = TaskSchedulerIdle(self.context)
#         # self.context.task_producer.workflow_name = \
#           self.context.workflow_name
#         #
#         # start_condition = threading.Condition()
#         await_event = await_event or threading.Event()
#         ready = threading.Event()
#         # self.context.task_consumer.start(start_condition)
#         # with start_condition:
#         if self.context.valid_workflows is not None:
#             if self.context.workflow_name is None:
#                 raise AssertionError("workflow_name is not set")
#             workflow_class = \
#                 self.context.valid_workflows.get(self.context.workflow_name)
#
#         else:
#             workflow_class = \
#                 available_workflows().get(self.context.workflow_name)
#         if workflow_class is None:
#             raise AssertionError("Workflow not found")
#         self.context.task_producer.workflow = workflow_class()
#
#         self.context.task_producer.workflow_options = \
#             self.context.workflow_options
#
#         # TODO: get rid of os.getcwd()
#         self.context.task_producer.working_directory = os.getcwd()
#         self.context.task_producer.start(ready)
#         ready.wait()
#         await_event.set()
#
#     def run_next_task(self) -> None:
#         self.context.status = TaskSchedulerWorking(self.context)
#         self.context.status.add_next_task_to_queue()
#
#     def run(self, await_event: Optional[threading.Event] = None) -> None:
#         raise RuntimeError("Schedule is not running")
#
#
# class TaskSchedulerIdle(AbsTaskSchedulerState):
#     status_name = 'idle'
#
#     def start(self, await_event: threading.Event = None) -> None:
#         raise RuntimeError("Scheduler already started")
#
#     def run(self, await_event: Optional[threading.Event] = None) -> None:
#         self.context.status = TaskSchedulerWorking(self.context)
#         start_condition = threading.Event()
#         await_event = await_event or threading.Event()
#         self.context.task_consumer.start(start_condition)
#         try:
#             while start_condition.wait(1) is False:
#                 if self.context.shutting_down.is_set():
#                     self.context.status = TaskSchedulerJoined(self.context)
#                     return
#         finally:
#             await_event.set()
#
#         # self.context.status.run_all_tasks()
#
#     def run_next_task(self) -> None:
#         self.context.status = TaskSchedulerWorking(self.context)
#         self.context.status.add_next_task_to_queue()
#
#
# class TaskSchedulerWorking(AbsTaskSchedulerState):
#     status_name = "working"
#
#     def start(self, await_event: threading.Event = None) -> None:
#         raise RuntimeError("Task scheduling already start")
#
#     def run_next_task(self):
#         self.add_next_task_to_queue()
#
#     def add_next_task_to_queue(self):
#         pass
#         # todo: add_next_task_to_queue
#
#     def run_all_tasks(self) -> None:
#         if self.context.valid_workflows is not None:
#             if self.context.workflow_name is None:
#                 raise AssertionError("Workflow missing name")
#             workflow_class = \
#                 self.context.valid_workflows.get(self.context.workflow_name)
#
#         else:
#             workflow_class = \
#                 available_workflows().get(self.context.workflow_name)
#         if workflow_class is None:
#             warnings.warn(
#                 f"No workflow found for {self.context.workflow_name}"
#             )
#             self.context.status = TaskSchedulerIdle(self.context)
#             return
#         self.context.task_producer.workflow = workflow_class()
#
#         self.context.task_producer.workflow_options = \
#             self.context.workflow_options
#
#         self.context.task_producer.working_directory = \
#             self.context.working_directory
#         #
#         # assert self.context.task_producer.workflow_class is not None
#         # assert self.context.task_producer.working_directory is not None
#         # assert self.context.task_producer.workflow_options is not None
#         # start = threading.Event()
#         # self.context.task_producer.start(start)
#         # # with start:
#         # while start.wait(1) is False:
#         #     print("task_producer is waiting to start")
#         # assert self.context.task_consumer._task_consumer_thread.is_alive()
#         # self.context.task_consumer.start()
#         # self.context.status = TaskSchedulerWorking(self.context)
#
#     def run(self, await_event: Optional[threading.Event] = None) -> None:
#         raise RuntimeError("Task scheduling already running")
#
#
# class TaskSchedulerFailed(AbsTaskSchedulerState):
#     status_name = "failed"
#
#     def start(self, await_event: threading.Event = None) -> None:
#         raise RuntimeError("Task failed")
#
#     def run_next_task(self) -> None:
#         raise RuntimeError("Task failed")
#
#     def run(self, await_event: Optional[threading.Event]) -> None:
#         raise RuntimeError("Task failed")
#
#     def join(self, timeout=None) -> None:
#         """This is a noop.
#
#         If in a failed state, there is nothing to join
#         """
#
#
# class TaskSchedulerJoined(AbsTaskSchedulerState):
#     status_name = "joined"
#
#     def start(self, await_event: threading.Event = None) -> None:
#         raise RuntimeError("Unable to start once joined")
#
#     def run_next_task(self) -> None:
#         raise RuntimeError("Run tasks once joined")
#
#     def run(self, await_event: Optional[threading.Event] = None) -> None:
#         raise RuntimeError("Run tasks once joined")
#
#
# class TaskManagementThread2(abc.ABC, threading.Thread):
#
#     def __init__(self, task_queue: 'queue.Queue[TaskPacket]',
#                  group=None,
#                  target=None,
#                  name: Optional[str] = None,
#                  args: Iterable[Any] = (),
#                  kwargs: Optional[Mapping[str, Any]] = None,
#                  *,
#                  daemon: Optional[bool] = None) -> None:
#         super().__init__(group, target, name, args, kwargs, daemon=daemon)
#         self.tast_queue = task_queue


class TaskManagementThread(abc.ABC):
    def __init__(self, task_queue: 'queue.Queue[TaskPacket]') -> None:
        self.task_queue = task_queue
        self.workflow_options: Dict[str, Any] = {}

    @abc.abstractmethod
    def run(self, await_event: threading.Event) -> None:
        """Run Main."""


# class ThreadedTaskProducer(TaskManagementThread):
#
#     def __init__(self, task_queue: 'queue.Queue[TaskPacket]') -> None:
#         super().__init__(task_queue)
#         self._task_producer_thread: Optional[threading.Thread] = None
#         self.workflow: Optional[Workflow] = None
#         self.working_directory: Optional[str] = None
#         self._last_packet_finished: Optional[threading.Condition] = None
#         self.total_tasks: Optional[int] = None
#         self.current_task_progress: Optional[int] = None
#         self._active = False
#         self._finished = False
#
#         self.abort = threading.Event()
#         self._start_event = threading.Event()
#
#         self.exc: Optional[BaseException] = None
#
#     def is_finished(self) -> bool:
#         return self._finished
#
#     def start(self, await_event: Optional[threading.Event] = None) -> None:
#
#         self._active = True
#         await_event = await_event or threading.Event()
#         logging.debug("starting task_producer_thread")
#         ready = threading.Event()
#         self._task_producer_thread = threading.Thread(
#             name='producer',
#             target=self.run, args=(ready,)
#         )
#         assert self.workflow is not None
#         self._start_event.set()
#
#         self._task_producer_thread.start()
#         while not ready.wait(1):
#             logging.debug("waiting for producer thread to start")
#         logging.debug("starting task_producer_thread - up")
#
#         await_event.set()
#
#     def join(self, timeout: Optional[float] = 2.0) -> None:
#         try:
#             logging.debug("stopping task_producer_thread")
#             if self._task_producer_thread is None:
#                 return
#
#             while self.is_finished() is False:
#                 if self._task_producer_thread.is_alive():
#                     self._task_producer_thread.join(timeout)
#                 if self.abort.is_set() is True:
#                     break
#             self._task_producer_thread.join(timeout)
#             if self._task_producer_thread.is_alive():
#                 raise RuntimeError("thread did not close is_finished")
#             logging.debug("task_producer_thread stopped")
#         finally:
#             self._finished = True
#             if self.exc is not None:
#                 self.abort.set()
#                 raise self.exc
#
#     def shutdown(self) -> None:
#         self._active = False
#         if self.abort.is_set():
#             return
#         self.join()
#
#     def run(self, await_event: threading.Event = None) -> None:
#
#         while not self._start_event.wait(1):
#             logging.debug('Producer thread waiting for start event ...')
#         logging.debug('Producer thread started ...')
#         self._active = True
#         started = False
#
#         await_event = await_event or threading.Event()
#         try:
#             while self._active:
#                 if not started:
#                     await_event.set()
#                     started = True
#                 if self.workflow is not None:
#                     for task in self.iter_tasks():
#                         if task is None:
#                             self._finished = True
#                             return
#                         self.submit_task(task)
#                     self._finished = True
#             logging.debug('Producer thread finished ...')
#         except BaseException as exception:
#             self.exc = exception
#             self.abort.set()
#             raise
#
#     def request_more_info(self, *args, **kwargs):
#         pass
#
#     def iter_tasks(
#             self
#     ) -> typing.Iterable[typing.Union[speedwagon.tasks.Subtask, None]]:
#
#         if self.workflow is None:
#             return []
#
#         if self.working_directory is None:
#             raise AssertionError("working_directory not set")
#
#         task_generator = TaskGenerator(
#             self.workflow,
#             working_directory=self.working_directory,
#             options=self.workflow_options,
#             caller=self
#         )
#         results = []
#
#         for task in task_generator.tasks():
#             if task_generator.total_task is not None:
#                 self.total_tasks = task_generator.total_task
#             yield task
#             if task.task_result:
#                 results.append(task.task_result)
#             if task_generator.current_task is not None:
#                 self.current_task_progress = task_generator.current_task
#         report = task_generator.generate_report(results)
#         if report is not None:
#             logging.info(task_generator.generate_report(results))
#         logging.debug("producer issued last task. Sending terminator")
#         yield None
#
#     def submit_task(self, task):
#         packet = TaskPacket(
#             TaskPacket.PacketType.TASK,
#             data=task,
#             finished=threading.Condition()
#         )
#         with packet.finished:
#             self.task_queue.put(
#                 packet
#             )
#             while not packet.finished.wait(1.0):
#                 if not self._active:
#                     break
#                 if task.status == speedwagon.tasks.tasks.TaskStatus.SUCCESS:
#                     break
#                 # fixme: why isn't this being triggered externally?
#                 if self.abort.is_set():
#                     logging.debug('Abort was set')
#                     break
#                     # return
#                 logging.debug('Producer thread waiting for task to finish')
#                 self.abort.set()
#
#             self._last_packet_finished = packet


class TerminateConsumerThread(Exception):
    pass


# class ThreadedTaskConsumer(TaskManagementThread):
#
#     def __init__(self, task_queue: 'queue.Queue[TaskPacket]') -> None:
#         super().__init__(task_queue)
#         self.exc: Optional[BaseException] = None
#         self._start_condition = None
#         self._task_consumer_thread: Optional[threading.Thread] = None
#         self._active = False
#         self.abort = threading.Event()
#
#     def start(
#             self,
#             confirm_started_condition: Optional[threading.Event] = None
#     ) -> None:
#
#         self._active = True
#         confirm_started_condition = \
#             confirm_started_condition or threading.Event()
#
#         self._task_consumer_thread = threading.Thread(
#             name='consumer',
#             target=self.run,
#             args=(confirm_started_condition,)
#         )
#         logging.debug("starting consumer thread")
#         self._task_consumer_thread.start()
#         while confirm_started_condition.wait(1) is False:
#             logging.debug("Waiting for consumer thread to start")
#         logging.debug("Waiting for consumer thread started")
#
#     def run(self, await_event: threading.Event) -> None:
#         logging.debug('Consumer thread started ...')
#         started = False
#         self._active = True
#         while self._active is True:
#             if started is False:
#                 # with start_condition:
#                 await_event.set()
#                 started = True
#             try:
#                 task = self.task_queue.get(timeout=1)
#                 try:
#                     if task is None:
#                         raise TerminateConsumerThread()
#                     self.execute_task_packet(task)
#                 except TerminateConsumerThread:
#                     break
#                 except BaseException as error:
#                     self.exc = error
#                     self.abort.set()
#                     raise
#                 finally:
#                     self.task_queue.task_done()
#             except queue.Empty:
#                 if self.abort.is_set():
#                     return
#                 if self._active is False:
#                     break
#                 logging.debug("no-op")
#                 continue
#         logging.debug('Consumer thread completed')
#
#     @classmethod
#     def execute_task_packet(cls, packet: "TaskPacket") -> None:
#         if packet.packet_type == packet.PacketType.COMMAND:
#             if packet.data == "done":
#                 logging.debug('Consumer thread got "done" task')
#                 raise TerminateConsumerThread()
#
#         elif packet.packet_type == packet.PacketType.TASK:
#             with packet.finished:
#                 try:
#                     task = typing.cast(speedwagon.tasks.Subtask, packet.data)
#                     task.exec()
#                 finally:
#                     packet.finished.notify()
#         else:
#             logging.error("Unknown packet type")
#
#     def shutdown(self) -> None:
#         try:
#             if self._task_consumer_thread is None:
#                 return
#             if self._task_consumer_thread.is_alive():
#                 self.task_queue.put(
#                     TaskPacket(TaskPacket.PacketType.COMMAND, "done"))
#                 self.task_queue.join()
#                 logging.debug("stopping task_consumer_thread")
#                 self._task_consumer_thread.join()
#                 logging.debug("task_consumer_thread stopped")
#             else:
#                 logging.debug("task_consumer_thread already stopped")
#         finally:
#             if self.exc is not None:
#                 self.abort.set()
#                 raise self.exc
#         # self._task_consumer_thread.ex


@dataclasses.dataclass
class TaskPacket:
    class PacketType(enum.Enum):
        COMMAND = 2
        TASK = 3
        NOOP = 4
    packet_type: "PacketType"
    data: typing.Any
    finished: threading.Condition = threading.Condition()


# class AbsTaskScheduler(metaclass=ABCMeta):
#
#     def __init__(self, parent: "JobManager", working_directory: str) -> None:
#         super().__init__()
#         self.working_directory = working_directory
#         self.parent = parent
#
#     @abstractmethod
#     def start(self) -> None:
#         pass
#
#     @abstractmethod
#     def join(self) -> None:
#         pass
#
#     @abstractmethod
#     def run(self, started_event: Optional[threading.Event] = None) -> None:
#         pass
#
#
# class TaskScheduler2(AbsTaskScheduler):
#     def __init__(self, parent: "JobManager", working_directory: str) -> None:
#         super().__init__(parent, working_directory)
#
#         self.current_task_progress: typing.Optional[int] = None
#         self.total_tasks: typing.Optional[int] = None
#
#         self.valid_workflows: Optional[Dict[str, typing.Type[Workflow]]] \
#           = None
#         self._workflow_class: Optional[typing.Type[Workflow]] = None
#         self.workflow_options: Dict[str, Any] = {}
#
#         self.task_queue: "queue.Queue[TaskPacket]" = queue.Queue(maxsize=1)
#         self.status: AbsTaskSchedulerState = TaskSchedulerInit(self)
#
#         self._task_ready = threading.Condition()
#
#         self.shutting_down = threading.Event()
#         self.abort = threading.Event()
#
#         self.task_consumer = ThreadedTaskConsumer(self.task_queue)
#         self.task_consumer.abort = self.abort
#         assert self.task_consumer.abort == self.abort
#
#         self.task_producer = ThreadedTaskProducer(self.task_queue)
#         self.task_producer.abort = self.abort
#         assert self.task_producer.abort == self.abort
#         print("ss")
#
#     def __str__(self) -> str:
#         base = "TaskScheduler2"
#         if self._workflow_class is None:
#             return base
#         return f"{base}: {self._workflow_class.name}"
#
#     @property
#     def workflow_name(self) -> Optional[str]:
#         # todo: convert to a strategy method
#
#         if self._workflow_class is None:
#             return None
#
#         workflow = self._workflow_class()
#         if workflow.name is None:
#             if self.valid_workflows is not None:
#                 for workflow_name, workflow_class in \
#                         self.valid_workflows.items():
#                     if workflow.__class__ == workflow_class:
#                         return workflow_name
#             return self._workflow_class.__name__
#         return workflow.name
#
#     @workflow_name.setter
#     def workflow_name(self, value: str) -> None:
#
#         if self.valid_workflows is not None:
#             workflow_class = self.valid_workflows.get(value)
#         else:
#             workflow_class = available_workflows().get(value)
#         if workflow_class is None:
#             raise ValueError(
#                 f"Unknown workflow: '{value}'"
#             )
#
#         self._workflow_class = typing.cast(Type[Workflow], workflow_class)
#
#     def start(self, await_event: Optional[threading.Event] = None) -> None:
#         self.status.start(await_event)
#
#     def join(self, timeout=None) -> None:
#         self.status.join(timeout)
#
#     def run(self, started_event: Optional[threading.Event] = None) -> None:
#         self.status.run(started_event)
#
#     def run_next_task(self):
#         self.status.run_next_task()


class QtRunner(AbsRunner2):
    def __init__(self,
                 parent: QtWidgets.QWidget = None) -> None:
        """Create a new runner."""
        self.parent = parent

    @staticmethod
    def update_progress(
            runner: "worker.WorkRunnerExternal3",
            current: int,
            total: int) -> None:

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
            workflow: Workflow,
            options: Dict[str, Any],
            pretask_results: typing.List[speedwagon.tasks.Result]
    ) -> Dict[str, Any]:
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

        with tempfile.TemporaryDirectory() as build_dir:
            task_scheduler = TaskScheduler(working_directory=build_dir)
            task_scheduler.reporter = QtDialogProgress(parent=self.parent)

            task_scheduler.logger = logger or logging.getLogger(__name__)

            if isinstance(job, Workflow):
                self.run_abs_workflow(
                    task_scheduler=task_scheduler,
                    job=job,
                    options=options,
                    logger=logger
                )

    def run_abs_workflow(self,
                         task_scheduler: TaskScheduler,
                         job: Workflow,
                         options: typing.Dict[str, Any],
                         logger: logging.Logger = None) -> None:

        task_scheduler.logger = logger or logging.getLogger(__name__)
        task_scheduler.request_more_info = self.request_more_info
        task_scheduler.run(job, options)


class AbsJobManager2(contextlib.AbstractContextManager):

    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(__name__)

    @abc.abstractmethod
    def submit_job(
            self,
            workflow_name: str,
            working_directory: str,
            callbacks: AbsJobCallbacks,
            events: AbsEvents,
            options: Optional[Dict[str, Any]] = None,
    ):
        pass

#
# class JobManager(AbsJobManager2):
#     def __init__(self) -> None:
#         self.workers: List["TaskScheduler2"] = []
#         self._threads = []
#         self.valid_workflows: \
#             Optional[dict[str, typing.Type[Workflow]]] = None
#
#     def __enter__(self) -> "JobManager":
#         return self
#
#     def __exit__(self,
#                  exc_type: Optional[Type[BaseException]],
#                  exc_value: Optional[BaseException],
#                  traceback: Optional[TracebackType]) -> None:
#         print("Shutting down workers")
#         for task_worker in self.workers:
#             # assert task_worker.abort == task_worker.task_producer.abort
#             # assert task_worker.abort == task_worker.task_consumer.abort
#             # task_worker.task_producer.abort.set()
#             # task_worker.task_consumer.abort.set()
#             print("shut down setting")
#             task_worker.shutting_down.set()
#             print("shut down set")
#             print("abort setting")
#             task_worker.abort.set()
#             print("abort set")
#             print("joining task worker")
#             task_worker.join()
#             print("joining task worker - done")
#         logging.debug("Joining threads")
#         for t in self._threads:
#             print(t)
#             t.join()
#         logging.debug("Joining threads - Done")
#
#     def __contains__(self, item: "TaskScheduler2") -> bool:
#         return item in self.workers
#
#     def submit_job(
#             self,
#             workflow_name: str,
#             working_directory: str,
#             callbacks: AbsJobCallbacks,
#             events: AbsEvents,
#             options: Optional[Dict[str, Any]] = None,
#     ) -> "TaskScheduler2":
#
#         options = options or {}
#         task_scheduler = TaskScheduler2(self, working_directory)
#
#         if self.valid_workflows is not None:
#             if any(
#                 {
#                     workflow_name not in self.valid_workflows,
#                     workflow_name not in available_workflows()
#                 }
#             ) is False:
#                 raise ValueError(
#                     f"Unable to submit unknown workflow {workflow_name}"
#                 )
#
#         # if self.valid_workflows is not None:
#             task_scheduler.valid_workflows = self.valid_workflows
#
#         task_scheduler.workflow_name = workflow_name
#         task_scheduler.workflow_options = options
#         event = threading.Event()
#         t = threading.Thread(target=task_scheduler.start, args=(event, ))
#         self._threads.append(t)
#         t.start()
#         while not event.wait(1):
#             print("waiting", file=sys.stderr)
#         print("up")
#         # task_scheduler.run()
#         self.workers.append(task_scheduler)
#         # TODO add this to a thread
#         return task_scheduler


class Run(TaskScheduler):

    def __init__(self, working_directory: str) -> None:
        super().__init__(working_directory)
        self.valid_workflows = None

    def get_workflow(self, workflow_name):
        if self.valid_workflows is not None:
            if workflow_name is None:
                raise AssertionError("workflow_name is not set")
            workflow_class = \
                self.valid_workflows.get(workflow_name)

        else:
            workflow_class = \
                available_workflows().get(workflow_name)
        if workflow_class is None:
            raise AssertionError(f"Workflow not found: {workflow_name}")
        return workflow_class


class BackgroundJobManager(AbsJobManager2):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._exec: Optional[BaseException] = None
        self.valid_workflows = None
        self._background_thread: Optional[threading.Thread] = None

    def __enter__(self) -> "BackgroundJobManager":
        self._exec = None
        self._background_thread = None
        return self

    def run_job_on_thread(
            self,
            workflow_name,
            working_directory,
            options,
            callbacks: AbsJobCallbacks,
            events: AbsEvents,
    ):
        self.logger.debug("Starting run_job_on_thread")
        try:
            task_scheduler = Run(working_directory)

            # Makes testing easier
            if self.valid_workflows is not None:
                task_scheduler.valid_workflows = self.valid_workflows

            workflow = task_scheduler.get_workflow(workflow_name)()
            for task in task_scheduler.iter_tasks(workflow, options):
                if events.is_stopped() is True:
                    break
                task.exec()
                callbacks.update_progress(
                    current=task_scheduler.current_task_progress,
                    total=task_scheduler.total_tasks
                )

        except BaseException as exception_thrown:
            self._exec = exception_thrown
            callbacks.error()
            # raise
        callbacks.done()

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_value: Optional[BaseException],
                 traceback: Optional[TracebackType]) -> None:
        self.clean_up_thread()
        if self._exec is not None:
            raise self._exec

    def clean_up_thread(self):
        if self._background_thread is not None:
            self._background_thread.join()

    def submit_job(
            self,
            workflow_name: str,
            working_directory: str,
            callbacks: AbsJobCallbacks,
            events: AbsEvents,
            options: Optional[Dict[str, Any]] = None,
    ):
        if self._background_thread is None:
            new_thread = threading.Thread(
                target=self.run_job_on_thread,
                kwargs={
                    "workflow_name": workflow_name,
                    "working_directory": working_directory,
                    "options": options,
                    "events": events,
                    "callbacks": callbacks,
                }
            )
            new_thread.start()
            self._background_thread = new_thread
            # todo: check if thread actually started

        QtWidgets.QApplication.processEvents()
        while self._background_thread.is_alive():
            self._background_thread.join(timeout=.01)
            callbacks.refresh()

        self._background_thread = None


class ThreadedEvents(AbsEvents):
    def __init__(self):
        super().__init__()
        self.stopped = threading.Event()

    def stop(self) -> None:
        self.stopped.set()

    def is_stopped(self) -> bool:
        return self.stopped.is_set()
