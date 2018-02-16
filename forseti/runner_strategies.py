import abc
import traceback
import logging
import sys

import time
import typing
import warnings

from PyQt5 import QtCore, QtWidgets

import forseti.tools.abstool
# Tool, Options,
from forseti import worker
import forseti.gui


class AbsRunner(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def run(self, parent, tool: forseti.tools.abstool.AbsTool, options: dict, on_success, on_failure,
            logger: logging.Logger):
        pass


class RunRunner:
    def __init__(self, strategy: AbsRunner) -> None:
        self._strategy = strategy

    def run(self, parent, tool: forseti.tools.abstool.AbsTool, options: dict, on_success: typing.Callable,
            on_failure: typing.Callable, logger: logging.Logger) -> None:
        return self._strategy.run(parent, tool, options, on_success, on_failure, logger)


class UsingWorkWrapper(AbsRunner):

    def __init__(self) -> None:
        super().__init__()
        warnings.warn("Use UsingWorkManager instead", DeprecationWarning)

    def run(self, parent, tool: forseti.tools.abstool.AbsTool, options: dict, on_success, on_failure,
            logger: logging.Logger):
        with worker.WorkWrapper(parent, tool, logger=logger) as work_manager:

            work_manager.worker_display.finished.connect(on_success)
            work_manager.worker_display.failed.connect(on_failure)

            try:
                # self.log_manager.debug("Validating arguments")
                work_manager.valid_arguments(options)
                # tool.validate_args(**options)
                # wm.completion_callback = lambda: self._tool.on_completion()

                # Search for jobs
                job_searcher = forseti.gui.JobSearcher(tool, options)
                # print("Job search starting", file=sys.stderr)
                job_searcher.start()
                while True:
                    if job_searcher.isFinished():
                        break
                    else:
                        time.sleep(0.01)
                    # self.log_manager.info("Loading")
                    QtCore.QCoreApplication.processEvents()
                    # self.QApplication.processEvents()
                # print("Job search Finished", file=sys.stderr)

                for _job_args in job_searcher.jobs:
                    # self.log_manager.debug("Adding {} with {} to work manager".format(tool, _job_args))
                    work_manager.add_job(_job_args)

                print("running {} tasks".format(work_manager.worker_display._jobs_queue.qsize()), file=sys.stderr)
                try:
                    work_manager.run()

                    # print("AFTER")
                    # work_manager.worker_display.finish()

                except RuntimeError as e:
                    QtWidgets.QMessageBox.warning(parent, "Process failed", str(e))
                # except TypeError as e:
                #     QtWidgets.QMessageBox.critical(self, "Process failed", str(e))
                #     raise

            except ValueError as e:

                # if work_manager._working is not None:
                #     work_manager.worker_display.cancel(e, quiet=True)
                work_manager.worker_display.cancel(quiet=True)
                QtWidgets.QMessageBox.warning(parent, "Invalid setting", str(e))
                return

            except Exception as e:
                work_manager.worker_display.cancel(quiet=True)
                exception_message = traceback.format_exception(type(e), e, tb=e.__traceback__)
                msg = QtWidgets.QMessageBox(self)
                msg.setIcon(QtWidgets.QMessageBox.Critical)
                msg.setWindowTitle(str(type(e).__name__))
                msg.setText(str(e))
                msg.setDetailedText("".join(exception_message))
                # self.log_manager.fatal("Terminating application. Reason: {}".format(e))
                msg.exec_()
                print("Exiting early", file=sys.stderr)
                sys.exit(1)
            finally:
                print("out!", file=sys.stderr)


class UsingWorkManager(AbsRunner):
    def run(self, parent, tool: forseti.tools.abstool.AbsTool, options: dict, on_success, on_failure, logger):
        worker_manager = worker.WorkerManager(title=tool.name, tool=tool, parent=parent, logger=logger)
        # worker_manager.logger = logger
        try:
            with worker_manager.open(options) as work_runner:
                work_runner.start()
                work_runner.finish()

            on_success(worker_manager.results, tool.on_completion)
        except Exception as e:
            on_failure(e)


class UsingExternalManager(AbsRunner):

    def __init__(self, manager: worker.ToolJobManager) -> None:
        self._manager = manager

    def run(self, parent, tool: forseti.tools.abstool.AbsTool, options: dict, on_success, on_failure,
            logger: logging.Logger):
        try:
            with self._manager.open(options=options, tool=tool, parent=parent) as runner:

                def update_progress(current: int, total: int):
                    runner.dialog.setMaximum(total)
                    runner.dialog.setValue(current)
                    if current == total:
                        runner.dialog.accept()

                runner.abort_callback = self.on_runner_aborted
                logger.addHandler(runner.progress_dialog_box_handler)
                runner.dialog.setRange(0, 0)

                i = -1
                for i, new_setting in enumerate(tool.discover_jobs(**options)):
                    self._manager.add_job(tool, new_setting)
                    logger.info("Found {} jobs".format(i + 1))
                runner.dialog.setMaximum(i)

                self._manager.start()

                runner.dialog.show()
                results = self._manager.get_results(update_progress)

                on_success(results, tool.on_completion)
        except Exception as e:
            on_failure(e)

    def on_runner_aborted(self):
        self._manager.abort()
