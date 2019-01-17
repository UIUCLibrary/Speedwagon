import abc
import argparse
import collections
import contextlib
import io
import logging
import os
import sys
from typing import Dict, Union, Iterator, Tuple
import yaml

import pkg_resources
from PyQt5 import QtWidgets, QtGui, QtCore

import speedwagon
import speedwagon.config
from speedwagon import worker, job
from speedwagon.gui import SplashScreenLogHandler, MainWindow


class FileFormatError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--version', action='version', version=speedwagon.__version__)

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

    return parser.parse_args()


class AbsSetting(metaclass=abc.ABCMeta):

    def update(self, settings=None) -> Dict["str", Union[str, bool]]:
        if settings is None:
            return dict()
        else:
            return settings


class DefaultsSetter(AbsSetting):

    def update(self, settings=None) -> Dict["str", Union[str, bool]]:
        new_settings = super().update(settings)
        new_settings["debug"] = False
        return new_settings


class CliArgsSetter(AbsSetting):

    def update(self, settings=None) -> Dict["str", Union[str, bool]]:
        new_settings = super().update(settings)

        args = self._parse_args()
        if args.start_tab is not None:
            new_settings["starting-tab"] = args.start_tab

        if args.debug is True:
            new_settings["debug"] = args.debug

        return new_settings

    def _parse_args(self):
        parser = argparse.ArgumentParser()

        parser.add_argument(
            '--version', action='version', version=speedwagon.__version__)

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

        return parser.parse_args()


class ConfigFileSetter(AbsSetting):
    def __init__(self, config_file):
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


def get_custom_tabs(all_workflows: dict, yaml_file)->\
        Iterator[Tuple[str, dict]]:

    try:
        with open(yaml_file) as f:
            tabs_config_data = yaml.load(f.read())
        if not isinstance(tabs_config_data, dict):
            raise FileFormatError(f"Failed to parse file")

        if tabs_config_data:
            for tab_name in tabs_config_data:

                try:
                    new_tab_items = dict()

                    for item_name in tabs_config_data.get(tab_name):
                        try:
                            new_tab_items[item_name] = all_workflows[item_name]

                        except LookupError:
                            print("Unable to load '{}' in tab {}.".format(
                                item_name, tab_name), file=sys.stderr)
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


class AbsStarter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def run(self):
        pass


class StartupDefault(AbsStarter):
    def __init__(self):
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
        self.data_dir = self.platform_settings.get("user_data_directory")
        self.startup_settings = dict()
        self._debug = False

        self.app_data_dir = self.platform_settings.get("app_data_directory")
        self.app = QtWidgets.QApplication(sys.argv)

    def run(self):
        self.ensure_settings_files()
        self.resolve_settings()

        # Display a splash screen until the app is loaded
        with pkg_resources.resource_stream(__name__, "logo.png") as logo:

            splash = QtWidgets.QSplashScreen(
                QtGui.QPixmap(logo.name).scaled(400, 400))

        splash.setEnabled(False)
        splash.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint
        )
        splash_message_handler = SplashScreenLogHandler(splash)

        # If debug mode, print the log messages directly on the splash screen
        if self._debug:
            splash_message_handler.setLevel(logging.DEBUG)
        else:
            splash_message_handler.setLevel(logging.INFO)

        splash.show()
        self.app.processEvents()

        self.set_app_display_metadata()

        with worker.ToolJobManager() as work_manager:

            work_manager.settings_path = \
                self.platform_settings.get_app_data_directory()

            windows = MainWindow(work_manager=work_manager,
                                 debug=self.startup_settings['debug'])

            windows.setWindowTitle("")
            self._logger.addHandler(splash_message_handler)

            self._logger.addHandler(windows.log_data_handler)
            self._logger.addHandler(windows.console_log_handler)

            app_title = speedwagon.__name__.title()
            app_version = speedwagon.__version__
            self._logger.info(f"{app_title} {app_version}")

            self.app.processEvents()

            # ==================================================
            # Load configurations
            self._logger.debug("Applying settings to Speedwagon")

            work_manager.user_settings = self.platform_settings
            work_manager.configuration_file = self.config_file

            # ==================================================
            self._logger.debug("Loading Tools")

            loading_job_stream = io.StringIO()

            with contextlib.redirect_stderr(loading_job_stream):
                tools = job.available_tools()
                windows.add_tools(tools)

            tool_error_msgs = loading_job_stream.getvalue().strip()
            if tool_error_msgs:
                for line in tool_error_msgs.split("\n"):
                    self._logger.warning(line)

            # ==================================================
            self._logger.debug("Loading Workflows")
            loading_workflows_stream = io.StringIO()
            with contextlib.redirect_stderr(loading_workflows_stream):
                all_workflows = job.available_workflows()

            # Load every user configured tab
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
                    tab_name=self.startup_settings['starting-tab'])

            # QtCore.QThread.sleep(1)
            splash.finish(windows)

            self._logger.info("Ready")
            self._logger.removeHandler(windows.log_data_handler)
            self._logger.removeHandler(windows.console_log_handler)
            self._logger.removeHandler(splash_message_handler)
            return self.app.exec_()

    def read_settings_file(self, settings_file):
        with speedwagon.config.ConfigManager(settings_file) as f:
            self.platform_settings._data.update(f.global_settings)

    def set_app_display_metadata(self):
        with pkg_resources.resource_stream(__name__, "favicon.ico") as icon:
            self.app.setWindowIcon(QtGui.QIcon(icon.name))

        self.app.setApplicationVersion(f"{speedwagon.__version__}")
        self.app.setApplicationDisplayName(f"{speedwagon.__name__.title()}")
        self.app.processEvents()

    def resolve_settings(self):
        resolution_order = [
            DefaultsSetter(),
            ConfigFileSetter(self.config_file),
            CliArgsSetter(),
        ]
        # self.read_settings_file(self.config_file)
        for settings_strategy in resolution_order:
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
            self._debug = self.startup_settings['debug']
        except KeyError:
            self._logger.warning(
                "Unable to find a key for debug mode. Setting false")

            self._debug = False
        except ValueError as e:
            self._logger.warning(
                "{} is an invalid setting for debug mode."
                "Setting false".format(e))

            self._debug = False

    def ensure_settings_files(self):
        if not os.path.exists(self.config_file):
            speedwagon.config.generate_default(self.config_file)

            self._logger.debug(
                "No config file found. Generated {}".format(self.config_file))

        if not os.path.exists(self.tabs_file):
            with open(self.tabs_file, "w"):
                pass
            self._logger.debug(
                "No tabs.yml file found. Generated {}".format(self.tabs_file))

        if self.data_dir and not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            self._logger.debug("Created directory {}".format(self.data_dir))

        if self.app_data_dir is not None and \
                not os.path.exists(self.app_data_dir):

            os.makedirs(self.app_data_dir)
            self._logger.debug("Created {}".format(self.app_data_dir))


def main() -> None:
    app = StartupDefault()
    sys.exit(app.run())


if __name__ == '__main__':
    main()
