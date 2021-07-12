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
import logging
import os
import sys
from typing import Dict, Union, Iterator, Tuple, List, cast, Optional, Type
import pathlib
import yaml
from PyQt5 import QtWidgets, QtGui, QtCore  # type: ignore

import speedwagon
import speedwagon.config
import speedwagon.models
import speedwagon.tabs
from speedwagon import worker, job, runner_strategies
from speedwagon.dialog.settings import TabEditor
from speedwagon.gui import SplashScreenLogHandler, MainWindow
from speedwagon.tabs import extract_tab_information


try:  # pragma: no cover
    from importlib import metadata
    import importlib.resources as resources  # type: ignore
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore
    import importlib_resources as resources  # type: ignore


class FileFormatError(Exception):
    pass


def parse_args() -> argparse.ArgumentParser:
    """Parse command line arguments."""
    return CliArgsSetter.get_arg_parser()


class AbsSetting(metaclass=abc.ABCMeta):

    @property
    @staticmethod
    @abc.abstractmethod
    def FRIENDLY_NAME():
        return NotImplementedError

    def update(
            self,
            settings: Dict[str, Union[str, bool]] = None
    ) -> Dict["str", Union[str, bool]]:
        if settings is None:
            return dict()
        else:
            return settings


class DefaultsSetter(AbsSetting):
    FRIENDLY_NAME = "Setting defaults"

    def update(
            self,
            settings: Dict[str, Union[str, bool]] = None
    ) -> Dict["str", Union[str, bool]]:
        new_settings = super().update(settings)
        new_settings["debug"] = False
        return new_settings


class CliArgsSetter(AbsSetting):

    FRIENDLY_NAME = "Command line arguments setting"

    def update(
            self,
            settings: Dict[str, Union[str, bool]] = None
    ) -> Dict["str", Union[str, bool]]:
        new_settings = super().update(settings)

        args = self._parse_args()
        if args.start_tab is not None:
            new_settings["starting-tab"] = args.start_tab

        if args.debug is True:
            new_settings["debug"] = args.debug

        return new_settings

    @staticmethod
    def get_arg_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        try:
            current_version = metadata.version(__package__)
        except metadata.PackageNotFoundError:
            current_version = "dev"
        parser.add_argument(
            '--version',
            action='version',
            version=current_version
        )

        parser.add_argument(
            "--starting-tab",
            dest="start_tab",
            help="Which tab to have open on start"
        )

        parser.add_argument(
            "--debug",
            dest="debug",
            action='store_true',
            help="Run with debug mode"
        )
        return parser

    @staticmethod
    def _parse_args() -> argparse.Namespace:
        parser = CliArgsSetter.get_arg_parser()
        return parser.parse_args()


class ConfigFileSetter(AbsSetting):
    FRIENDLY_NAME = "Config file settings"

    def __init__(self, config_file: str):
        """Create a new config file setter."""
        self.config_file = config_file

    def update(
            self,
            settings: Dict[str, Union[str, bool]] = None
    ) -> Dict["str", Union[str, bool]]:
        """Update setting configuration."""
        new_settings = super().update(settings)
        with speedwagon.config.ConfigManager(self.config_file) as cfg:
            new_settings.update(cfg.global_settings.items())
        return new_settings


def get_selection(all_workflows):
    """Get current selection of workflows."""
    new_workflow_set = dict()
    for k, v in all_workflows.items():
        if "Verify" in k:
            new_workflow_set[k] = v
    return new_workflow_set


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
        with open(yaml_file) as file_handler:
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
    @abc.abstractmethod
    def run(self) -> int:
        pass

    @abc.abstractmethod
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
            self.platform_settings.get_app_data_directory(), "config.ini")

        self.tabs_file = os.path.join(
            self.platform_settings.get_app_data_directory(), "tabs.yml")

        # Make sure required directories exists
        self.user_data_dir = self.platform_settings.get("user_data_directory")
        self.startup_settings: Dict[str, Union[str, bool]] = dict()
        self._debug = False

        self.app_data_dir = self.platform_settings.get("app_data_directory")
        self.app = app or QtWidgets.QApplication(sys.argv)

    def initialize(self) -> None:
        self.ensure_settings_files()
        self.resolve_settings()

    def run(self) -> int:
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
        splash_message_handler = SplashScreenLogHandler(splash)

        # If debug mode, print the log messages directly on the splash screen
        if self._debug:
            splash_message_handler.setLevel(logging.DEBUG)
        else:
            splash_message_handler.setLevel(logging.INFO)

        splash.show()
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents)

        self.set_app_display_metadata()

        with worker.ToolJobManager() as work_manager:

            work_manager.settings_path = \
                self.platform_settings.get_app_data_directory()

            windows = MainWindow(
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

            self._load_configurations(work_manager)
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

    def _load_configurations(self,
                             work_manager: worker.ToolJobManager) -> None:

        self._logger.debug("Applying settings to Speedwagon")
        work_manager.user_settings = self.platform_settings
        work_manager.configuration_file = self.config_file

    def _load_workflows(self, application: MainWindow) -> None:
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

    def read_settings_file(self, settings_file: str) -> None:
        with speedwagon.config.ConfigManager(settings_file) as config:
            self.platform_settings._data.update(config.global_settings)

    def set_app_display_metadata(self) -> None:
        with resources.open_binary(speedwagon.__name__, "favicon.ico") as icon:
            self.app.setWindowIcon(QtGui.QIcon(icon.name))
        try:
            self.app.setApplicationVersion(metadata.version(__package__))
        except metadata.PackageNotFoundError:
            pass
        self.app.setApplicationDisplayName(f"{speedwagon.__name__.title()}")
        QtWidgets.QApplication.processEvents()

    def resolve_settings(
            self,
            resolution_strategy_order: Optional[List[AbsSetting]] = None
    ) -> None:
        if resolution_strategy_order is None:
            resolution_strategy_order = [
                DefaultsSetter(),
                ConfigFileSetter(self.config_file),
                CliArgsSetter(),
            ]
        self.read_settings_file(self.config_file)
        for settings_strategy in resolution_strategy_order:

            self._logger.debug("Loading settings from %s",
                               settings_strategy.FRIENDLY_NAME)

            try:
                self.startup_settings = settings_strategy.update(
                    self.startup_settings)
            except ValueError as error:
                if isinstance(settings_strategy, ConfigFileSetter):
                    self._logger.warning(
                        "%s contains an invalid setting. Details: %s",
                        self.config_file,
                        error
                    )

                else:
                    self._logger.warning("%s is an invalid setting",
                                         error)
        try:
            self._debug = cast(bool, self.startup_settings['debug'])
        except KeyError:
            self._logger.warning(
                "Unable to find a key for debug mode. Setting false")

            self._debug = False
        except ValueError as error:
            self._logger.warning(
                "%s is an invalid setting for debug mode."
                "Setting false",
                error)

            self._debug = False

    def ensure_settings_files(self) -> None:
        if not os.path.exists(self.config_file):
            speedwagon.config.generate_default(self.config_file)

            self._logger.debug(
                "No config file found. Generated %s",
                self.config_file
            )
        else:
            self._logger.debug(
                "Found existing config file %s",
                self.config_file
            )

        if not os.path.exists(self.tabs_file):
            pathlib.Path(self.tabs_file).touch()

            self._logger.debug(
                "No tabs.yml file found. Generated %s", self.tabs_file)
        else:
            self._logger.debug(
                "Found existing tabs file %s", self.tabs_file)

        if self.user_data_dir and not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)
            self._logger.debug("Created directory %s", self.user_data_dir)

        else:
            self._logger.debug(
                "Found existing user data directory %s",
                self.user_data_dir
            )

        if self.app_data_dir is not None and \
                not os.path.exists(self.app_data_dir):

            os.makedirs(self.app_data_dir)
            self._logger.debug("Created %s", self.app_data_dir)
        else:
            self._logger.debug(
                "Found existing app data "
                "directory %s",
                self.app_data_dir
            )


class SingleWorkflowLauncher(AbsStarter):
    """Single workflow launcher.

    .. versionadded:: 0.2.0
       Added SingleWorkflowLauncher class for running a single workflow \
            without user interaction. Useful for building new workflows.

    """

    def __init__(self) -> None:
        """Set up window for running a single workflow."""
        super().__init__()
        self.window: Optional[MainWindow] = None
        self._active_workflow: Optional[job.AbsWorkflow] = None
        self.options: Dict[str, Union[str, bool]] = {}

    def run(self) -> int:
        """Run the workflow configured with the options given."""
        if self._active_workflow is None:
            raise AttributeError("Workflow has not been set")

        with worker.ToolJobManager() as work_manager:

            window = MainWindow(
                work_manager=work_manager,
                debug=False)

            window.show()

            runner_strategy = \
                runner_strategies.UsingExternalManagerForAdapter(work_manager)

            self._active_workflow.validate_user_options(**self.options)

            runner_strategy.run(window,
                                self._active_workflow,
                                self.options,
                                window.log_manager)
            window.log_manager.handlers.clear()
        return 0

    def initialize(self) -> None:
        """No initialize is needed."""

    def set_workflow(self, workflow: job.AbsWorkflow):
        """Set the current workflow."""
        self._active_workflow = workflow


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

    tabs_file = os.path.join(settings.get_app_data_directory(), "tabs.yml")
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

            from speedwagon.workflows.workflow_capture_one_to_dl_compound_and_dl import CaptureOneToDlCompoundAndDLWorkflow

        .. testcode::
           :skipif: True

           >>> startup_strategy = SingleWorkflowLauncher()
           >>> startup_strategy.set_workflow(CaptureOneToDlCompoundAndDLWorkflow())
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
        self.strategy = strategy or StartupDefault()

    def initialize(self) -> None:
        """Initialize anything that needs to done prior to running."""
        self.strategy.initialize()

    def run(self) -> int:
        """Run Speedwagon."""
        return self.strategy.run()


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
