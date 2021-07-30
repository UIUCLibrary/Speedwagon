"""Defining execution of a given workflow steps and processes."""

import abc
import functools
import logging
import tempfile
import typing
import warnings
from typing import List, Any, Dict

from PyQt5 import QtWidgets

import speedwagon
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
            "Use UsingExternalManagerForAdapter instead",
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


def runner_managed_task(callback):

    def run(self, runner, *args, **kwargs):
        runner.abort_callback = self.manager.abort
        runner.dialog.setRange(0, 0)
        try:
            runner.dialog.setWindowTitle(self.job.name)
            self.logger.addHandler(runner.progress_dialog_box_handler)
            results = callback(self, *args, runner=runner, **kwargs)
            if runner.was_aborted:
                raise TaskFailed(USER_ABORTED_MESSAGE)
            return results
        finally:
            runner.dialog.accept()
            runner.dialog.close()
            self.logger.removeHandler(
                runner.progress_dialog_box_handler)

    @functools.wraps(callback)
    def dialog_window(self, *args, **kwargs):
        if 'runner' in kwargs and kwargs['runner'] is not None:
            return run(self, kwargs['runner'], *args, **kwargs)
        with self.manager.open(
                parent=self.parent_widget,
                runner=worker.WorkRunnerExternal3
        ) as runner:
            return run(self, runner, *args, **kwargs)
    return dialog_window


class TaskRunner:

    def __init__(self,
                 job,
                 manager,
                 parent_widget: typing.Optional[QtWidgets.QWidget],
                 working_directory: str,
                 ) -> None:
        super().__init__()
        self.manager = manager
        self.parent_widget = parent_widget
        self.logger = logging.getLogger(__name__)
        self.job = job
        self.working_directory = working_directory
        self.update_progress_callback: \
            typing.Optional[
                typing.Callable[[worker.WorkRunnerExternal3, int, int], None]
            ] = None

    @runner_managed_task
    def run_pre_tasks(
            self,
            options: Dict[str, Any],
            runner: "worker.WorkRunnerExternal3" = None
    ) -> List[Any]:

        self._add_jobs_tasks(
            self.manager,
            self.working_directory,
            lambda task_builder: self.job.initial_task(task_builder, **options)
        )

        self.manager.start()

        post_results = self.manager.get_results(
            lambda x, y: self.update_progress(runner, x, y)
        )

        return [
            post_result for post_result
            in post_results
            if post_result is not None
        ]

    @staticmethod
    def _add_jobs_tasks(manager: "worker.ToolJobManager",
                        working_directory: str,
                        callback: typing.Callable[[tasks.TaskBuilder], None]):
        task_builder = tasks.TaskBuilder(
            tasks.MultiStageTaskBuilder(working_directory),
            working_directory
        )
        callback(task_builder)

        for subtask in task_builder.build_task().main_subtasks:
            adapted_tool = speedwagon.worker.SubtaskJobAdapter(subtask)
            manager.add_job(adapted_tool, adapted_tool.settings)

    def update_progress(self,
                        runner: "typing.Optional[worker.WorkRunnerExternal3]",
                        current: int,
                        total: int) -> None:
        if callable(self.update_progress_callback) and runner is not None:
            self.update_progress_callback(runner, current, total)

    @runner_managed_task
    def run_main_tasks(self,
                       options: Dict[str, Any],
                       pretask_results,
                       additional_data: Dict[str, Any],
                       runner: "worker.WorkRunnerExternal3" = None,
                       ) -> list:

        i = -1

        metadata_tasks = \
            self.job.discover_task_metadata(
                pretask_results,
                additional_data,
                **options
            ) or []

        for task_metadata in metadata_tasks:
            self._add_jobs_tasks(
                manager=self.manager,
                working_directory=self.working_directory,
                callback=lambda task_builder, metadata=task_metadata:
                self.job.create_new_task(task_builder, **metadata)
            )
            i += 1

        self.logger.info("Found %d jobs", i + 1)
        if runner is not None and runner.dialog is not None:
            runner.dialog.setMaximum(i)
        self.manager.start()

        main_results = self.manager.get_results(
            lambda x, y: self.update_progress(runner, x, y)
        )

        return [result for result in main_results if result is not None]

    @runner_managed_task
    def run_post_tasks(
            self,
            options: Dict[str, Any],
            results,
            runner: "worker.WorkRunnerExternal3" = None,
    ) -> list:
        self._add_jobs_tasks(
            self.manager,
            self.working_directory,
            lambda task_builder: self.job.completion_task(
                task_builder, results, **options
            )
        )
        self.manager.start()

        post_results = self.manager.get_results(
            lambda x, y: self.update_progress(runner, x, y)
        )
        return [
            post_result for post_result in post_results
            if post_result is not None
        ]


class UsingExternalManagerForAdapter2(AbsRunner2):
    def __init__(self,
                 manager: "worker.ToolJobManager",
                 parent: QtWidgets.QWidget = None) -> None:
        """Create a new runner."""
        self._manager = manager
        self.parent = parent

    @staticmethod
    def _update_progress(
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

    @staticmethod
    def _get_additional_options(parent,
                                job: Workflow,
                                options: Dict[str, Any],
                                pretask_results) -> Dict[str, Any]:

        return job.get_additional_info(parent, options, pretask_results)

    def _get_additional_data(self, job, options, parent, pre_results):
        if isinstance(job, Workflow):
            return self._get_additional_options(
                parent,
                job,
                options,
                pre_results.copy()
            )

        return {}

    def run_abs_workflow(self,
                         task_runner: TaskRunner,
                         job: AbsWorkflow,
                         options,
                         logger: logging.Logger = None):
        logger = logger or logging.getLogger(__name__)
        results: List[Any] = []
        try:
            pre_results = task_runner.run_pre_tasks(options=options)

            results += pre_results

            additional_data = \
                self._get_additional_data(job,
                                          options,
                                          self.parent,
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
            results += task_runner.run_main_tasks(
                options,
                pre_results,
                additional_data=additional_data
            )

        except TaskFailed as error:

            logger.error(
                "Job stopped during main tasks phase. "
                "Reason: {}".format(error)
            )

            return

        try:
            results += task_runner.run_post_tasks(
                options=options,
                results=results
            )
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

    def run(self,
            job: AbsWorkflow, options: dict,
            logger: logging.Logger = None,
            completion_callback=None
            ) -> None:
        with tempfile.TemporaryDirectory() as build_dir:
            task_runner = TaskRunner(job=job,
                                     manager=self._manager,
                                     parent_widget=self.parent,
                                     working_directory=build_dir
                                     )
            task_runner.logger = logger or logging.getLogger(__name__)
            task_runner.update_progress_callback = self._update_progress
            if isinstance(job, AbsWorkflow):
                self.run_abs_workflow(
                    task_runner=task_runner,
                    job=job,
                    options=options,
                    logger=logger
                )
