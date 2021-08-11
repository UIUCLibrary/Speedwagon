"""Defining execution of a given workflow steps and processes."""

import abc
import contextlib

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
from . import tasks
from .job import AbsWorkflow, Workflow, JobCancelled

__all__ = [
    "RunRunner",
    "UsingExternalManagerForAdapter"
]

USER_ABORTED_MESSAGE = "User Aborted"


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
    def __init__(self, strategy: AbsRunner2) -> None:
        """Create a new runner executor."""
        self._strategy = strategy

    def run(self,
            tool: AbsWorkflow,
            options: dict,
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

    def _get_additional_data(self, job, options, parent, pre_results):
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

                    main_task_builder = tasks.TaskBuilder(
                        tasks.MultiStageTaskBuilder(working_dir),
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
                        results,
                        working_dir: str,
                        logger: logging.Logger) -> list:
        _results = []
        with self._manager.open(parent=parent,
                                runner=worker.WorkRunnerExternal3) as runner:

            runner.dialog.setRange(0, 0)
            try:
                logger.addHandler(runner.progress_dialog_box_handler)

                finalization_task_builder = tasks.TaskBuilder(
                    tasks.MultiStageTaskBuilder(working_dir),
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
                task_builder = tasks.TaskBuilder(
                    tasks.MultiStageTaskBuilder(working_dir),
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
    def _get_additional_options(parent,
                                job: Workflow,
                                options: Dict[str, Any],
                                pretask_results) -> Dict[str, Any]:

        return job.get_additional_info(parent, options, pretask_results)


class TaskGenerator:

    def __init__(
            self,
            workflow: Workflow,
            options: typing.Mapping[str, Any],
            working_directory: str
    ) -> None:
        self.workflow = workflow
        self.options = options
        self.working_directory = working_directory
        self.current_task: typing.Optional[int] = None
        self.total_task: typing.Optional[int] = None
        self.parent = None

    def generate_report(
            self, results: List[tasks.Result]
    ) -> typing.Optional[str]:
        return self.workflow.generate_report(results, **self.options)

    def request_more_info(self, options, pretask_results):
        # TODO: Fix this so no parent is required
        if self.parent is not None and \
                hasattr(self.workflow, "get_additional_info"):
            return self.workflow.get_additional_info(
                self.parent, options, pretask_results.copy()
            )
        return {}

    def tasks(self) -> typing.Iterable[tasks.Subtask]:
        pretask_results = []

        results = []

        for pre_task in self.get_pre_tasks(
            self.working_directory, **self.options
        ):
            yield pre_task
            pretask_results.append(pre_task.task_result)
            results.append(pre_task.task_result)

        additional_data = self.request_more_info(self.options, pretask_results)

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
            **options) -> typing.Iterable[speedwagon.tasks.Subtask]:

        task_builder = tasks.TaskBuilder(
            tasks.MultiStageTaskBuilder(working_directory),
            working_directory
        )
        self.workflow.initial_task(task_builder, **options)
        yield from task_builder.build_task().main_subtasks

    def add_main_tasks(self,
                       working_directory: str,
                       pretask_results,
                       additional_data,
                       **options):

        for subtask in self.get_main_tasks(
                working_directory,
                pretask_results=pretask_results,
                additional_data=additional_data,
                **options
        ):
            adapted_tool = speedwagon.worker.SubtaskJobAdapter(subtask)
            yield adapted_tool, adapted_tool.settings

    def get_main_tasks(
            self,
            working_directory: str,
            pretask_results,
            additional_data,
            **options) -> typing.Iterable[speedwagon.tasks.Subtask]:
        metadata_tasks = \
            self.workflow.discover_task_metadata(
                pretask_results,
                additional_data,
                **options
            ) or []

        subtasks_generated = []
        for task_metadata in metadata_tasks:
            task_builder = tasks.TaskBuilder(
                tasks.MultiStageTaskBuilder(working_directory),
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
            results,
            **options) -> typing.Iterable[speedwagon.tasks.Subtask]:
        task_builder = tasks.TaskBuilder(
            tasks.MultiStageTaskBuilder(working_directory),
            working_directory
        )
        self.workflow.completion_task(task_builder, results, **options)
        yield from task_builder.build_task().main_subtasks

    @staticmethod
    def iter_tasks(
            runner: "worker.WorkRunnerExternal3",
            manager: "worker.ToolJobManager",
            update_progress_callback: typing.Callable[
                ["worker.WorkRunnerExternal3", int, int], None
            ]
    ):
        for result in manager.get_results(
                lambda x, y: update_progress_callback(runner, x, y)
        ):
            if result is not None:
                yield result


class RunnerDisplay(contextlib.AbstractContextManager, abc.ABC):

    def __init__(self) -> None:
        super().__init__()
        self.task_runner: typing.Optional[ProcessingTaskRunner] = None
        self.task_scheduler: typing.Optional[TaskScheduler] = None
        self._total_tasks_amount: typing.Optional[int] = None
        self._current_task_progress: typing.Optional[int] = None
        self._details = None

    @property
    def total_tasks_amount(self) -> typing.Optional[int]:
        return self._total_tasks_amount

    @total_tasks_amount.setter
    def total_tasks_amount(self, value):
        self._total_tasks_amount = value

    @abc.abstractmethod
    def refresh(self) -> None:
        pass

    @property
    def current_task_progress(self):
        return self._current_task_progress

    @current_task_progress.setter
    def current_task_progress(self, value):
        self._current_task_progress = value

    @property
    @abc.abstractmethod
    def user_canceled(self) -> bool:
        pass

    def __enter__(self):
        return self

    def __exit__(self, __exc_type: Optional[Type[BaseException]],
                 __exc_value: Optional[BaseException],
                 __traceback: Optional[TracebackType]) -> Optional[bool]:
        return None


class QtDialogProgress(RunnerDisplay):

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget]) -> None:
        super().__init__()
        self.dialog = speedwagon.dialog.WorkProgressBar(parent=parent)
        self.dialog.setMaximum(0)
        self.dialog.setValue(0)

    @property
    def details(self):
        return self.dialog.labelText()

    @details.setter
    def details(self, value):
        if self._details == value:
            return

        self._details = value
        self.dialog.setLabelText(value)
        QtWidgets.QApplication.processEvents()

    @property
    def user_canceled(self):
        return self.dialog.wasCanceled()

    @property
    def current_task_progress(self):
        return super().current_task_progress

    @current_task_progress.setter
    def current_task_progress(self, value):
        self._current_task_progress = value
        dialog_value = value or 0
        if self.dialog:
            self.dialog.setValue(dialog_value)

    @property
    def total_tasks_amount(self):
        return super().total_tasks_amount

    @total_tasks_amount.setter
    def total_tasks_amount(self, value):
        self._total_tasks_amount = value
        if value is None:
            self.dialog.setMaximum(0)
            return

        self.dialog.setMaximum(value)

    @property
    def title(self):
        return self.dialog.windowTitle()

    @title.setter
    def title(self, value):
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

    def __enter__(self):

        self.dialog.show()
        return super().__enter__()

    def __exit__(self, __exc_type: Optional[Type[BaseException]],
                 __exc_value: Optional[BaseException],
                 __traceback: Optional[TracebackType]):
        self.dialog.accept()
        self.close()

    def close(self):
        self.dialog.close()

    def _update_window_task_info(self, current_task: tasks.Subtask):
        self.details = current_task.name

    def _update_progress(self, task_scheduler):
        self.total_tasks_amount = task_scheduler.total_tasks
        self.current_task_progress = task_scheduler.current_task_progress


class ProcessingTaskRunner:

    def __init__(self, job_queue: queue.Queue, logger=None) -> None:
        super().__init__()
        self.job_queue = job_queue
        self._stop = threading.Event()
        self._thread: typing.Optional[threading.Thread] = None
        self.finish_event = threading.Event()
        self.progress_callback = lambda: None
        self.current_task: Optional[tasks.Subtask] = None
        self.logger = logger or logging.getLogger(__name__)

    def timeout_refresh(self):
        self.progress_callback()
        # QtWidgets.QApplication.processEvents()

    def stop(self):
        if self._thread is None:
            return
        self._stop.set()

        # self.job_queue.join()
        self._thread.join()
        # self.loggerlogger = logging.getLogger(__name__)
        self.logger.debug("Processing thread has stopped")

    def _start(
            self,
            stop_event: threading.Event,
            job_finished_event: threading.Event
    ):
        logger = self.logger
        # logger = logging.getLogger(__name__)
        logger.debug("Processing thread is available")
        while not stop_event.is_set():
            if self.job_queue.empty():
                continue
            task = self.job_queue.get()
            logger.info(task.task_description())
            logger.debug(
                "Threaded worker received task: [%s](%s)",
                task.name,
                task.task_description()
            )

            self.current_task = task
            task.log = logger.info
            task.exec()
            logger.debug(
                "Threaded worker completed task: [%s]",
                task.name
            )

            self.job_queue.task_done()
        job_finished_event.set()

    def start(self):
        logger = logging.getLogger(__name__)

        logger.debug("Starting processing thread")
        self._thread = threading.Thread(
            name="processing_thread",
            target=self._start,
            kwargs={
                "stop_event": self._stop,
                "job_finished_event": self.finish_event
            }
        )
        self._thread.start()


class TaskScheduler:

    def __init__(self, manager,
                 working_directory: str) -> None:
        self.manager = manager
        self.logger = logging.getLogger(__name__)
        self.working_directory = working_directory
        # self.update_progress_callback: typing.Callable[
        #     [worker.WorkRunnerExternal3, int, int], None
        # ] = lambda runner, current, total: None
        self.reporter: Optional[RunnerDisplay] = None

        self.current_task_progress: typing.Optional[int] = None
        self.total_tasks: typing.Optional[int] = None
        self.task_queue: "queue.Queue[tasks.Subtask]" = queue.Queue(maxsize=1)

    @staticmethod
    def _get_additional_data(job, options, parent, pre_results):
        if isinstance(job, Workflow):
            return job.get_additional_info(parent, options, pre_results.copy())
        return {}

    def iter_tasks(self,
                   workflow: Workflow,
                   options: Dict[str, Any]
                   ) -> typing.Iterable[tasks.Subtask]:
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
            options=options
        )

        task_generator.parent = None
        for task in task_generator.tasks():
            self.total_tasks = task_generator.total_task
            yield task
            if task.task_result:
                results.append(task.task_result)
            self.current_task_progress = task_generator.current_task
        report = task_generator.generate_report(results)
        if report is not None:
            self.logger.info(task_generator.generate_report(results))

    def run(self, job: Workflow, options: Dict[str, Any]) -> None:

        with self.manager.open(parent=None,
                               runner=worker.WorkRunnerExternal3):
            task_runner_strategy = ProcessingTaskRunner(
                self.task_queue,
                self.logger
            )
            try:
                task_runner_strategy.start()
                if self.reporter is not None:
                    self.reporter.task_runner = task_runner_strategy
                    self.reporter.task_scheduler = self
                    with self.reporter as reporter:
                        reporter.current_task_progress = 0
                        reporter.title = job.name

                        for subtask in self.iter_tasks(job, options):
                            self.task_queue.put(subtask)
                            self.logger.debug(
                                "Task added to queue: [%s]",
                                subtask.name
                            )

                            while self.task_queue.unfinished_tasks > 0:
                                reporter.refresh()
                                if reporter.user_canceled is True:
                                    raise JobCancelled(USER_ABORTED_MESSAGE)
                        reporter.refresh()
            finally:
                reporter.refresh()
                self.task_queue.join()
                task_runner_strategy.stop()
                reporter.close()


class QtRunner(AbsRunner2):
    def __init__(self,
                 manager: "worker.ToolJobManager",
                 parent: QtWidgets.QWidget = None) -> None:
        """Create a new runner."""
        self._manager = manager
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

    def run(self,
            job: AbsWorkflow, options: dict,
            logger: logging.Logger = None,
            completion_callback=None
            ) -> None:

        with tempfile.TemporaryDirectory() as build_dir:
            task_runner = TaskScheduler(
                manager=self._manager,
                working_directory=build_dir
            )
            task_runner.reporter = QtDialogProgress(parent=self.parent)

            task_runner.logger = logger or logging.getLogger(__name__)

            if isinstance(job, Workflow):
                self.run_abs_workflow(
                    task_scheduler=task_runner,
                    job=job,
                    options=options,
                    logger=logger
                )

    @staticmethod
    def run_abs_workflow(task_scheduler: TaskScheduler,
                         job: Workflow,
                         options, logger: logging.Logger = None) -> None:

        task_scheduler.logger = logger or logging.getLogger(__name__)
        task_scheduler.run(job, options)

        # task_scheduler.reporter
