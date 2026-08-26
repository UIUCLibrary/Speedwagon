"""Define how Speedwagon starts up on the current system.

Use for loading and starting up the main application

Changes:
++++++++

    .. versionadded:: 0.1.4
       added a splash screen for logo

"""

from __future__ import annotations
import abc
import argparse
import contextlib
import functools
import io
import logging
import os
import sys
import traceback
import warnings
from typing import (
    Dict,
    Iterator,
    Tuple,
    List,
    Type,
    TYPE_CHECKING,
    Optional,
    Callable,
    Any,
    Collection,
    TypeVar,
    Mapping,
    Union,
    Iterable,
    Sequence, cast,
)

import speedwagon.job
import speedwagon.config
import speedwagon.info
from speedwagon.config.workflow import (
    default_backend_factory,
    AbsWorkflowBackend,
)
from speedwagon.config.plugins import (
    get_whitelisted_plugins_from_config_data,
    read_settings_data_plugins
)
from speedwagon.config.common import DEFAULT_CONFIG_DIRECTORY_NAME
from speedwagon.config import StandardConfigFileLocator
from speedwagon.exceptions import WorkflowLoadFailure, TabLoadFailure
from speedwagon.tasks.system import CallbackSystemTask, AbsSystemTask
from speedwagon.tasks.utils import TaskBuilder
from speedwagon import plugins
import speedwagon.workflow
from speedwagon.utils import parse_json_file, read_file

if TYPE_CHECKING:
    import speedwagon.frontend.qtwidgets.gui_startup
    from speedwagon.config.common import SettingsData
    from speedwagon.config.config import (
        AbsSettingLocator,
        AbsConfigSettings,
        SettingsLocations,
    )

__all__ = [
    "ApplicationLauncher",
]

_T = TypeVar("_T", bound=Mapping[str, object])


logger = logging.getLogger(__name__)


def parse_args() -> argparse.ArgumentParser:
    """Parse command line arguments."""
    return speedwagon.config.config.CliArgsSetter.get_arg_parser()


class AbsTabFileReader(abc.ABC):  # pylint: disable=too-few-public-methods
    def __init__(
        self, all_workflows: Dict[str, Type[speedwagon.job.Workflow]]
    ) -> None:
        """Load all workflows supported.

        Args:
            all_workflows: Source workflows referred to by file.
        """
        self.all_workflows = all_workflows

    @abc.abstractmethod
    def load_custom_tabs(
        self, strategy: speedwagon.config.tabs.AbsTabsConfigDataManagement
    ) -> Iterator[Tuple[str, dict]]:
        """Get custom tabs data from file.

        Args:
            strategy: strategy for retrieving the tab data.

        Yields:
            Yields a tuple containing the name of the tab and the
                containing workflows.
        """


class CustomTabsFileReader(AbsTabFileReader):
    """Reads the tab file data."""

    def _load_workflow(
        self, workflow_name: str
    ) -> Type[speedwagon.job.Workflow[_T]]:
        workflow = self.all_workflows[workflow_name]
        if workflow.active is False:
            logger.warning("Loading workflow that is not active")
        return workflow

    def load_custom_tabs(
        self, strategy: speedwagon.config.tabs.AbsTabsConfigDataManagement
    ) -> Iterator[Tuple[str, dict]]:
        """Get custom tabs data from config yaml.

        Args:
            strategy: strategy for retrieving the tab data.

        Yields:
            Yields a tuple containing the name of the tab and the
                containing workflows.
        """
        try:
            for tab_entity in strategy.data():
                try:
                    yield (
                        tab_entity.tab_name,
                        self.gather_registered_workflows(
                            tab_entity.workflow_names
                        ),
                    )
                except TabLoadFailure as error:
                    logger.error(
                        "Custom tab %s failed to load. Reason: %s",
                        tab_entity.tab_name,
                        error,
                    )
                    raise
        except TabLoadFailure as error:
            print(
                f"Custom tabs failed to load. Reason: {error}", file=sys.stderr
            )
        except AttributeError as error:
            print(
                f"Custom tabs failed to load. Reason: {error}", file=sys.stderr
            )

    def gather_registered_workflows(
        self, workflow_names: Collection[str]
    ) -> Dict[str, Type[speedwagon.job.Workflow[_T]]]:
        new_tab_items: Dict[str, Type[speedwagon.job.Workflow[_T]]] = {}
        for item_name in workflow_names:
            try:
                if item_name not in self.all_workflows:
                    raise WorkflowLoadFailure("Workflow not registered.")
                new_tab_items[item_name] = self._load_workflow(item_name)
            except WorkflowLoadFailure as error:
                print(
                    f"Unable to load workflow '{item_name}'. "
                    f"Reason: {error}",
                    file=sys.stderr,
                )
                continue

        return new_tab_items


def get_custom_tabs(
    all_workflows: Dict[str, Type[speedwagon.job.Workflow]],
    yaml_file: str,
    reader_klass: Type[AbsTabFileReader] = CustomTabsFileReader,
) -> Iterator[Tuple[str, dict]]:
    """Load custom tab yaml file."""
    getter = reader_klass(all_workflows)
    try:
        yield from getter.load_custom_tabs(
            strategy=speedwagon.config.tabs.CustomTabsYamlConfig(yaml_file)
        )
    except FileNotFoundError as error:
        print(f"Custom tabs file not found. Reason: {error}", file=sys.stderr)


class ApplicationLauncher:
    """Application launcher.

    .. versionadded:: 0.2.0
       Added ApplicationLauncher for launching speedwagon in different ways.
    """

    strategy: AbsStarter

    def __init__(self, strategy: Optional[AbsStarter] = None) -> None:
        """Strategy pattern for loading speedwagon in different ways.

        Args:
            strategy: Starter strategy class.
        """
        super().__init__()
        self.application_name = "speedwagon"
        self.application_config_directory_name = "Speedwagon"
        self.settings_resolver: Optional[
            speedwagon.frontend.qtwidgets.gui_startup.ResolveSettings
        ] = None
        self.startup_tasks: List[AbsSystemTask] = []
        try:
            # Avoid circular imports!  pylint: disable=import-outside-toplevel
            from speedwagon.frontend.qtwidgets.gui_startup import (
                StartQtThreaded,
                ResolveSettings,
                ResolveSettingsStrategyConfigAdapter,
            )

            self.settings_resolver = ResolveSettings()
            self.settings_resolver.config_file_locator_strategy = (
                lambda: StandardConfigFileLocator(
                    self.application_config_directory_name
                ).get_config_file()
            )

            config_backend_factory = functools.partial(
                speedwagon.config.workflow.default_backend_factory,
                config_directory_name=self.application_config_directory_name,
            )
            self.strategy = strategy or StartQtThreaded(
                config=ResolveSettingsStrategyConfigAdapter(
                    source_application_settings=self.settings_resolver,
                    workflow_backend=config_backend_factory,
                ),
            )
        except ImportError:
            self.strategy = strategy or CLIStarter()

    def initialize(self) -> None:
        """Initialize anything that needs to done prior to running."""
        self.strategy.config_files_locator = StandardConfigFileLocator(
            self.application_config_directory_name
        )
        self.strategy.set_application_name(self.application_name)
        self.strategy.startup_tasks = self.startup_tasks
        self.strategy.initialize()

    def run(self, app=None) -> int:
        """Run Speedwagon."""
        self.strategy.set_application_name(self.application_name)
        config_backend = functools.partial(
            default_backend_factory,
            config_directory_name=self.application_config_directory_name,
        )

        self.strategy.set_workflow_config_backend_factory(config_backend)
        if app:
            try:
                # Avoid circular imports!
                # pylint: disable=import-outside-toplevel
                from speedwagon.frontend.qtwidgets.gui_startup import (
                    AbsGuiStarter,
                )

                if isinstance(self.strategy, AbsGuiStarter):
                    return self.strategy.start_gui(app)
            except ImportError:
                pass
        return self.strategy.run()


class SubCommand(abc.ABC):
    def __init__(self, args: argparse.Namespace, config_prefix: str) -> None:
        super().__init__()
        self.args = args
        self.global_settings: Optional[SettingsData] = None
        self.config_prefix = config_prefix

    @abc.abstractmethod
    def run(self) -> None:
        """Run the command."""


class InfoCommand(SubCommand):
    """Info command for speedwagon.

    .. versionadded:: 0.4.0
        speedwagon info command added for quering information about speedwagon.
    """

    def __init__(
        self,
        args: argparse.Namespace,
        config_dir: str = DEFAULT_CONFIG_DIRECTORY_NAME
    ) -> None:
        super().__init__(args, config_dir)
        self.report_builder_strategy: Callable[[], str] = lambda: (
            speedwagon.info.system_report(
                speedwagon.info.SystemInfo(),
                report_format=self.args.report_format
            )
        )
        self.exit_strategy: Callable[[int], None] = sys.exit

    def run(self) -> None:
        """Build a system info report and write it to stdout."""
        report = self.build_report()
        try:
            logger.info(report)
            sys.stdout.flush()
        except BrokenPipeError:
            print("Broken pipe")
        finally:
            self.exit_strategy(0)

    def build_report(self) -> str:
        """Build a system info report as a string.

        Use self.report_builder_strategy() to build a system info report.
        """
        return self.report_builder_strategy()


def get_gui_json_strategy() -> AbsStarter:
    # Avoid circular imports! pylint: disable=import-outside-toplevel
    from speedwagon import frontend

    try:
        return frontend.qtwidgets.gui_startup.SingleWorkflowJSON(app=None)
    except AttributeError as error:
        raise ImportError("GUI strategy not available") from error


def get_cli_json_strategy() -> AbsStarter:
    return SingleWorkflowJSON()


JSON_STRATEGIES_TRY_ORDER: List[Callable[[], AbsStarter]] = [
    get_gui_json_strategy,
    get_cli_json_strategy
]


def get_best_json_strategy(
    strategy_order: Optional[List[Callable[[], AbsStarter]]] = None
) -> AbsStarter:
    order: List[Callable[[], AbsStarter]] =\
        strategy_order if strategy_order is not None \
        else JSON_STRATEGIES_TRY_ORDER

    for json_strategy in order:
        try:
            return json_strategy()
        except ImportError:
            continue
    raise ImportError("No json strategy not available")


class RunCommand(SubCommand):
    create_app_launcher = ApplicationLauncher

    def __init__(
        self,
        args: argparse.Namespace,
        config_prefix: str = DEFAULT_CONFIG_DIRECTORY_NAME
    ) -> None:
        super().__init__(args, config_prefix)
        self.default_json_strategy = get_best_json_strategy

    def json_startup(
        self,
        startup_strategy: Union[
            SingleWorkflowJSON,
            speedwagon.frontend.qtwidgets.gui_startup.SingleWorkflowJSON,
            None
        ] = None
    ) -> None:
        startup_strategy =\
            cast(
                SingleWorkflowJSON,
                (startup_strategy or self.default_json_strategy())
            )

        startup_strategy.global_settings = self.global_settings
        startup_strategy.config =\
            speedwagon.config.StandardConfig(self.config_prefix)
        config_file_locator = StandardConfigFileLocator(
            config_directory_prefix=self.config_prefix
        )
        try:
            default_yaml_file_name =\
                speedwagon.config.workflow.WORKFLOWS_SETTINGS_YML_FILE_NAME
            startup_strategy.get_workflow_options_strategy = (
                lambda workflow_name: (
                    speedwagon.config.workflow.get_workflow_options(
                        os.path.join(
                            config_file_locator.get_app_data_dir(),
                            default_yaml_file_name,
                        ),
                        workflow_name,
                    )
                )
            )

            startup_strategy.get_plugin_data_strategy = (
                lambda: speedwagon.config.plugins.read_settings_data_plugins(
                    speedwagon.utils.read_file(
                        config_file_locator.get_config_file()
                    )
                )
            )

            startup_strategy.load(self.args.json)
            self._run_strategy(startup_strategy)
        except WorkflowLoadFailure as e:
            message = [f"Failed to load json. {e}",
                       "Available workflows are:"]
            for workflow in startup_strategy.available_workflows:
                message.append(f"- \"{workflow}\"")
            logger.error("\n".join(message))
            if self.args.debug:
                traceback.print_exc()

    @staticmethod
    def _run_strategy(startup_strategy: AbsStarter) -> None:
        app_launcher = RunCommand.create_app_launcher(
            strategy=startup_strategy
        )

        app = ApplicationLauncher()
        app.initialize()
        sys.exit(app_launcher.run())

    def run(self) -> None:
        if "json" in self.args and self.args.json:
            self.json_startup()
        else:
            print(f"Invalid {self.args}")


def get_global_options_resolution_order(
    config_file_strategy: Callable[
        [], str
    ] = lambda: speedwagon.config.StandardConfigFileLocator(
        config_directory_prefix=DEFAULT_CONFIG_DIRECTORY_NAME
    ).get_config_file(),
) -> List[speedwagon.config.config.AbsSetting]:

    resolution_order: List[speedwagon.config.config.AbsSetting] = [
        speedwagon.config.config.DefaultsSetter(),
    ]
    config_file = config_file_strategy()
    if os.path.exists(config_file):
        resolution_order.append(
            speedwagon.config.config.ConfigFileSetter(config_file)
        )
    else:
        logger.warning("no config file found")
    resolution_order.append(speedwagon.config.config.CliArgsSetter())
    return resolution_order


def get_global_options(
    resolution_order: Optional[
        List[speedwagon.config.config.AbsSetting]
    ] = None
) -> Dict[str, Any]:
    resolution_order = (
        resolution_order or
        get_global_options_resolution_order()
    )

    loader = speedwagon.config.config.MixedConfigLoader()
    loader.resolution_strategy_order = resolution_order
    return loader.get_settings().get("GLOBAL", {})


def run_command(
    command_name: str,
    args: argparse.Namespace,
    command: Optional[Type[SubCommand]] = None,
    config_dir: Optional[str] = None
) -> None:
    commands: Dict[str, Type[SubCommand]] = {
        "run": RunCommand, "info": InfoCommand
    }
    command = command or commands.get(command_name)

    if command is None:
        raise ValueError(f"Unknown command {command_name}")

    new_command = command(args, config_dir or DEFAULT_CONFIG_DIRECTORY_NAME)

    def use_user_config_dir_if_available():
        return speedwagon.config.StandardConfigFileLocator(
            config_directory_prefix=config_dir or DEFAULT_CONFIG_DIRECTORY_NAME
        ).get_config_file()
    resolution_order =\
        get_global_options_resolution_order(use_user_config_dir_if_available)
    new_command.global_settings = get_global_options(resolution_order)
    new_command.run()


class AbsStarter(metaclass=abc.ABCMeta):
    # config_files_locator: AbsSettingLocator
    startup_tasks: Sequence[
        Union[
            AbsSystemTask,
            Callable[[AbsConfigSettings, SettingsLocations], None],
        ]
    ]

    @property
    def config_files_locator(self):
        warnings.warn(
            "config_files_locator should be avoided."
            "Try to move to config management object",
            Warning,
            stacklevel=2,
        )
        return self._config_files_locator

    @config_files_locator.setter
    def config_files_locator(self, value) -> None:
        self._config_files_locator = value

    @property
    def available_workflows(self):
        return self.locate_available_workflows()

    @abc.abstractmethod
    def locate_available_workflows(
        self
    ) -> Dict[str, Type[speedwagon.job.Workflow]]:
        """Locate available workflows."""

    def set_application_name(self, name: str) -> None:  # noqa: B027
        """Set the application name if environment supports changing name.

        Defaults to no-op.

        This is useful for GUI applications such as ones that based on Qt.
        """

    def set_workflow_config_backend_factory(  # noqa: B027
        self, factory: Callable[[speedwagon.job.Workflow], AbsWorkflowBackend]
    ) -> None:
        """Set the workflow config backend factory.

        Defaults to no-op.

        Args:
            factory: Factory for creating workflow config backend.
        """

    @abc.abstractmethod
    def run(self) -> int:
        pass

    def initialize(self) -> None:  # noqa: B027
        """Initialize startup routine.

        By default, this is a no-op
        """


def default_config_strategy(config_files_locator):
    config_name = os.path.split(config_files_locator.get_app_data_dir())[
        -1
    ]
    return speedwagon.config.StandardConfig(config_name)


def default_get_plugin_data_strategy():
    config_files_locator = StandardConfigFileLocator(
        config_directory_prefix=DEFAULT_CONFIG_DIRECTORY_NAME
    )
    speedwagon.config.plugins.read_settings_data_plugins(
        speedwagon.utils.read_file(config_files_locator.get_config_file())
    )


def default_get_workflow_options_strategy(
    workflow_name,
    config_files_locator: Optional[AbsSettingLocator] = None
) -> Dict[str, Any]:

    config_files_locator = config_files_locator or StandardConfigFileLocator(
        config_directory_prefix=DEFAULT_CONFIG_DIRECTORY_NAME
    )
    return speedwagon.config.workflow.get_workflow_options(
        os.path.join(
            config_files_locator.get_app_data_dir(),
            speedwagon.config.workflow.WORKFLOWS_SETTINGS_YML_FILE_NAME,
        ),
        workflow_name,
    )


class SingleWorkflowJSON(AbsStarter):
    def __init__(self) -> None:
        super().__init__()
        self.config: Optional[AbsConfigSettings] = None
        self.options: Optional[Dict[str, Any]] = None
        self.global_settings: Optional[SettingsData] = None
        self.workflow: Optional[speedwagon.job.Workflow] = None
        self.get_workflow_options_strategy: Callable[[str], Dict[str, Any]] =\
            default_get_workflow_options_strategy
        self.get_plugin_data_strategy = default_get_plugin_data_strategy

    def run(self) -> int:
        if self.workflow:
            workflow_options = self.get_workflow_options_strategy(
                self.workflow.name or ""
            )
            workflow_logger = logging.getLogger()
            workflow_logger.setLevel(logging.INFO)
            handler = logging.StreamHandler(stream=sys.stdout)
            handler.setLevel(
                logging.DEBUG if (
                    self.global_settings and
                    self.global_settings.get('debug', False)
                )
                else logging.INFO
            )
            workflow_logger.addHandler(handler)
            speedwagon.runner_strategies.simple_api_run_workflow2(
                self.workflow,
                speedwagon.runner_strategies.JobSubmitConfig(
                    workflow=workflow_options,
                    job=self.options or {},
                    global_settings=self.global_settings or {}
                ),
                workflow_logger,
            )
        return 0

    def load(self, json_file: str) -> None:
        """Load the information from the json.

        Args:
            json_file: json file

        """
        loaded_data = parse_json_file(json_file)
        self.options = loaded_data["Configuration"]
        self._set_workflow(loaded_data["Workflow"])

    def locate_available_workflows(
        self
    ) -> Dict[str, Type[speedwagon.job.Workflow]]:
        if self.config is None:
            logger.warning(
                "running locate_available_workflows without config loaded "
                "produces no workflows"
            )
            return {}
        return locate_workflows_with_reporting(
            self.config.application_settings(),
        )

    def _set_workflow(self, workflow_name: str) -> None:
        if self.config is None:
            global_settings = {}
        else:
            global_settings = self.config.application_settings().get(
                    "GLOBAL", {}
                )
        self.workflow = self.available_workflows[workflow_name](
            global_settings=global_settings
        )


class CLIStarter(AbsStarter):
    def run(self) -> int:
        print("Try running --help for info on the commands")
        return 0

    def locate_available_workflows(
        self
    ) -> Dict[str, Type[speedwagon.job.Workflow]]:
        return speedwagon.job.available_workflows()


class StartupTaskBuilder:
    def __init__(
        self,
        config_backend: AbsConfigSettings,
        config_file_locator: AbsSettingLocator,
    ) -> None:
        self._tasks: List[AbsSystemTask] = []
        self.config_backend = config_backend
        self.config_file_locator = config_file_locator

    def add_task(self, task: AbsSystemTask) -> None:
        self._tasks.append(task)

    def add_callable(
        self,
        task: Callable[[AbsConfigSettings, SettingsLocations], None],
    ) -> None:
        self._tasks.append(CallbackSystemTask(task, "Startup Task"))

    def iter_tasks(self) -> Iterable[AbsSystemTask]:
        for task in self._tasks:
            task.set_config_backend(self.config_backend)
            task.set_config_file_locator(self.config_file_locator)
            yield task


def configure_startup_task(
    task: Union[
        AbsSystemTask,
        Callable[[AbsConfigSettings, SettingsLocations], None],
    ],
    config_backend: AbsConfigSettings,
    config_file_locator: AbsSettingLocator,
) -> AbsSystemTask:
    if not isinstance(task, AbsSystemTask):
        task = CallbackSystemTask(task, "Startup Task")
    task.set_config_backend(config_backend)
    task.set_config_file_locator(config_file_locator)
    return task


def get_startup_tasks(
    config_backend: AbsConfigSettings,
    config_file_locator: AbsSettingLocator,
    user_tasks: Optional[
        Sequence[
            Union[
                AbsSystemTask,
                Callable[[AbsConfigSettings, SettingsLocations], None],
            ]
        ]
    ] = None,
) -> Iterable[AbsSystemTask]:
    task_builder: TaskBuilder[
        Union[
            AbsSystemTask,
            Callable[[AbsConfigSettings, SettingsLocations], None],
        ],
        AbsSystemTask,
    ] = TaskBuilder(
        functools.partial(
            configure_startup_task,
            config_backend=config_backend,
            config_file_locator=config_file_locator,
        )
    )

    for task in user_tasks or []:
        task_builder.add(task)

    def get_whitelist_strategy():
        config_file = config_file_locator.get_config_file()
        logger.debug(
            "Using config file to load whitelisted plugins: %s",
            config_file
        )
        data = read_file(config_file)
        return get_whitelisted_plugins_from_config_data(
            read_settings_data_plugins(data)
        )

    plugin_manager_strategy = functools.partial(
        speedwagon.plugins.register_whitelisted_plugins,
        get_whitelist_strategy=get_whitelist_strategy,
    )
    plugin_manager = plugins.get_plugin_manager(plugin_manager_strategy)

    for plugin_tasks in plugin_manager.hook.registered_initialization_tasks():
        for task in plugin_tasks:
            task_builder.add(task)

    return list(task_builder.iter_tasks())


def locate_workflows_with_reporting(settings, error_loggers=None):
    workflow_load_config = (
        speedwagon.workflow.LoadWorkflowsUsingPluginsConfig()
    )
    workflow_load_config.plugin_config_data =\
        speedwagon.config.plugins.parse_plugin_data(settings)

    workflow_load_config.workflow_validation_checkers.append(
        lambda workflow: speedwagon.workflow.locate_errors_in_workflow(
            workflow, settings
        )
    )

    loading_workflows_stream = io.StringIO()
    with contextlib.redirect_stderr(loading_workflows_stream):
        return speedwagon.workflow.load_workflows(
            workflow_load_config, error_loggers=error_loggers or []
        )


def main(argv: Optional[List[str]] = None) -> None:
    """Launch main entry point."""
    argv = argv or sys.argv
    if "tab-editor" in argv:
        speedwagon.frontend.qtwidgets.gui_startup.standalone_tab_editor()
        return
    parser = speedwagon.config.config.CliArgsSetter.get_arg_parser()
    args = parser.parse_args(argv[1:])

    if args.command is not None:
        run_command(command_name=args.command, args=args)
        return

    app = ApplicationLauncher()
    app.initialize()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
