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
import io
import json
import sys
import typing
from typing import Dict, Iterator, Tuple, List, cast, Type, TYPE_CHECKING, \
    Optional
import yaml

import speedwagon
import speedwagon.config
import speedwagon.exceptions

from speedwagon import job


try:
    from typing import Final
except ImportError:  # pragma: no cover
    from typing_extensions import Final  # type: ignore

if TYPE_CHECKING:
    import speedwagon.frontend.qtwidgets.gui_startup


__all__ = [
    "ApplicationLauncher",
    "FileFormatError",
]

CONFIG_INI_FILE_NAME: Final[str] = "config.ini"
TABS_YML_FILE_NAME:  Final[str] = "tabs.yml"


class FileFormatError(Exception):
    """Exception is thrown when Something wrong with the contents of a file."""


def parse_args() -> argparse.ArgumentParser:
    """Parse command line arguments."""
    return speedwagon.config.CliArgsSetter.get_arg_parser()


class CustomTabsFileReader:
    """Reads the tab file data."""

    def __init__(
            self,
            all_workflows: Dict[str, Type[speedwagon.job.Workflow]]
    ) -> None:
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
                        print(
                            f"Error loading tab '{tab_name}'. "
                            f"Reason: {tab_error}",
                            file=sys.stderr
                        )
                        continue

        except FileNotFoundError as error:
            print(
                f"Custom tabs file not found. Reason: {error}",
                file=sys.stderr
            )
        except AttributeError as error:
            print(
                f"Custom tabs file failed to load. Reason: {error}",
                file=sys.stderr
            )

        except yaml.YAMLError as error:
            print(
                f"{yaml_file} file failed to load. Reason: {error}",
                file=sys.stderr
            )


def get_custom_tabs(
        all_workflows: Dict[str, Type[speedwagon.job.Workflow]],
        yaml_file: str
) -> Iterator[Tuple[str, dict]]:
    """Load custom tab yaml file."""
    getter = CustomTabsFileReader(all_workflows)
    yield from getter.load_custom_tabs(yaml_file)


class ApplicationLauncher:
    """Application launcher.

    .. versionadded:: 0.2.0
       Added ApplicationLauncher for launching speedwagon in different ways.
    """

    def __init__(self, strategy: Optional[AbsStarter] = None) -> None:
        """Strategy pattern for loading speedwagon in different ways.

        Args:
            strategy: Starter strategy class.
        """
        super().__init__()
        try:
            from speedwagon.frontend.qtwidgets.gui_startup import \
                StartQtThreaded

            self.strategy = strategy or StartQtThreaded()
        except ImportError:
            self.strategy = strategy or CLIStarter()

    def initialize(self) -> None:
        """Initialize anything that needs to done prior to running."""
        self.strategy.initialize()

    def run(self, app=None) -> int:
        """Run Speedwagon."""
        if app:
            try:
                from speedwagon.frontend.qtwidgets.gui_startup \
                    import AbsGuiStarter
                if isinstance(self.strategy, AbsGuiStarter):
                    return self.strategy.start_gui(app)
            except ImportError:
                pass
        return self.strategy.run()


class SubCommand(abc.ABC):
    def __init__(self, args) -> None:
        super().__init__()
        self.args = args
        self.global_settings = None

    @abc.abstractmethod
    def run(self):
        """Run the command."""


class RunCommand(SubCommand):
    def get_gui_strategy(
            self
    ) -> speedwagon.frontend.qtwidgets.gui_startup.SingleWorkflowJSON:
        from speedwagon import frontend
        return frontend.qtwidgets.gui_startup.SingleWorkflowJSON(app=None)

    def json_startup(self) -> None:
        try:
            startup_strategy = self.get_gui_strategy()
        except ImportError:
            startup_strategy = SingleWorkflowJSON()

        startup_strategy.global_settings = self.global_settings
        startup_strategy.load(self.args.json)
        self._run_strategy(startup_strategy)

    @staticmethod
    def _run_strategy(startup_strategy):
        app_launcher = \
            speedwagon.startup.ApplicationLauncher(strategy=startup_strategy)

        app = ApplicationLauncher()
        app.initialize()
        sys.exit(app_launcher.run())

    def run(self):
        if "json" in self.args:
            self.json_startup()
        else:
            print(f"Invalid {self.args}")


def get_global_options():
    config_locator = speedwagon.config.StandardConfigFileLocator()
    return speedwagon.config.ConfigLoader(
        config_locator.get_config_file()
    ).get_settings()


def run_command(
        command_name: str,
        args: argparse.Namespace,
        command=None
) -> None:
    commands = {
        "run": RunCommand
    }
    command = command or commands.get(command_name)

    if command is None:
        raise ValueError(f"Unknown command {command_name}")

    new_command = command(args)
    new_command.global_settings = get_global_options()
    new_command.run()


class AbsStarter(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def run(self) -> int:
        pass

    def initialize(self) -> None:
        """Initialize startup routine."""


class SingleWorkflowJSON(AbsStarter):

    def __init__(self) -> None:
        super().__init__()
        self.options: typing.Optional[typing.Dict[str, typing.Any]] = None
        self.global_settings = None
        self.workflow = None

    def run(self) -> int:
        speedwagon.simple_api_run_workflow(
            self.workflow,
            self.options,
        )
        return 0

    def load(self, file_pointer: io.TextIOBase) -> None:
        """Load the information from the json.

        Args:
            file_pointer: File pointer to json file

        """
        loaded_data = json.load(file_pointer)
        self.options = loaded_data['Configuration']
        self._set_workflow(loaded_data['Workflow'])

    def _set_workflow(self, workflow_name: str) -> None:
        available_workflows = speedwagon.job.available_workflows()
        self.workflow = available_workflows[workflow_name](
            global_settings=self.global_settings or {}
        )


class CLIStarter(AbsStarter):

    def run(self) -> int:
        print("Try running --help for info on the commands")
        return 0


def main(argv: Optional[List[str]] = None) -> None:
    """Launch main entry point."""
    argv = argv or sys.argv
    if "tab-editor" in argv:
        speedwagon.frontend.qtwidgets.gui_startup.standalone_tab_editor()
        return
    parser = speedwagon.config.CliArgsSetter.get_arg_parser()
    args = parser.parse_args(argv[1:])

    if args.command is not None:
        run_command(command_name=args.command, args=args)
        return

    app = ApplicationLauncher()
    app.initialize()
    sys.exit(app.run())


if __name__ == '__main__':
    main()
