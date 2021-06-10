"""Define how Speedwagon starts up on the current system

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
import yaml
from PyQt5 import QtWidgets, QtGui, QtCore  # type: ignore

import speedwagon
import speedwagon.config
import speedwagon.models
import speedwagon.tabs
from speedwagon import worker, job
from speedwagon.dialog.settings import TabEditor
from speedwagon.gui import SplashScreenLogHandler, MainWindow
from speedwagon.tabs import extract_tab_information
import pathlib
try:  # pragma: no cover
    from importlib import metadata
    import importlib.resources as resources  # type: ignore
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore
    import importlib_resources as resources  # type: ignore


class FileFormatError(Exception):
    pass


def parse_args() -> argparse.ArgumentParser:
    return CliArgsSetter.get_arg_parser()


class AbsSetting(metaclass=abc.ABCMeta):

    @property
    @staticmethod
    @abc.abstractmethod
    def FRIENDLY_NAME():
        return NotImplementedError

    def update(self, settings=None) -> Dict["str", Union[str, bool]]:
        if settings is None:
            return dict()
        else:
            return settings


class DefaultsSetter(AbsSetting):
    FRIENDLY_NAME = "Setting defaults"

    def update(self, settings=None) -> Dict["str", Union[str, bool]]:
        new_settings = super().update(settings)
        new_settings["debug"] = False
        return new_settings


class CliArgsSetter(AbsSetting):

    FRIENDLY_NAME = "Command line arguments setting"

    def update(self, settings=None) -> Dict["str", Union[str, bool]]:
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
        self.config_file = config_file

    def update(self, settings=None) -> Dict["str", Union[str, bool]]:
        new_settings = super().update(settings)
        with speedwagon.config.ConfigManager(self.config_file) as cfg:
            new_settings.update(cfg.global_settings.items())
        return new_settings


def get_selection(all_workflows):
    new_workflow_set = dict()
    for k, v in all_workflows.items():
        if "Verify" in k:
            new_workflow_set[k] = v
    return new_workflow_set


class CustomTabsGetter:
    def get(
            self,
            all_workflows: Dict[str, Type[speedwagon.Workflow]],
            yaml_file: str
    ) -> Iterator[Tuple[str, dict]]:
        try:
            with open(yaml_file) as f:
                tabs_config_data = yaml.load(f.read(), Loader=yaml.SafeLoader)
            if not isinstance(tabs_config_data, dict):
                raise FileFormatError("Failed to parse file")

            if tabs_config_data:
                tabs_config_data = cast(Dict[str, List[str]], tabs_config_data)
                for tab_name in tabs_config_data:

                    try:
                        new_tab_items = dict()
                        new_tab = tabs_config_data.get(tab_name)
                        if new_tab is not None:
                            for item_name in new_tab:
                                try:
                                    workflow = all_workflows[item_name]
                                    if workflow.active is False:
                                        print("workflow not active")
                                    new_tab_items[item_name] = workflow

                                except LookupError:
                                    print(
                                        f"Unable to load '{item_name}' in "
                                        f"tab {tab_name}", file=sys.stderr)
                            yield tab_name, new_tab_items
                    except TypeError as e:
                        print("Error loading tab '{}'. "
                              "Reason: {}".format(tab_name, e), file=sys.stderr)
                        continue

        except FileNotFoundError as e:
            print("Custom tabs file not found. "
                  "Reason: {}".format(e), file=sys.stderr)
        except AttributeError as e:
            print("Custom tabs file failed to load. "
                  "Reason: {}".format(e), file=sys.stderr)

        except yaml.YAMLError as e:
            print("{} file failed to load. "
                  "Reason: {}".format(yaml_file, e), file=sys.stderr)


def get_custom_tabs(
        all_workflows: Dict[str, Type[speedwagon.Workflow]],
        yaml_file: str
) -> Iterator[Tuple[str, dict]]:
    getter = CustomTabsGetter()
    yield from getter.get(all_workflows, yaml_file)


class AbsStarter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def run(self) -> int:
        pass

    @abc.abstractmethod
    def initialize(self) -> None:
        pass


class StartupDefault(AbsStarter):
    def __init__(self, app: QtWidgets.QApplication = None) -> None:
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

            self._logger.info(f"{app_title} {app_version}")

            QtWidgets.QApplication.processEvents()

            # ==================================================
            # Load configurations
            self._logger.debug("Applying settings to Speedwagon")

            work_manager.user_settings = self.platform_settings
            work_manager.configuration_file = self.config_file

            # ==================================================
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

                        windows.add_tab(tab_name, collections.OrderedDict(
                            sorted(extra_tab.items())))
                except FileFormatError as e:
                    self._logger.warning(
                        "Unable to load custom tabs from {}. "
                        "Reason: {}".format(self.tabs_file, e))

            # All Workflows tab

            self._logger.debug("Loading Tab All")
            windows.add_tab("All", collections.OrderedDict(
                sorted(all_workflows.items())))

            workflow_errors_msg = loading_workflows_stream.getvalue().strip()

            if workflow_errors_msg:
                for line in workflow_errors_msg.split("\n"):
                    self._logger.warning(line)

            # ==================================================
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

    def read_settings_file(self, settings_file: str) -> None:
        with speedwagon.config.ConfigManager(settings_file) as f:
            self.platform_settings._data.update(f.global_settings)

    def set_app_display_metadata(self) -> None:
        with resources.open_binary(speedwagon.__name__, "favicon.ico") as icon:
            self.app.setWindowIcon(QtGui.QIcon(icon.name))
        try:
            self.app.setApplicationVersion(metadata.version(__package__))
        except metadata.PackageNotFoundError:
            pass
        self.app.setApplicationDisplayName(f"{speedwagon.__name__.title()}")
        QtWidgets.QApplication.processEvents()

    def resolve_settings(self) -> None:
        resolution_order: List[AbsSetting] = [
            DefaultsSetter(),
            ConfigFileSetter(self.config_file),
            CliArgsSetter(),
        ]
        self.read_settings_file(self.config_file)
        for settings_strategy in resolution_order:

            self._logger.debug("Loading settings from {}".format(
                settings_strategy.FRIENDLY_NAME))

            try:
                self.startup_settings = settings_strategy.update(
                    self.startup_settings)
            except ValueError as e:
                if isinstance(settings_strategy, ConfigFileSetter):
                    self._logger.warning(
                        "{} contains an invalid setting. Details: {} ".format(
                            self.config_file, e)
                    )

                else:
                    self._logger.warning("{} is an invalid setting".format(e))
        try:
            self._debug = cast(bool, self.startup_settings['debug'])
        except KeyError:
            self._logger.warning(
                "Unable to find a key for debug mode. Setting false")

            self._debug = False
        except ValueError as e:
            self._logger.warning(
                "{} is an invalid setting for debug mode."
                "Setting false".format(e))

            self._debug = False

    def ensure_settings_files(self) -> None:
        if not os.path.exists(self.config_file):
            speedwagon.config.generate_default(self.config_file)

            self._logger.debug(
                "No config file found. Generated {}".format(self.config_file))
        else:
            self._logger.debug(
                "Found existing config file {}".format(self.config_file))

        if not os.path.exists(self.tabs_file):
            pathlib.Path(self.tabs_file).touch()

            self._logger.debug(
                "No tabs.yml file found. Generated {}".format(self.tabs_file))
        else:
            self._logger.debug(
                "Found existing tabs file {}".format(self.tabs_file))

        if self.user_data_dir and not os.path.exists(self.user_data_dir):
            os.makedirs(self.user_data_dir)
            self._logger.debug("Created directory {}".format(
                self.user_data_dir))

        else:
            self._logger.debug(
                "Found existing user data directory {}".format(
                    self.user_data_dir))

        if self.app_data_dir is not None and \
                not os.path.exists(self.app_data_dir):

            os.makedirs(self.app_data_dir)
            self._logger.debug("Created {}".format(self.app_data_dir))
        else:
            self._logger.debug(
                "Found existing app data "
                "directory {}".format(self.app_data_dir))


class TabsEditorApp(QtWidgets.QDialog):
    """Dialog box for editing tabs.yml file"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Speedwagon Tabs Editor")
        layout = QtWidgets.QVBoxLayout()
        self.editor = TabEditor()
        layout.addWidget(self.editor)
        self.dialogButtonBox = QtWidgets.QDialogButtonBox(self)
        layout.addWidget(self.dialogButtonBox)

        self.dialogButtonBox.setStandardButtons(
            cast(
                QtWidgets.QDialogButtonBox.StandardButtons,
                QtWidgets.QDialogButtonBox.Cancel |
                QtWidgets.QDialogButtonBox.Ok
            )
        )

        self.setLayout(layout)

        self.dialogButtonBox.accepted.connect(self.on_okay)
        self.dialogButtonBox.rejected.connect(self.on_cancel)
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
        self.editor.tabs_file = filename

    @property
    def tabs_file(self) -> Optional[str]:
        return self.editor.tabs_file

    @tabs_file.setter
    def tabs_file(self, value: str) -> None:
        self.editor.tabs_file = value


def standalone_tab_editor(app: QtWidgets.QApplication = None) -> None:
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


def main(argv: List[str] = None) -> None:
    argv = argv or sys.argv
    if "tab-editor" in argv:
        standalone_tab_editor()
        return
    app = StartupDefault()
    app.initialize()
    sys.exit(app.run())


if __name__ == '__main__':
    main()
