import abc
import argparse
import collections
import contextlib
import io
import logging
import os
import sys
from typing import Dict, Union

import pkg_resources
from PyQt5 import QtWidgets, QtGui, QtCore

import speedwagon
import speedwagon.config
from speedwagon import worker, job
from speedwagon.gui import SplashScreenLogHandler, MainWindow


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


def main() -> None:
    platform_settings = speedwagon.config.get_platform_settings()

    config_file = os.path.join(
        platform_settings.get_app_data_directory(), "config.ini")

    if not os.path.exists(config_file):
        speedwagon.config.generate_default(config_file)

    resolution_order = [
        DefaultsSetter(),
        ConfigFileSetter(config_file),
        CliArgsSetter(),
    ]
    startup_settings = dict()

    for settings_strategy in resolution_order:
        startup_settings = settings_strategy.update(startup_settings)

    app = QtWidgets.QApplication(sys.argv)
    logo = pkg_resources.resource_stream(__name__, "logo.png")
    splash = QtWidgets.QSplashScreen(QtGui.QPixmap(logo.name).scaled(400, 400))

    splash.setEnabled(False)
    splash.setWindowFlags(
        QtCore.Qt.WindowStaysOnTopHint |
        QtCore.Qt.FramelessWindowHint
    )
    splash_message_handler = SplashScreenLogHandler(splash)
    if startup_settings['debug']:
        splash_message_handler.setLevel(logging.DEBUG)
    else:
        splash_message_handler.setLevel(logging.INFO)
    splash.show()
    app.processEvents()

    icon = pkg_resources.resource_stream(__name__, "favicon.ico")
    app.setWindowIcon(QtGui.QIcon(icon.name))
    app.setApplicationVersion(f"{speedwagon.__version__}")
    app.setApplicationDisplayName(f"{speedwagon.__name__.title()}")
    app.processEvents()
    with worker.ToolJobManager() as work_manager:
        windows = MainWindow(work_manager=work_manager,
                             debug=startup_settings['debug'])

        windows.setWindowTitle("")
        windows.log_manager.addHandler(splash_message_handler)
        windows.log_manager.info(
            f"{speedwagon.__name__.title()} {speedwagon.__version__}"
        )
        app.processEvents()


        # ==================================================
        # Load configurations
        windows.log_manager.debug("Loading settings")

        # Make sure required directories exists
        data_dir = platform_settings.get("user_data_directory")
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)
            windows.log_manager.debug("Created directory {}".format(data_dir))

        app_data_dir = platform_settings.get("app_data_directory")

        if app_data_dir is not None and not os.path.exists(app_data_dir):
            os.makedirs(app_data_dir)
            windows.log_manager.debug("Created {}".format(app_data_dir))

        with speedwagon.config.ConfigManager(config_file) as f:
            platform_settings._data.update(f.global_settings)
        # windows.user_settings = platform_settings
        work_manager.user_settings = platform_settings
        work_manager.configuration_file = config_file
        # ==================================================
        if startup_settings['debug'] is True:
            splash_message_handler.setLevel(logging.DEBUG)
            windows.log_manager.debug("DEBUG mode")

        else:
            splash_message_handler.setLevel(logging.INFO)

        # ==================================================
        windows.log_manager.debug("Loading Tools")

        loading_job_stream = io.StringIO()

        with contextlib.redirect_stderr(loading_job_stream):
            tools = job.available_tools()
            windows.add_tools(tools)

        tool_error_msgs = loading_job_stream.getvalue().strip()
        if tool_error_msgs:
            for line in tool_error_msgs.split("\n"):
                windows.log_manager.warn(line)

        # ==================================================
        windows.log_manager.debug("Loading Workflows")

        loading_workflows_stream = io.StringIO()

        with contextlib.redirect_stderr(loading_workflows_stream):
            all_workflows = job.available_workflows()
            selection_workflows = get_selection(all_workflows)
            windows.add_tab("Subsection", selection_workflows)
            windows.add_tab("All", collections.OrderedDict(sorted(all_workflows.items())))
        workflow_errors_msg = loading_workflows_stream.getvalue().strip()

        if workflow_errors_msg:
            for line in workflow_errors_msg.split("\n"):
                windows.log_manager.warn(line)

        # ==================================================
        windows.log_manager.debug("Loading User Interface")
        windows.show()

        windows.log_manager.removeHandler(splash_message_handler)
        if "starting-tab" in startup_settings:
            windows.set_current_tab(tab_name=startup_settings['starting-tab'])

        # QtCore.QThread.sleep(1)
        splash.finish(windows)

        windows.log_manager.info("Ready")
        rc = app.exec_()
    sys.exit(rc)


if __name__ == '__main__':
    main()
