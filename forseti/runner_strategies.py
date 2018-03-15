import abc
import traceback
import logging
import sys

import time
import typing
import warnings

from PyQt5 import QtCore, QtWidgets

import forseti.job
import forseti.workflows
import forseti.tasks
# Tool, Options,
from forseti import worker
import forseti.gui


class TaskFailed(Exception):
    pass


class AbsRunner(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def run(self, parent, job: forseti.job.AbsJob, options: dict, logger: logging.Logger,
            completion_callback=None) -> None:
        pass


class RunRunner:
    def __init__(self, strategy: AbsRunner) -> None:
        self._strategy = strategy

    def run(self, parent, tool: forseti.job.AbsJob, options: dict, logger: logging.Logger,
            completion_callback=None) -> None:
        self._strategy.run(parent, tool, options, logger, completion_callback)


# class UsingWorkWrapper(AbsRunner):
#
#     def __init__(self) -> None:
#         super().__init__()
#         warnings.warn("Use UsingWorkManager instead", DeprecationWarning)
#
#     def run(self, parent, tool: forseti.tools.abstool.AbsTool, options: dict, finalization_task, on_failure,
#             logger: logging.Logger):
#         with worker.WorkWrapper(parent, tool, logger=logger) as work_manager:
#
#             work_manager.worker_display.finished.connect(finalization_task)
#             work_manager.worker_display.failed.connect(on_failure)
#
#             try:
#                 # self.log_manager.debug("Validating arguments")
#                 work_manager.valid_arguments(options)
#                 # tool.validate_user_options(**options)
#                 # wm.completion_callback = lambda: self._tool.setup_task()
#
#                 # Search for jobs
#                 job_searcher = forseti.gui.JobSearcher(tool, options)
#                 # print("Job search starting", file=sys.stderr)
#                 job_searcher.start()
#                 while True:
#                     if job_searcher.isFinished():
#                         break
#                     else:
#                         time.sleep(0.01)
#                     # self.log_manager.info("Loading")
#                     QtCore.QCoreApplication.processEvents()
#                     # self.QApplication.processEvents()
#                 # print("Job search Finished", file=sys.stderr)
#
#                 for _job_args in job_searcher.jobs:
#                     # self.log_manager.debug("Adding {} with {} to work manager".format(tool, _job_args))
#                     work_manager.add_job(_job_args)
#
#                 print("running {} subtasks".format(work_manager.worker_display._jobs_queue.qsize()), file=sys.stderr)
#                 try:
#                     work_manager.run()
#
#                     # print("AFTER")
#                     # work_manager.worker_display.finish()
#
#                 except RuntimeError as e:
#                     QtWidgets.QMessageBox.warning(parent, "Process failed", str(e))
#                 # except TypeError as e:
#                 #     QtWidgets.QMessageBox.critical(self, "Process failed", str(e))
#                 #     raise
#
#             except ValueError as e:
#
#                 # if work_manager._working is not None:
#                 #     work_manager.worker_display.cancel(e, quiet=True)
#                 work_manager.worker_display.cancel(quiet=True)
#                 QtWidgets.QMessageBox.warning(parent, "Invalid setting", str(e))
#                 return
#
#             except Exception as e:
#                 work_manager.worker_display.cancel(quiet=True)
#                 exception_message = traceback.format_exception(type(e), e, tb=e.__traceback__)
#                 msg = QtWidgets.QMessageBox(self)
#                 msg.setIcon(QtWidgets.QMessageBox.Critical)
#                 msg.setWindowTitle(str(type(e).__name__))
#                 msg.setText(str(e))
#                 msg.setDetailedText("".join(exception_message))
#                 # self.log_manager.fatal("Terminating application. Reason: {}".format(e))
#                 msg.exec_()
#                 print("Exiting early", file=sys.stderr)
#                 sys.exit(1)
#             finally:
#                 print("out!", file=sys.stderr)


# class UsingWorkManager(AbsRunner):
#     def run(self, parent, tool: forseti.tools.abstool.AbsTool, options: dict, finalization_task, on_failure, logger):
#         worker_manager = worker.WorkerManager(title=tool.name, tool=tool, parent=parent, logger=logger)
#         # worker_manager.logger = logger
#         try:
#             with worker_manager.open(options) as work_runner:
#                 work_runner.start()
#                 work_runner.finish()
#
#             finalization_task(worker_manager.results, tool.setup_task)
#         except Exception as e:
#             on_failure(e)


class UsingExternalManager(AbsRunner):

    def __init__(self, manager: worker.ToolJobManager, on_success, on_failure) -> None:
        self._manager = manager
        self._on_success = on_success
        self._on_failure = on_failure

    def run(self, parent, job: forseti.job.AbsJob, options: dict, logger: logging.Logger, completion_callback=None):
        try:
            with self._manager.open(options=options, tool=job, parent=parent) as runner:

                def update_progress(current: int, total: int):

                    if total != runner.dialog.maximum():
                        runner.dialog.setMaximum(total)
                    if current != runner.dialog.value():
                        runner.dialog.setValue(current)

                    if current == total:
                        runner.dialog.accept()

                if isinstance(job, forseti.tools.AbsTool):
                    runner.abort_callback = self.on_runner_aborted
                    logger.addHandler(runner.progress_dialog_box_handler)
                    runner.dialog.setRange(0, 0)

                    i = -1
                    for i, new_setting in enumerate(job.discover_task_metadata(**options)):
                        new_job = job.new_job()
                        self._manager.add_job(new_job(), new_setting)
                    logger.info("Found {} jobs".format(i + 1))
                    runner.dialog.setMaximum(i)

                    self._manager.start()

                    runner.dialog.show()

                    results = list()
                    for result in self._manager.get_results(update_progress):
                        results.append(result)
                    logger.removeHandler(runner.progress_dialog_box_handler)

                    self._on_success(results, job.on_completion)
        except Exception as e:
            self._on_failure(e)

    def on_runner_aborted(self):
        self._manager.abort()


class UsingExternalManagerForAdapter(AbsRunner):

    def __init__(self, manager: worker.ToolJobManager) -> None:
        self._manager = manager

    def _update_progress(self, runner, current: int, total: int):

        if total != runner.dialog.maximum():
            runner.dialog.setMaximum(total)
        if current != runner.dialog.value():
            runner.dialog.setValue(current)

        if current == total:
            runner.dialog.accept()

    def run(self, parent, job: forseti.job.AbsJob, options: dict, logger: logging.Logger,
            completion_callback=None) -> None:

        results: typing.List[typing.Any] = []
        if isinstance(job, forseti.workflows.AbsWorkflow):

            try:
                results += self._run_pre_tasks(parent, job, options, logger)
            except TaskFailed as e:
                logger.error("Job stopped during pre-task phase. Reason: {}".format(e))
                return

            try:
                results += self._run_main_tasks(parent, job, options, logger)
            except TaskFailed as e:
                logger.error("Job stopped during main tasks phase. Reason: {}".format(e))
                return

            try:
                results += self._run_post_tasks(parent, job, options, results, logger)
            except TaskFailed as e:
                logger.error("Job stopped during post-task phase. Reason: {}".format(e))
                return

            logger.debug("Generating report")
            report = job.generate_report(results, **options)
            if report:
                logger.info(report)

    def _run_main_tasks(self, parent, job, options, logger) -> list:
        results = []
        with self._manager.open(parent=parent, runner=worker.WorkRunnerExternal3) as runner:
            runner.abort_callback = self._manager.abort
            i = -1
            runner.dialog.setRange(0, 0)
            runner.dialog.setWindowTitle(job.name)
            try:
                logger.addHandler(runner.progress_dialog_box_handler)
                # add any tasks that need to start before the main work
                # startup_task_builder = forseti.tasks.TaskBuilder(forseti.tasks.MultiStageTaskBuilder())
                # # job.setup_task(startup_task_builder)
                # startup_task = startup_task_builder.build_task()
                # for subtask in startup_task.subtasks:
                #     adapted_tool = forseti.tasks.SubtaskJobAdapter(subtask)
                #     self._manager.add_job(adapted_tool, adapted_tool.settings)
                #     # self._manager.add_startup_job(adapted_tool, adapted_tool.settings)

                # Run the main tasks. Keep track of the progress
                for new_task_metadata in job.discover_task_metadata(**options):
                    main_task_builder = forseti.tasks.TaskBuilder(forseti.tasks.MultiStageTaskBuilder())
                    job.create_new_task(main_task_builder, **new_task_metadata)
                    new_task = main_task_builder.build_task()
                    for subtask in new_task.subtasks:
                        i += 1
                        adapted_tool = forseti.tasks.SubtaskJobAdapter(subtask)
                        self._manager.add_job(adapted_tool, adapted_tool.settings)
                logger.info("Found {} jobs".format(i + 1))
                runner.dialog.setMaximum(i)
                self._manager.start()

                runner.dialog.show()
                for result in self._manager.get_results(lambda x, y: self._update_progress(runner, x, y)):
                    # for f in self._manager.futures:
                    #     print(f)
                    if result is not None:
                        results.append(result)
                if runner.was_aborted:
                    raise TaskFailed("User Aborted")
            finally:
                logger.removeHandler(runner.progress_dialog_box_handler)
            return results

    def _run_post_tasks(self, parent, job, options, results, logger) -> list:
        _results = []
        with self._manager.open(parent=parent, runner=worker.WorkRunnerExternal3) as runner:
            runner.dialog.setRange(0, 0)
            try:
                logger.addHandler(runner.progress_dialog_box_handler)
                finalization_task_builder = forseti.tasks.TaskBuilder(forseti.tasks.MultiStageTaskBuilder())
                job.completion_task(finalization_task_builder, results, **options)
                task = finalization_task_builder.build_task()
                for subtask in task.subtasks:
                    adapted_tool = forseti.tasks.SubtaskJobAdapter(subtask)
                    self._manager.add_job(adapted_tool, adapted_tool.settings)
                self._manager.start()
                for post_result in self._manager.get_results(lambda x, y: self._update_progress(runner, x, y)):
                    if post_result is not None:
                        _results.append(post_result)

                runner.dialog.accept()
                runner.dialog.close()
                if runner.was_aborted:
                    raise TaskFailed("User Aborted")
                return _results
            finally:
                logger.removeHandler(runner.progress_dialog_box_handler)

    def _run_pre_tasks(self, parent, job, options, logger):
        results = []
        with self._manager.open(parent=parent, runner=worker.WorkRunnerExternal3) as runner:
            runner.dialog.setRange(0, 0)
            logger.addHandler(runner.progress_dialog_box_handler)
            try:
                task_builder = forseti.tasks.TaskBuilder(forseti.tasks.MultiStageTaskBuilder())
                job.initial_task(task_builder, **options)
                task = task_builder.build_task()
                for subtask in task.subtasks:
                    adapted_tool = forseti.tasks.SubtaskJobAdapter(subtask)
                    self._manager.add_job(adapted_tool, adapted_tool.settings)
                self._manager.start()
                for post_result in self._manager.get_results(lambda x, y: self._update_progress(runner, x, y)):
                    if post_result is not None:
                        results.append(post_result)

                runner.dialog.accept()
                runner.dialog.close()
                if runner.was_aborted:
                    raise TaskFailed("User Aborted")
                return results
            finally:
                logger.removeHandler(runner.progress_dialog_box_handler)
