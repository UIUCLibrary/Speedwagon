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

                logger.info("Found {} jobs".format(i + 1))
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
        self.workflow.initial_task(task_builder, **options)
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
        """Stopping an idle thread is a no-op."""

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


class AbsTaskSchedulerState(abc.ABC):

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if cls.status_name is None:
            raise NotImplementedError(
                f"You must implement 'status_name' class property "
                f"for {cls.__name__}"
            )

    status_name = None

    def __init__(self, context: "TaskScheduler2") -> None:
        self.context = context

    @abc.abstractmethod
    def start(self):
        """Start task producer and consumer"""

    @abc.abstractmethod
    def run_next_task(self):
        pass

    def join(self):

        if self.context._task_producer_thread.is_alive():
            logging.debug("stopping task_producer_thread")
            self.context._task_producer_thread.join()
            logging.debug("task_producer_thread stopped")
        self.context.shutdown_consumer_thread()

        logging.debug("Task queue joining")
        self.context.task_queue.join()
        logging.debug("Task queue joining - Done")

        self.context.status = TaskSchedulerJoined(self.context)

    @abc.abstractmethod
    def run(self):
        pass


class TaskSchedulerInit(AbsTaskSchedulerState):
    status_name = 'initialized'

    def start(self):
        pass

    def run_next_task(self):
        self.context.status = TaskSchedulerWorking(self.context)
        self.context.status.add_next_task_to_queue()

    def run(self):
        self.context.status = TaskSchedulerWorking(self.context)
        self.context.status.run_all_tasks()


class TaskSchedulerIdle(AbsTaskSchedulerState):
    status_name = 'idle'

    def start(self):
        self.context.status = TaskSchedulerWorking(self.context)

    def run(self):
        self.context.status = TaskSchedulerWorking(self.context)
        self.context._task_producer_thread.start()
        self.context.status.run_all_tasks()

    def run_next_task(self):
        self.context.status = TaskSchedulerWorking(self.context)
        self.context.status.add_next_task_to_queue()


class TaskSchedulerWorking(AbsTaskSchedulerState):
    status_name = "working"

    def __init__(self, context: "TaskScheduler2") -> None:
        super().__init__(context)
        self.generator = None
        if self.context.task_producer.workflow_class is None:
            if self.context.valid_workflows is not None:
                workflow_class = \
                    self.context.valid_workflows.get(
                        self.context.workflow_name
                    )
            else:
                workflow_class = \
                    available_workflows().get(self.context.workflow_name)

            if workflow_class is None:
                warnings.warn(
                    f"No workflow found for {self.context.workflow_name}"
                )
                return
            self.context.task_producer.workflow_class = workflow_class()

            self.context.task_producer.workflow_options = \
                self.context.workflow_options

            self.context.task_producer.working_directory = \
                self.context.working_directory

    def start(self):
        raise RuntimeError("Task scheduling already start")

    def run_next_task(self):
        self.add_next_task_to_queue()

    def add_next_task_to_queue(self):
        # FIXME:

        if self.generator is None:
            self.generator = self.context.task_producer.iter_tasks()
        try:
            task = next(self.generator)
            self.context.task_queue.put(task)
        except StopIteration:
            self.generator = None
            module_logger.warning("No task added to queue")

    def run_all_tasks(self):
        if self.context.valid_workflows is not None:
            workflow_class = \
                self.context.valid_workflows.get(self.context.workflow_name)

        else:
            workflow_class = \
                available_workflows().get(self.context.workflow_name)

        if workflow_class is None:
            warnings.warn(
                f"No workflow found for {self.context.workflow_name}"
            )
            # module_logger.warning()
            return
        self.context.task_producer.workflow_class = workflow_class()

        self.context.task_producer.workflow_options = \
            self.context.workflow_options

        self.context.task_producer.working_directory = \
            self.context.working_directory

        assert self.context.task_producer.workflow_class is not None
        assert self.context.task_producer.working_directory is not None
        assert self.context.task_producer.workflow_options is not None

        self.context._task_consumer_thread.name = \
            f"Consumer thread: {self.context.workflow_name}"

        self.context._task_producer_thread.start()
        self.context.start_consumer_thread()
        self.context.status = TaskSchedulerWorking(self.context)

    def run(self):
        pass

        # self.run_next_task()


class TaskSchedulerJoined(AbsTaskSchedulerState):
    status_name = "joined"

    def start(self):
        raise RuntimeError("Unable to start once joined")

    def run_next_task(self):
        raise RuntimeError("Run tasks once joined")

    def run(self):
        raise RuntimeError("Run tasks once joined")


class TaskManagementThread(abc.ABC):
    def __init__(self, task_queue: 'queue.Queue[TaskPacket]'):
        self.task_queue = task_queue

    @abc.abstractmethod
    def run(self):
        """Run Main"""


class TaskProducer1(TaskManagementThread):

    def __init__(self, task_queue: 'queue.Queue[TaskPacket]'):
        super().__init__(task_queue)
        self.workflow_class: Optional[Workflow] = None
        self.workflow_options = {}
        self.working_directory = None
        self.last_task_finished = None
        self.total_tasks = None
        self.current_task_progress = None

    def run(self):
        logging.debug('Producer thread started ...')
        if self.workflow_class is not None:
            for task in self.iter_tasks():
                # print(self.task_queue.unfinished_tasks)
                packet = TaskPacket(
                    TaskPacket.PacketType.TASK,
                    data=task,
                    finished=threading.Condition()
                )
                with packet.finished:
                    self.task_queue.put(
                        packet
                    )
                    packet.finished.wait()
                    self.last_task_finished = packet.finished
        logging.debug('Producer thread finished ...')

    def request_more_info(self, *args, **kwargs):
        pass

    def add_task_to_queue(self, task):
        # print(self.task_queue.unfinished_tasks)
        self.task_queue.put(
            TaskPacket(TaskPacket.PacketType.TASK, data=task,
                       finished=threading.Condition()
                       )
        )
        logging.debug('Added to queue: %s', task.task_description())

    def iter_tasks(self):

        task_generator = TaskGenerator(
            self.workflow_class,
            working_directory=self.working_directory,
            options=self.workflow_options,
            caller=self
        )
        results = []

        for task in task_generator.tasks():
            self.total_tasks = task_generator.total_task
            yield task
            if task.task_result:
                results.append(task.task_result)
            self.current_task_progress = task_generator.current_task
        report = task_generator.generate_report(results)
        if report is not None:
            logging.info(task_generator.generate_report(results))


class TerminateConsumerThread(Exception):
    pass


class TaskConsumer3(TaskManagementThread):

    def run(self):
        logging.debug('Consumer thread started ...')
        while True:
            try:
                task = self.task_queue.get(timeout=1)
                try:
                    self.execute_task_packet(task)
                except TerminateConsumerThread:
                    break
                finally:
                    self.task_queue.task_done()
            except queue.Empty:
                logging.debug("no-op")
                continue
        logging.debug('Consumer thread completed')

    @staticmethod
    def execute_task_packet(packet: "TaskPacket"):
        if packet.packet_type == packet.PacketType.COMMAND:
            if packet.data == "done":
                logging.debug('Consumer thread got "done" task')
                raise TerminateConsumerThread()

        elif packet.packet_type == packet.PacketType.TASK:
            task = typing.cast(speedwagon.tasks.Subtask, packet.data)
            with packet.finished:
                try:
                    task.work()
                finally:
                    packet.finished.notify()
        else:
            logging.error("Unknown packet type")


@dataclasses.dataclass
class TaskPacket:
    class PacketType(enum.Enum):
        COMMAND = 2
        TASK = 3
    packet_type: "PacketType"
    data: typing.Any
    finished: threading.Condition = threading.Condition()


class TaskScheduler2:
    def __init__(self, working_directory: str) -> None:
        self.logger = logging.getLogger(__name__)
        self.working_directory = working_directory
        self.reporter: Optional[RunnerDisplay] = None

        self.current_task_progress: typing.Optional[int] = None
        self.total_tasks: typing.Optional[int] = None

        self.valid_workflows: Optional[Dict[str, typing.Type[Workflow]]] = None
        self._workflow_class: Optional[typing.Type[Workflow]] = None
        self.workflow_options = {}
        self.task_queue = queue.Queue(maxsize=1)
        self.status: AbsTaskSchedulerState = TaskSchedulerInit(self)
        logging.basicConfig(level=logging.DEBUG,
                            format='(%(threadName)-9s) %(message)s', )

        self.task_consumer = TaskConsumer3(self.task_queue)
        self.task_producer = TaskProducer1(self.task_queue)

        self._task_consumer_thread = threading.Thread(
            name='consumer',
            target=self.task_consumer.run,
        )
        self._task_producer_thread = threading.Thread(
            name='producer',
            target=self.task_producer.run,
        )

    def start_consumer_thread(self):
        self._task_consumer_thread.start()

    def shutdown_consumer_thread(self):
        if self._task_consumer_thread.is_alive():
            self.task_queue.put(
                TaskPacket(TaskPacket.PacketType.COMMAND, "done"))
            logging.debug("stopping task_consumer_thread")
            self._task_consumer_thread.join()
            logging.debug("task_consumer_thread stopped")
        else:
            logging.debug("task_consumer_thread already stopped")

    @property
    def workflow_name(self) -> Optional[str]:
        if self._workflow_class is None:
            return None
        if self._workflow_class.name is None:
            return self._workflow_class.__class__.__name__
        return self._workflow_class.name

    @workflow_name.setter
    def workflow_name(self, value: str):

        if self.valid_workflows is not None:
            workflow_class = self.valid_workflows.get(value)
        else:
            workflow_class = available_workflows().get(value)
        if workflow_class is None:
            raise ValueError(
                f"Unknown workflow: '{value}'"
            )
        self._workflow_class = workflow_class()

    def start(self):
        self.status.start()

    def join(self):
        self.status.join()

    def run(self):
        self.status.run()

    def run_next_task(self):
        self.status.run_next_task()


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


class JobManager(contextlib.AbstractContextManager):
    def __init__(self):
        self._workers = []
        self.valid_workflows: Optional[dict[str, typing.Type[Workflow]]] = None

    def __enter__(self) -> "JobManager":
        return self

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_value: Optional[BaseException],
                 traceback: Optional[TracebackType]) -> None:
        for task_worker in self._workers:
            task_worker.join()

    def __contains__(self, item) -> bool:
        return item in self._workers

    def submit_job(
            self,
            workflow_name: str,
            working_directory: str,
            options=None
    ) -> "TaskScheduler2":

        options = options or {}
        task_scheduler = TaskScheduler2(working_directory)

        if self.valid_workflows is not None:
            workflow_class = self.valid_workflows.get(workflow_name)
        else:
            workflow_class = available_workflows().get(workflow_name)
        if workflow_class is None:
            raise ValueError(
                f"Unable to submit unknown workflow {workflow_name}"
            )

        if self.valid_workflows is not None:
            task_scheduler.valid_workflows = self.valid_workflows
        task_scheduler.workflow_name = workflow_name
        task_scheduler.workflow_options = options
        # TODO add this to a thread
        self._workers.append(task_scheduler)
        return task_scheduler
