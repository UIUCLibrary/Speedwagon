"""Define how Speedwagon starts up on the current system.

Use for loading and starting up the main application

Changes:
++++++++

    .. versionadded:: 0.1.4
       added a splash screen for logo

"""
import abc
import argparse
import collections
import contextlib
import io
import json
import logging
import os
import queue
import sys
import threading
import time
import typing
import webbrowser
from typing import Dict, Union, Iterator, Tuple, List, cast, Optional, Type
import yaml
from PyQt5 import QtWidgets, QtGui, QtCore  # type: ignore

import speedwagon
import speedwagon.config
import speedwagon.models
import speedwagon.tabs
import speedwagon.exceptions
from speedwagon import worker, job, runner_strategies
from speedwagon.dialog.settings import TabEditor
from speedwagon.dialog.dialogs import WorkflowProgress
from speedwagon.logging_helpers import SignalLogHandler
from speedwagon.runner_strategies import ThreadedEvents
from speedwagon.tabs import extract_tab_information
import speedwagon.gui


try:  # pragma: no cover
    from importlib import metadata
    from importlib import resources  # type: ignore
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore
    import importlib_resources as resources  # type: ignore

__all__ = [
    "ApplicationLauncher",
    "FileFormatError",
    "SingleWorkflowLauncher",
    "SingleWorkflowJSON",
    "standalone_tab_editor",
]

CONFIG_INI_FILE_NAME = "config.ini"
TABS_YML_FILE_NAME = "tabs.yml"


class FileFormatError(Exception):
    """Exception is thrown when Something wrong with the contents of a file."""


def parse_args() -> argparse.ArgumentParser:
    """Parse command line arguments."""
    return speedwagon.config.CliArgsSetter.get_arg_parser()


class CustomTabsFileReader:
    """Reads the tab file data."""

    def __init__(
            self, all_workflows: Dict[str, Type[speedwagon.Workflow]]) -> None:
        """Load all workflows supported.

        Args:
            all_workflows:
        """
        self.all_workflows = all_workflows

    @staticmethod
    def read_yml_file(yaml_file: str) -> Dict[str,  List[str]]:
        """Read the contents of the yml file."""
        with open(yaml_file, encoding="utf-8") as file_handler:
            tabs_config_data = yaml.load(file_handler.read(),
                                         Loader=yaml.SafeLoader)

        if not isinstance(tabs_config_data, dict):
            raise FileFormatError("Failed to parse file")
        return tabs_config_data

    def _get_tab_items(self,
                       tab: List[str],
                       tab_name: str) -> Dict[str, Type[job.Workflow]]:
        new_tab_items = {}
        for item_name in tab:
            try:
                workflow = self.all_workflows[item_name]
                if workflow.active is False:
                    print("workflow not active")
                new_tab_items[item_name] = workflow

            except LookupError:
                print(
                    f"Unable to load '{item_name}' in "
                    f"tab {tab_name}", file=sys.stderr)
        return new_tab_items

    def load_custom_tabs(self, yaml_file: str) -> Iterator[Tuple[str, dict]]:
        """Get custom tabs data from config yaml.

        Args:
            yaml_file: file path to a yaml file containing custom.

        Yields:
            Yields a tuple containing the name of the tab and the containing
                workflows.
        Notes:
            Failure to load will only a print message to standard error.

        """
        try:
            tabs_config_data = self.read_yml_file(yaml_file)
            if tabs_config_data:
                tabs_config_data = cast(Dict[str, List[str]], tabs_config_data)
                for tab_name in tabs_config_data:
                    try:
                        new_tab = tabs_config_data.get(tab_name)
                        if new_tab is not None:
                            yield tab_name, \
                                  self._get_tab_items(new_tab, tab_name)

                    except TypeError as tab_error:
                        print("Error loading tab '{}'. "
                              "Reason: {}".format(tab_name, tab_error),
                              file=sys.stderr)
                        continue

        except FileNotFoundError as error:
            print("Custom tabs file not found. "
                  "Reason: {}".format(error), file=sys.stderr)
        except AttributeError as error:
            print("Custom tabs file failed to load. "
                  "Reason: {}".format(error), file=sys.stderr)

        except yaml.YAMLError as error:
            print("{} file failed to load. "
                  "Reason: {}".format(yaml_file, error), file=sys.stderr)


def get_custom_tabs(
        all_workflows: Dict[str, Type[speedwagon.Workflow]],
        yaml_file: str
) -> Iterator[Tuple[str, dict]]:
    """Load custom tab yaml file."""
    getter = CustomTabsFileReader(all_workflows)
    yield from getter.load_custom_tabs(yaml_file)


class AbsStarter(metaclass=abc.ABCMeta):
    config_file: str
    tabs_file: str
    user_data_dir: str
    app_data_dir: str

    @abc.abstractmethod
    def run(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        pass

    def initialize(self) -> None:
        """Initialize startup routine."""


class StartupDefault(AbsStarter):
    """Default startup.

    .. versionadded:: 0.2.0
       Added StartupDefault class for speedwagon with the normal Qt-based GUI.
    """

    def __init__(self, app: QtWidgets.QApplication = None) -> None:
        """Create a new default startup routine."""
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.DEBUG)

        self.handler = logging.StreamHandler(stream=sys.stderr)
        self.handler.setLevel(logging.DEBUG)
        self.platform_settings = speedwagon.config.get_platform_settings()

        self.config_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            CONFIG_INI_FILE_NAME
        )

        self.tabs_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            TABS_YML_FILE_NAME
        )

        # Make sure required directories exists
        self.user_data_dir = typing.cast(
            str, self.platform_settings.get("user_data_directory")
        )

        self.startup_settings: Dict[str, Union[str, bool]] = {}
        self._debug = False

        self.app_data_dir = typing.cast(
            str, self.platform_settings.get("app_data_directory")
        )
        self.app = app or QtWidgets.QApplication(sys.argv)

    def initialize(self) -> None:
        self.ensure_settings_files()
        self.resolve_settings()

    def run(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        # Display a splash screen until the app is loaded
        with resources.open_binary(speedwagon.__name__, "logo.png") as logo:
            splash = QtWidgets.QSplashScreen(
                QtGui.QPixmap(logo.name).scaled(400, 400))

        splash.setEnabled(False)
        splash.setWindowFlags(
            cast(
                QtCore.Qt.WindowType,
                QtCore.Qt.WindowStaysOnTopHint |
                QtCore.Qt.FramelessWindowHint
             )
        )
        splash_message_handler = speedwagon.gui.SplashScreenLogHandler(splash)

        # If debug mode, print the log messages directly on the splash screen
        if self._debug:
            splash_message_handler.setLevel(logging.DEBUG)
        else:
            splash_message_handler.setLevel(logging.INFO)

        splash.show()
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents)

        set_app_display_metadata(self.app)

        with worker.ToolJobManager() as work_manager:

            work_manager.settings_path = \
                self.platform_settings.get_app_data_directory()

            windows = speedwagon.gui.MainWindow1(
                work_manager=work_manager,
                debug=cast(bool, self.startup_settings['debug'])
            )

            windows.setWindowTitle("")
            self._logger.addHandler(splash_message_handler)

            self._logger.addHandler(windows.log_data_handler)
            self._logger.addHandler(windows.console_log_handler)

            app_title = speedwagon.__name__.title()
            try:
                app_version = metadata.version(__package__)
            except metadata.PackageNotFoundError:
                app_version = ""

            self._logger.info("%s %s", app_title, app_version)

            QtWidgets.QApplication.processEvents()

            self.load_configurations(work_manager)
            self._load_workflows(windows)

            self._logger.debug("Loading User Interface")

            windows.show()

            if "starting-tab" in self.startup_settings:
                windows.set_current_tab(
                    tab_name=cast(str, self.startup_settings['starting-tab']))

            splash.finish(windows)

            self._logger.info("Ready")
            self._logger.removeHandler(windows.log_data_handler)
            self._logger.removeHandler(windows.console_log_handler)
            self._logger.removeHandler(splash_message_handler)
            return self.app.exec_()

    def load_configurations(self,
                            work_manager: "worker.ToolJobManager") -> None:

        self._logger.debug("Applying settings to Speedwagon")
        work_manager.user_settings = self.platform_settings
        work_manager.configuration_file = self.config_file

    def _load_workflows(self, application: speedwagon.gui.MainWindow1) -> None:
        self._logger.debug("Loading Workflows")
        loading_workflows_stream = io.StringIO()
        with contextlib.redirect_stderr(loading_workflows_stream):
            all_workflows = job.available_workflows()
        # Load every user configured tab
        tabs_file_size = os.path.getsize(self.tabs_file)
        if tabs_file_size > 0:
            try:
                for tab_name, extra_tab in \
                        get_custom_tabs(all_workflows, self.tabs_file):
                    application.add_tab(tab_name, collections.OrderedDict(
                        sorted(extra_tab.items())))
            except FileFormatError as error:
                self._logger.warning(
                    "Unable to load custom tabs from %s. Reason: %s",
                    self.tabs_file,
                    error
                )
        # All Workflows tab
        self._logger.debug("Loading Tab All")
        application.add_tab("All", collections.OrderedDict(
            sorted(all_workflows.items())))
        workflow_errors_msg = loading_workflows_stream.getvalue().strip()
        if workflow_errors_msg:
            for line in workflow_errors_msg.split("\n"):
                self._logger.warning(line)

    def resolve_settings(
            self,
            resolution_strategy_order: Optional[List[
                speedwagon.config.AbsSetting]
            ] = None,
            loader: typing.Optional[speedwagon.config.ConfigLoader] = None
    ) -> None:
        loader = loader or speedwagon.config.ConfigLoader(self.config_file)

        self.platform_settings._data.update(
            loader.read_settings_file(self.config_file)
        )
        loader.logger = self._logger
        if resolution_strategy_order:
            loader.resolution_strategy_order = resolution_strategy_order
        results = loader.get_settings()

        self.startup_settings = results
        self._debug = self._get_debug(results)

    def _get_debug(self, settings) -> bool:
        try:
            debug = cast(bool, settings['debug'])
        except KeyError:
            self._logger.warning(
                "Unable to find a key for debug mode. Setting false")

            debug = False
        return bool(debug)

    def ensure_settings_files(self) -> None:
        speedwagon.config.ensure_settings_files(self, self._logger)


class WorkflowProgressCallbacks(runner_strategies.AbsJobCallbacks):
    class WorkflowSignals(QtCore.QObject):
        error = QtCore.pyqtSignal([object, object, object])
        progress_changed = QtCore.pyqtSignal(int)
        total_jobs_changed = QtCore.pyqtSignal(int)
        cancel_complete = QtCore.pyqtSignal()
        message = QtCore.pyqtSignal(str, int)
        status_changed = QtCore.pyqtSignal(str)
        started = QtCore.pyqtSignal()
        finished = QtCore.pyqtSignal(runner_strategies.JobSuccess)

        def __init__(self, parent: WorkflowProgress) -> None:
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
            self.message.emit(text, level)

        @QtCore.pyqtSlot(str)
        def set_banner_text(self, text: str) -> None:
            self.dialog_box.banner.setText(text)

        def set_status(self, text: str) -> None:
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

        @QtCore.pyqtSlot(object)
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
            self.finished.emit(result)
            self.dialog_box.flush()

        def cancelling_complete(self) -> None:
            self.cancel_complete.emit()
            self.dialog_box.flush()

        def update_progress(self, current: Optional[int],
                            total: Optional[int]) -> None:
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
            self.error.emit(message, exc, traceback_string)

    def __init__(self, dialog_box: WorkflowProgress) -> None:
        super().__init__()

        self.signals = WorkflowProgressCallbacks.WorkflowSignals(dialog_box)

        self.log_handler = SignalLogHandler(signal=self.signals.message)

    def log(self, text: str, level: int = logging.INFO) -> None:
        self.signals.log(text, level)

    def set_banner_text(self, text: str) -> None:
        self.signals.set_banner_text(text)

    def error(
            self,
            message: Optional[str] = None,
            exc: Optional[BaseException] = None,
            traceback_string: Optional[str] = None
    ) -> None:
        self.signals.submit_error(message, exc, traceback_string)

    def start(self) -> None:
        self.signals.started.emit()
        self.signals.dialog_box.start()

    def finished(self, result: runner_strategies.JobSuccess) -> None:
        self.signals.finished_called(result)

    def cancelling_complete(self) -> None:
        self.signals.cancelling_complete()

    def refresh(self) -> None:
        QtCore.QCoreApplication.processEvents()

    def update_progress(self, current: Optional[int],
                        total: Optional[int]) -> None:
        self.signals.update_progress(current, total)

    def status(self, text: str) -> None:
        self.signals.set_status(text)


def set_app_display_metadata(app: QtWidgets.QApplication) -> None:
    with resources.open_binary(speedwagon.__name__, "favicon.ico") as icon:
        app.setWindowIcon(QtGui.QIcon(icon.name))
    try:
        app.setApplicationVersion(metadata.version(__package__))
    except metadata.PackageNotFoundError:
        pass
    app.setApplicationDisplayName(f"{speedwagon.__name__.title()}")
    QtWidgets.QApplication.processEvents()


class QtRequestMoreInfo(QtCore.QObject):
    request = QtCore.pyqtSignal(object, object, object, object)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget]) -> None:
        super().__init__(parent)
        self.results = None
        self._parent = parent
        self.exc: Optional[BaseException] = None
        self.request.connect(self._request)

    def _request(self, user_is_interacting: threading.Condition,
                 workflow: speedwagon.Workflow,
                 options,
                 pre_results
                 ):
        with user_is_interacting:
            try:
                self.results = workflow.get_additional_info(
                    self._parent,
                    options=options,
                    pretask_results=pre_results
                )
            except job.JobCancelled as exc:
                self.exc = exc
            except BaseException as exc:
                self.exc = exc
                raise
            finally:
                user_is_interacting.notify()


class StartQtThreaded(AbsStarter):

    def __init__(self, app: QtWidgets.QApplication = None) -> None:
        self.startup_settings: Dict[str, Union[str, bool]] = {
            'debug': False
        }

        self.windows: Optional[speedwagon.gui.MainWindow2] = None
        self.logger = logging.getLogger()

        formatter = logging.Formatter(
            '%(asctime)-15s %(threadName)s %(message)s'
        )

        self.platform_settings = speedwagon.config.get_platform_settings()
        self.app = app or QtWidgets.QApplication(sys.argv)
        self._debug = False
        self._log_data = io.StringIO()

        self.log_data_handler = logging.StreamHandler(self._log_data)
        self.log_data_handler.setLevel(logging.DEBUG)
        self.log_data_handler.setFormatter(formatter)

        self.logger.addHandler(self.log_data_handler)
        self.logger.setLevel(logging.DEBUG)

        self.load_settings()
        set_app_display_metadata(self.app)
        self._request_window = QtRequestMoreInfo(self.windows)

    def load_settings(self) -> None:
        self.user_data_dir = typing.cast(
            str, self.platform_settings.get("user_data_directory")
        )

        self.config_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            CONFIG_INI_FILE_NAME
        )

        self.app_data_dir = typing.cast(
            str, self.platform_settings["app_data_directory"]
        )

        self.tabs_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            TABS_YML_FILE_NAME
        )

    def _load_help(self) -> None:
        try:
            pkg_metadata = dict(metadata.metadata(speedwagon.__name__))
            webbrowser.open_new(pkg_metadata['Home-page'])
        except metadata.PackageNotFoundError as error:
            self.logger.warning(
                "No help link available. Reason: %s", error)

    def ensure_settings_files(self) -> None:
        speedwagon.config.ensure_settings_files(
            self,
            logger=self.logger
        )

    def read_settings_file(
            self,
            settings_file: str
    ) -> Dict[str, Union[str, bool]]:

        with speedwagon.config.ConfigManager(settings_file) as config:
            return config.global_settings

    def resolve_settings(
            self,
            resolution_strategy_order: Optional[
                List[speedwagon.config.AbsSetting]
            ] = None,
            loader: speedwagon.config.ConfigLoader = None
    ) -> Dict[str, Union[str, bool]]:

        loader = loader or speedwagon.config.ConfigLoader(self.config_file)

        self.platform_settings._data.update(
            loader.read_settings_file(self.config_file)
        )

        loader.logger = self.logger
        if resolution_strategy_order:
            loader.resolution_strategy_order = resolution_strategy_order

        results = loader.get_settings()

        self.startup_settings = results
        self._debug = self._get_debug(results)
        return self.startup_settings

    def _get_debug(self, settings) -> bool:
        try:
            debug = cast(bool, settings['debug'])
        except KeyError:
            self.logger.warning(
                "Unable to find a key for debug mode. Setting false")

            debug = False
        return bool(debug)

    def initialize(self) -> None:
        self.ensure_settings_files()
        self.startup_settings = self.resolve_settings()

    def _load_workflows(self, application: speedwagon.gui.MainWindow2) -> None:
        tabs_file = os.path.join(
            self.platform_settings.get_app_data_directory(),
            TABS_YML_FILE_NAME
        )

        self.logger.debug("Loading Workflows")
        loading_workflows_stream = io.StringIO()
        with contextlib.redirect_stderr(loading_workflows_stream):
            all_workflows = job.available_workflows()

        for workflow_name, error in \
                self._find_invalid(all_workflows):
            error_message = \
                f"Unable to load workflow '{workflow_name}'. Reason: {error}"

            self.logger.error(error_message)
            application.console.add_message(error_message)
            del all_workflows[workflow_name]

        # Load every user configured tab
        self.load_custom_tabs(application, tabs_file, all_workflows)

        # All Workflows tab
        self.load_all_workflows_tab(application, all_workflows)

        workflow_errors_msg = loading_workflows_stream.getvalue().strip()
        if workflow_errors_msg:
            for line in workflow_errors_msg.split("\n"):
                self.logger.warning(line)

    def load_all_workflows_tab(
            self,
            application: speedwagon.gui.MainWindow2,
            loaded_workflows: typing.Dict[str, Type[speedwagon.Workflow]]
    ) -> None:
        self.logger.debug("Loading Tab All")
        application.add_tab(
            "All",
            collections.OrderedDict(
                sorted(loaded_workflows.items())
            )
        )

    def load_custom_tabs(
            self,
            main_window: speedwagon.gui.MainWindow2,
            tabs_file: str,
            loaded_workflows: typing.Dict[str, Type[speedwagon.Workflow]]
    ) -> None:
        tabs_file_size = os.path.getsize(tabs_file)
        if tabs_file_size > 0:
            try:
                for tab_name, extra_tab in \
                        get_custom_tabs(loaded_workflows, tabs_file):
                    main_window.add_tab(tab_name, collections.OrderedDict(
                        sorted(extra_tab.items())))
            except FileFormatError as error:
                self.logger.warning(
                    "Unable to load custom tabs from %s. Reason: %s",
                    tabs_file,
                    error
                )

    def save_log(self, parent: QtWidgets.QWidget = None) -> None:
        data = self._log_data.getvalue()
        epoch_in_minutes = int(time.time() / 60)
        while True:
            log_file_name, _ = \
                QtWidgets.QFileDialog.getSaveFileName(
                    parent,
                    "Export Log",
                    "speedwagon_log_{}.txt".format(epoch_in_minutes),
                    "Text Files (*.txt)")

            if not log_file_name:
                return
            try:
                with open(log_file_name, "w", encoding="utf-8") as file_handle:
                    file_handle.write(data)
            except OSError as error:
                message_box = QtWidgets.QMessageBox(parent)
                message_box.setText("Saving Log Failed")
                message_box.setDetailedText(str(error))
                message_box.exec_()
                continue

            self.logger.info("Saved log to %s", log_file_name)
            break

    @staticmethod
    def request_system_info(
            parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        speedwagon.dialog.dialogs.SystemInfoDialog(parent).exec()

    @staticmethod
    def request_settings(parent: QtWidgets.QWidget = None) -> None:
        platform_settings = speedwagon.config.get_platform_settings()
        settings_path = platform_settings.get_app_data_directory()

        dialog_builder = \
            speedwagon.dialog.settings.SettingsBuilder(parent=parent)

        dialog_builder.add_open_settings(
            platform_settings.get_app_data_directory()
        )

        dialog_builder.add_global_settings(
            os.path.join(settings_path, CONFIG_INI_FILE_NAME)
        )

        dialog_builder.add_tabs_setting(
            os.path.join(settings_path, TABS_YML_FILE_NAME)
        )

        config_dialog = dialog_builder.build()
        config_dialog.exec_()

    def run(self, app: Optional[QtWidgets.QApplication] = None) -> int:

        with runner_strategies.BackgroundJobManager() as job_manager:
            self.windows = speedwagon.gui.MainWindow2(
                job_manager=job_manager,
                settings=self.startup_settings
            )

            if self.windows is None:
                return 1

            self.windows.console.attach_logger(self.logger)
            self.windows.configuration_requested.connect(
                self.request_settings
            )

            self.windows.save_logs_requested.connect(self.save_log)

            self.windows.system_info_requested.connect(
                self.request_system_info
            )
            self.windows.help_requested.connect(self._load_help)
            self.windows.submit_job.connect(
                lambda workflow_name, options:
                self.submit_job(
                    self.windows,
                    job_manager,
                    workflow_name,
                    options
                )
            )

            self._load_workflows(self.windows)
            self.windows.show()
            return self.app.exec_()

    @staticmethod
    def abort_job(
            dialog: WorkflowProgress,
            events: runner_strategies.AbsEvents
    ) -> None:
        dialog.stop()
        events.stop()

    def request_more_info(self, workflow, options, pre_results):
        waiter = threading.Condition()
        with waiter:
            self._request_window.request.emit(
                waiter,
                workflow,
                options,
                pre_results
            )
            waiter.wait()
        if self._request_window.exc is not None:
            raise self._request_window.exc
        return self._request_window.results

    def submit_job(
            self,
            main_app: typing.Optional[speedwagon.gui.MainWindow2],
            job_manager: runner_strategies.BackgroundJobManager,
            workflow_name: str,
            options: Dict[str, typing.Any]
    ) -> None:

        workflow_class = \
            job.available_workflows().get(workflow_name)
        try:
            if workflow_class is None:
                raise ValueError(f"Unknown workflow: '{workflow_name}'")
            workflow_class.validate_user_options(**options)
        except ValueError as user_option_error:
            self.report_exception(
                parent=main_app,
                exc=user_option_error,
                dialog_box_title="Invalid User Options"
            )
            return

        dialog_box = WorkflowProgress(parent=self.windows)
        if main_app is not None:
            dialog_box.rejected.connect(main_app.close)

        dialog_box.setWindowTitle(workflow_name)
        dialog_box.show()
        threaded_events = ThreadedEvents()

        dialog_box.aborted.connect(
            lambda: self.abort_job(dialog_box, threaded_events)
        )
        callbacks = WorkflowProgressCallbacks(dialog_box)
        if main_app is not None:
            callbacks.signals.finished.connect(
                main_app.console.log_handler.flush
            )

        dialog_box.attach_logger(self.logger)
        setattr(job_manager, "request_more_info", self.request_more_info)
        job_manager.submit_job(
            workflow_name=workflow_name,
            options=options,
            app=self,
            liaison=runner_strategies.JobManagerLiaison(
                callbacks=callbacks,
                events=threaded_events
            )
        )
        threaded_events.started.set()

    def report_exception(
            self,
            exc: BaseException,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            dialog_box_title: Optional[str] = None,
    ) -> None:
        text = str(exc)
        self.logger.error(text)
        dialog_box = QtWidgets.QMessageBox(parent)
        if dialog_box_title is not None:
            dialog_box.setWindowTitle(dialog_box_title)
        dialog_box.setText(text)
        dialog_box.exec_()

    def _find_invalid(
            self,
            workflows: typing.Dict[str, typing.Type[speedwagon.Workflow]]
    ) -> typing.Iterable[
            typing.Tuple[str, str]
    ]:
        for title, workflow in workflows.copy().items():
            try:
                workflow(global_settings=self.startup_settings)
            except (
                    speedwagon.exceptions.SpeedwagonException,
                    AttributeError
            ) as error:
                yield title, str(error)


class SingleWorkflowLauncher(AbsStarter):
    """Single workflow launcher.

    .. versionadded:: 0.2.0
       Added SingleWorkflowLauncher class for running a single workflow \
            without user interaction. Useful for building new workflows.

    """

    def __init__(self, logger: typing.Optional[logging.Logger] = None) -> None:
        """Set up window for running a single workflow."""
        super().__init__()
        self.window: Optional[speedwagon.gui.MainWindow1] = None
        self._active_workflow: Optional[job.AbsWorkflow] = None
        self.options: Dict[str, Union[str, bool]] = {}
        self.logger = logger or logging.getLogger(__name__)

    def run(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        """Run the workflow configured with the options given."""
        if self._active_workflow is None:
            raise AttributeError("Workflow has not been set")

        with worker.ToolJobManager() as work_manager:
            work_manager.logger = self.logger
            self._run(work_manager)
        return 0

    def _run(self, work_manager: worker.ToolJobManager) -> None:
        if self._active_workflow is None:
            raise ValueError("No active workflow set")

        window = speedwagon.gui.MainWindow1(
            work_manager=work_manager,
            debug=False)

        window.show()
        if self._active_workflow.name is not None:
            window.setWindowTitle(self._active_workflow.name)
        runner_strategy = \
            runner_strategies.QtRunner(window)

        self._active_workflow.validate_user_options(**self.options)
        # runner_strategy.additional_info_callback

        runner_strategy.run(self._active_workflow,
                            self.options,
                            window.log_manager)
        window.log_manager.handlers.clear()
        window.close()

    def set_workflow(self, workflow: job.AbsWorkflow) -> None:
        """Set the current workflow."""
        self._active_workflow = workflow


class SingleWorkflowJSON(AbsStarter):
    """Start up class for loading instructions from a JSON file.

    .. versionadded:: 0.2.0
        SingleWorkflowJSON class added

    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """Create a environment where the workflow is loaded from a json file.

        Args:
            logger: Optional Logger, defaults to default logger for __name__.
        """
        self.options: typing.Optional[typing.Dict[str, typing.Any]] = None
        self.workflow: typing.Optional[job.AbsWorkflow] = None
        self.logger = logger or logging.getLogger(__name__)

    def load_json_string(self, data: str) -> None:
        """Load json data containing options and workflow info.

        Args:
            data: JSON data as a string.

        """
        loaded_data = json.loads(data)
        self.options = loaded_data['options']
        self._set_workflow(loaded_data['workflow'])

    def _set_workflow(self, workflow_name: str) -> None:
        available_workflows = job.available_workflows()
        self.workflow = available_workflows[workflow_name]()

    def run(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        """Launch Speedwagon."""
        if self.options is None:
            raise ValueError("no data loaded")
        if self.workflow is None:
            raise ValueError("no workflow loaded")

        with worker.ToolJobManager() as work_manager:
            work_manager.logger = self.logger

            self._run(work_manager, self.workflow, self.options)
        return 0

    def initialize(self) -> None:
        """Initialize environment."""
        if self.options is None:
            raise ValueError("no data loaded")
        if self.workflow is None:
            raise ValueError("no workflow loaded")

    @staticmethod
    def _run(work_manager: "worker.ToolJobManager",
             workflow: job.AbsWorkflow,
             options: Dict[str, typing.Any]) -> None:
        window = SingleWorkflowJSON._load_window(work_manager, workflow.name)
        window.show()
        runner_strategy = runner_strategies.QtRunner(window)

        workflow.validate_user_options(**options)

        runner_strategy.run(workflow,
                            options,
                            window.log_manager)
        window.log_manager.handlers.clear()

    @staticmethod
    def _load_window(work_manager: "worker.ToolJobManager",
                     title: Optional[str]) -> speedwagon.gui.MainWindow1:
        window = speedwagon.gui.MainWindow1(
            work_manager=work_manager,
            debug=False)

        if title is not None:
            window.setWindowTitle(title)

        return window


class MultiWorkflowLauncher(AbsStarter):

    def __init__(self, logger:  Optional[logging.Logger] = None) -> None:
        super().__init__()
        self.logger = logger or logging.getLogger(__name__)
        self._pending_tasks: \
            "queue.Queue[Tuple[job.AbsWorkflow, Dict[str, typing.Any]]]" \
            = queue.Queue()

    def run(self, app: Optional[QtWidgets.QApplication] = None) -> int:
        with worker.ToolJobManager() as work_manager:
            work_manager.logger = self.logger
            self._run(work_manager)
        return 0

    def _run(self, work_manager: worker.ToolJobManager) -> None:
        window = speedwagon.gui.MainWindow1(
            work_manager=work_manager,
            debug=False)

        window.show()
        try:
            while not self._pending_tasks.empty():
                active_workflow, options = self._pending_tasks.get()
                if active_workflow.name is not None:
                    window.setWindowTitle(active_workflow.name)
                runner_strategy = \
                    runner_strategies.QtRunner(window)

                active_workflow.validate_user_options(**options)

                runner_strategy.run(
                    active_workflow,
                    options,
                    window.log_manager
                )

                self._pending_tasks.task_done()
        except runner_strategies.TaskFailed as task_error:
            raise job.JobCancelled(task_error) from task_error

        finally:
            window.log_manager.handlers.clear()
            window.close()

    def add_job(self, workflow, args):
        self._pending_tasks.put((workflow, args))


class TabsEditorApp(QtWidgets.QDialog):
    """Dialog box for editing tabs.yml file."""

    def __init__(self, *args, **kwargs) -> None:
        """Create a tabs editor dialog window."""
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Speedwagon Tabs Editor")
        layout = QtWidgets.QVBoxLayout()
        self.editor = TabEditor()
        layout.addWidget(self.editor)
        self.dialog_button_box = QtWidgets.QDialogButtonBox(self)
        layout.addWidget(self.dialog_button_box)

        self.dialog_button_box.setStandardButtons(
            cast(
                QtWidgets.QDialogButtonBox.StandardButtons,
                QtWidgets.QDialogButtonBox.Cancel |
                QtWidgets.QDialogButtonBox.Ok
            )
        )

        self.setLayout(layout)

        self.dialog_button_box.accepted.connect(self.on_okay)
        self.dialog_button_box.rejected.connect(self.on_cancel)
        self.rejected.connect(self.on_cancel)

    def load_all_workflows(self) -> None:
        workflows = job.available_workflows()
        self.editor.set_all_workflows(workflows)

    def on_okay(self) -> None:
        if self.editor.modified is True:
            if self.tabs_file is None:
                return
            print("Saving changes")
            tabs = extract_tab_information(
                self.editor.selectedTabComboBox.model())

            speedwagon.tabs.write_tabs_yaml(self.tabs_file, tabs)

        self.close()

    def on_cancel(self) -> None:
        self.close()

    def load_tab_file(self, filename: str) -> None:
        """Load tab file."""
        self.editor.tabs_file = filename

    @property
    def tabs_file(self) -> Optional[str]:
        return self.editor.tabs_file

    @tabs_file.setter
    def tabs_file(self, value: str) -> None:
        self.editor.tabs_file = value


def standalone_tab_editor(app: QtWidgets.QApplication = None) -> None:
    """Launch standalone tab editor app."""
    print("Loading settings")
    settings = speedwagon.config.get_platform_settings()

    app = app or QtWidgets.QApplication(sys.argv)
    print("Loading tab editor")
    editor = TabsEditorApp()
    editor.load_all_workflows()

    tabs_file = \
        os.path.join(settings.get_app_data_directory(), TABS_YML_FILE_NAME)

    editor.load_tab_file(tabs_file)

    print("displaying tab editor")
    editor.show()
    app.exec()


class ApplicationLauncher:
    """Application launcher.

    .. versionadded:: 0.2.0
       Added ApplicationLauncher for launching speedwagon in different ways.

    Examples:
       The easy way

        .. testsetup::

            from speedwagon.startup import ApplicationLauncher, StartupDefault
            from unittest.mock import Mock

        .. doctest::
           :skipif: True

           >>> app = ApplicationLauncher()
           >>> app.run()

       or

        .. testsetup::

            from speedwagon.workflows.workflow_capture_one_to_dl_compound_and_dl import CaptureOneToDlCompoundAndDLWorkflow  # noqa: E501 pylint: disable=line-too-long


        .. testcode::
           :skipif: True

           >>> startup_strategy = SingleWorkflowLauncher()
           >>> startup_strategy.set_workflow(
           ...      CaptureOneToDlCompoundAndDLWorkflow()
           ... )
           >>> startup_strategy.options = {
           ...      "Input": "source/images/",
           ...      "Package Type": "Capture One",
           ...      "Output Digital Library": "output/dl",
           ...      "Output HathiTrust": "output/ht"
           ... }
           >>> app = ApplicationLauncher(strategy=startup_strategy)
           >>> app.run()
    """

    def __init__(self, strategy: AbsStarter = None) -> None:
        """Strategy pattern for loading speedwagon in different ways.

        Args:
            strategy: Starter strategy class.
        """
        super().__init__()
        self.strategy = strategy or StartQtThreaded()

    def initialize(self) -> None:
        """Initialize anything that needs to done prior to running."""
        self.strategy.initialize()

    def run(self, app=None) -> int:
        """Run Speedwagon."""
        return self.strategy.run(app)


def main(argv: List[str] = None) -> None:
    """Launch main entry point."""
    argv = argv or sys.argv
    if "tab-editor" in argv:
        standalone_tab_editor()
        return
    app = ApplicationLauncher()
    app.initialize()
    sys.exit(app.run())


if __name__ == '__main__':
    main()
