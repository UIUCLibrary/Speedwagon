"""Defining execution of a given workflow steps and processes."""

from __future__ import annotations

import abc
import contextlib
import dataclasses

import logging
import os
import sys
import threading
import typing
import warnings
from abc import ABC
from types import TracebackType
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
)
import functools

from speedwagon.config.common import DEFAULT_CONFIG_DIRECTORY_NAME
import speedwagon.config
import speedwagon.config.plugins as plugins_config
import speedwagon.exceptions
import speedwagon.job
import speedwagon.plugins
import speedwagon.tasks
import speedwagon.utils
import speedwagon.runner

_T = TypeVar("_T", bound=Mapping[str, object])

if typing.TYPE_CHECKING:
    from speedwagon.job import Workflow
    from speedwagon.config import SettingsData
    from speedwagon.config.plugins import PluginDataType
    from speedwagon.tasks import Result
    from speedwagon.runner import (
        WorkflowLoaderProtocol,
        RequestMoreInfoProtocol
    )


__all__ = [
    "simple_api_run_workflow",
    "simple_api_run_workflow2",
]

module_logger = logging.getLogger(__name__)

USER_ABORTED_MESSAGE = "User Aborted"


class ConcurrentJobBackendRunner(abc.ABC):
    def __init__(
        self,
        workflow_loader_strategy: speedwagon.runner.WorkflowLoaderProtocol,
        liaison: JobManagerLiaison,
        logger=None,
    ):
        self.workflow_loader_strategy = workflow_loader_strategy
        self.liaison = liaison
        self.logger = logger or logging.Logger(__name__)
        self.global_settings: SettingsData = {}
        self.workflow_config: SettingsData = {}

        self.request_more_info_strategy: RequestMoreInfoProtocol =\
            lambda *args, **kwargs: None

    @abc.abstractmethod
    def start(self, workflow_name: str, options: SettingsData):
        """Start the job."""

    def clean_up(self) -> None:  # noqa: B027
        """Clean up concurrency resources.

        Defaults to a no-op.

        """

    @abc.abstractmethod
    def is_alive(self) -> bool:
        """Check if the worker is alive."""


class PythonThreadedWorker(threading.Thread):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.started = False
        self.job_options: Optional[JobSubmitConfig] = None
        self.workflow_name: Optional[str] = None
        self.workflow_loader_strategy: Optional[WorkflowLoaderProtocol] = None
        self.request_more_info_strategy: Optional[RequestMoreInfoProtocol] =\
            None
        self.liaison: Optional[JobManagerLiaison] = None
        self.exception: Optional[BaseException] = None

    def run(self) -> None:
        super().run()
        if not self.job_options:
            raise ValueError("Job options not set")
        self.started = True
        try:
            self._run(self.job_options)
        except Exception as exc:
            self.exception = exc

    def _run(self, config: JobSubmitConfig) -> None:
        if not self.workflow_loader_strategy:
            raise ValueError("Workflow loader strategy not set")
        if not self.workflow_name:
            raise ValueError("Workflow name not set")
        if not self.liaison:
            raise ValueError("Job liaison not set")
        if not self.request_more_info_strategy:
            raise ValueError("Request more info strategy not set")
        speedwagon.runner.run(
            workflow_name=self.workflow_name,
            config=config,
            workflow_loader_strategy=self.workflow_loader_strategy,
            request_more_info_strategy=self.request_more_info_strategy,
            async_communication=speedwagon.runner.AsyncCommunication(
                callbacks=self.liaison.callbacks,
                events=self.liaison.events,
            ),
        )
        self.liaison.events.done()


class ConcurrentJobPyThreaded(ConcurrentJobBackendRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workflow_name = None
        self._job_options = {}
        self._background_thread = PythonThreadedWorker()

    def is_alive(self) -> bool:
        return self._background_thread.is_alive()

    @property
    def config(self):
        return JobSubmitConfig(
            workflow=self.workflow_config,
            global_settings=self.global_settings,
            job=self._job_options,
        )

    def update_status(self, status):
        self.liaison.callbacks.status(status)

    def start(self, workflow_name, options):
        self.workflow_name = workflow_name
        self._job_options = options
        self._background_thread.liaison = self.liaison

        self._background_thread.request_more_info_strategy =\
            self.request_more_info_strategy

        self._background_thread.workflow_loader_strategy =\
            self.workflow_loader_strategy

        self._background_thread.job_options = self.config
        self._background_thread.workflow_name = workflow_name
        self._background_thread.start()

    def _run(self, config: JobSubmitConfig) -> None:
        if not self.request_more_info_strategy:
            raise ValueError("Request more info strategy not set")
        speedwagon.runner.run(
            workflow_name=self.workflow_name,
            config=config,
            workflow_loader_strategy=self.workflow_loader_strategy,
            request_more_info_strategy=self.request_more_info_strategy,
            async_communication=speedwagon.runner.AsyncCommunication(
                callbacks=self.liaison.callbacks,
                events=self.liaison.events,
            ),
        )
        self.liaison.events.done()

    def run_thread(self):
        self._run(self.config)

    def clean_up(self):
        self.logger.debug("Background thread joined")
        if not self._background_thread.started:
            return
        if self._background_thread.exception:
            raise self._background_thread.exception
        if self._background_thread.is_alive():
            self._background_thread.join()


@dataclasses.dataclass
class JobManagerLiaison:
    callbacks: speedwagon.runner.JobRunnerCallbacks
    events: "speedwagon.runner.AbsEvents"


# pylint: disable=too-few-public-methods
class AbsJobManager2(contextlib.AbstractContextManager):
    @abc.abstractmethod
    def submit_job(
        self,
        workflow_name: str,
        app: speedwagon.startup.AbsStarter,
        liaison: JobManagerLiaison,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Submit job to worker."""


# pylint: disable=too-few-public-methods
class BaseJobManager(AbsJobManager2, ABC):
    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.on_job_complete_callbacks: List[Callable] = []


def notify_user_of_config_error(
    logger: logging.Logger,
    config_error: speedwagon.exceptions.MissingConfiguration,
) -> None:
    logger.info(
        "Unable to start job with missing configurations. %s", config_error
    )

    if config_error.key and config_error.workflow:
        logger.debug(
            "Unable to start job with missing configurations: "
            '"%s" from "%s". '
            "\nCheck the Workflow Settings section in "
            "Speedwagon settings.",
            config_error.key,
            config_error.workflow,
        )
    else:
        logger.debug(
            "Unable to start job with missing configurations. "
            "\nReason: %s"
            "\nCheck the Workflow Settings section in "
            "Speedwagon settings.",
            config_error,
        )


def get_plugin_data(config_file: str) -> PluginDataType:
    return plugins_config.read_settings_data_plugins(
        speedwagon.utils.read_file(config_file)
    )


def default_get_plugin_data_strategy() -> PluginDataType:
    config_file_locator = speedwagon.config.StandardConfigFileLocator(
        DEFAULT_CONFIG_DIRECTORY_NAME
    )
    return get_plugin_data(config_file_locator.get_config_file())


def _default_get_workflow_options_strategy(workflow_name: str) -> SettingsData:
    config_file_locator = speedwagon.config.StandardConfigFileLocator(
        DEFAULT_CONFIG_DIRECTORY_NAME
    )
    return speedwagon.config.workflow.get_workflow_options(
        os.path.join(
            config_file_locator.get_app_data_dir(),
            speedwagon.config.workflow.WORKFLOWS_SETTINGS_YML_FILE_NAME,
        ),
        workflow_name,
    )


class BackgroundJobManager(BaseJobManager):
    @dataclasses.dataclass
    class Internal:
        exception_thrown: Optional[BaseException] = None
        backend: Optional[ConcurrentJobBackendRunner] = None

    def __init__(self) -> None:
        super().__init__()
        self._internal = self.Internal()
        self.request_more_info: RequestMoreInfoProtocol =\
            lambda *args, **kwargs: None

        self.global_settings: Optional[SettingsData] = None

        self.get_workflow_options_strategy: Callable[[str], SettingsData] = (
            _default_get_workflow_options_strategy
        )

        self.get_plugin_data_strategy: Callable[[], PluginDataType] = (
            default_get_plugin_data_strategy
        )
        self.workflow_loader_strategy: WorkflowLoaderProtocol = (
            self._get_workflow_loader_strategy(self.get_plugin_data_strategy())
        )
        self.backend_threading_strategy: Type[ConcurrentJobBackendRunner] = (
            ConcurrentJobPyThreaded
        )

    def __enter__(self) -> "BackgroundJobManager":
        self._internal.exception_thrown = None
        self._internal.backend = None
        return self

    @staticmethod
    def _get_workflow_loader_strategy(
        plugin_config_data: PluginDataType,
    ) -> Callable[[], Dict[str, Type[Workflow]]]:
        def whitelist_plugins_strategy() -> Set[Tuple[str, str]]:
            return plugins_config.get_whitelisted_plugins_from_config_data(
                plugin_config_data
            )

        register_strategy = functools.partial(
            speedwagon.plugins.register_whitelisted_plugins,
            get_whitelist_strategy=whitelist_plugins_strategy,
        )
        job_lookup_strategy = (
            speedwagon.job.FindAllWorkflowsPluggyPluginManagerStrategy(
                plugin_manager=speedwagon.plugins.get_plugin_manager(
                    register_strategy
                )
            )
        )
        return lambda: speedwagon.job.available_workflows(job_lookup_strategy)

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback_: Optional[TracebackType],
    ) -> None:
        self.clean_up()
        if self._internal.exception_thrown is not None:
            raise self._internal.exception_thrown
        logging.debug("thread threw no exceptions")

    def clean_up(self) -> None:
        if self._internal.backend is not None:
            self._internal.backend.clean_up()

    def submit_job(
        self,
        workflow_name: str,
        app: speedwagon.startup.AbsStarter,
        liaison: JobManagerLiaison,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        if (
            self._internal.backend is None or
            self._internal.backend.is_alive() is False
        ):
            backend = self.backend_threading_strategy(
                self.workflow_loader_strategy,
                liaison,
                logger=self.logger,
            )
            backend.request_more_info_strategy = self.request_more_info
            backend.workflow_config = self.get_workflow_options_strategy(
                workflow_name
            )
            backend.global_settings = self.global_settings or {}
            self._internal.backend = backend
            backend.start(workflow_name, options or {})
        else:
            warnings.warn(
                f"submit_job() called in Background manager but "
                f"self._internal.backend {self._internal.backend} and "
                "self._internal.backend.is_alive() is "
                f"{self._internal.backend.is_alive()}",
                UserWarning,
                stacklevel=2
            )


default_workflows_loader_strategy = speedwagon.job.available_workflows


def simple_api_run_workflow(
    workflow: Workflow,
    workflow_options,
    logger: Optional[logging.Logger] = None,
    request_factory: Optional[
        speedwagon.frontend.interaction.UserRequestFactory
    ] = None,
) -> None:
    """Run a workflow and block until finished.

    This is the simplest API for running a workflow.

    Args:
        workflow: Workflow
        workflow_options: dictionary of options
        logger: file stream handle for logging data
        request_factory: factory for generating the user input mid-job
    """
    warnings.warn(
        "simple_api_run_workflow is deprecated and now calls "
        "simple_api_run_workflow2 under the hood. Use "
        "simple_api_run_workflow2 instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    task_scheduler = speedwagon.runner.TaskScheduler(".")
    log_handler = None

    if logger is None:
        logger = logging.getLogger()
        log_handler = logging.StreamHandler(stream=sys.stdout)
        logger.addHandler(log_handler)
    try:
        task_scheduler.logger = logger
        logging.StreamHandler(stream=sys.stdout)
        task_scheduler.logger.setLevel(logging.INFO)

        def request_more_info(
            workflow: Workflow[_T],
            options: _T,
            pretask_results: List[speedwagon.tasks.Result[Any, Any]],
            *_,
            **__
        ) -> typing.Optional[Mapping[str, Any]]:
            factory = (
                request_factory
                or speedwagon.frontend.cli.user_interaction.CLIFactory()
            )

            return workflow.get_additional_info(
                factory, options, pretask_results
            )

        task_scheduler.request_more_info = request_more_info
        for task in task_scheduler.iter_tasks(
            workflow=workflow, options=workflow_options
        ):
            task.parent_task_log_q = type(
                "reporter", (object,), {"append": logger.info}
            )
            logger.info("%s\n", task.task_description())
            task.exec()
    finally:
        if log_handler is not None:
            task_scheduler.logger.removeHandler(log_handler)


@dataclasses.dataclass(frozen=True)
class JobSubmitConfig:
    workflow: SettingsData = dataclasses.field(default_factory=dict)
    job: SettingsData = dataclasses.field(default_factory=dict)
    global_settings: SettingsData = dataclasses.field(default_factory=dict)


def simple_api_run_workflow2(
    workflow_name: str,
    config: JobSubmitConfig,
    workflows_loader_strategy: WorkflowLoaderProtocol =
    default_workflows_loader_strategy,
    request_factory: Optional[
        speedwagon.frontend.interaction.UserRequestFactory
    ] = None,
) -> None:
    """Run a workflow and block until finished.

    This is the simplest API for running a workflow.

    Args:
        workflow_name: Workflow name
        config: Job config data
        workflows_loader_strategy: strategy for loading workflows
        request_factory: factory for generating the user input mid-job
    """

    def request_more_info(
        workflow: Workflow[_T],
        options: _T,
        pretask_results: List[Result[Any, Any]],
        *_,
        **__,
    ) -> Optional[Mapping[str, Any]]:
        factory = (
            request_factory
            or speedwagon.frontend.cli.user_interaction.CLIFactory()
        )

        return workflow.get_additional_info(factory, options, pretask_results)
    return speedwagon.runner.run(
        workflow_name=workflow_name,
        config=config,
        workflow_loader_strategy=workflows_loader_strategy,
        request_more_info_strategy=request_more_info,
    )
