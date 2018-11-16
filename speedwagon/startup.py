import argparse
import contextlib
import io
import logging
import os
import sys
from typing import Optional

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


def main(args: Optional[argparse.Namespace] = None) -> None:
    app = QtWidgets.QApplication(sys.argv)

    logo = pkg_resources.resource_stream(__name__, "logo.png")
    splash = QtWidgets.QSplashScreen(QtGui.QPixmap(logo.name).scaled(400, 400))

    splash.setEnabled(False)
    splash.setWindowFlags(
        QtCore.Qt.WindowStaysOnTopHint |
        QtCore.Qt.FramelessWindowHint
    )

    splash.show()

    icon = pkg_resources.resource_stream(__name__, "favicon.ico")
    app.setWindowIcon(QtGui.QIcon(icon.name))
    app.setApplicationVersion(f"{speedwagon.__version__}")
    app.setApplicationDisplayName(f"{speedwagon.__name__.title()}")

    with worker.ToolJobManager() as work_manager:
        splash_message_handler = SplashScreenLogHandler(splash)

        windows = MainWindow(work_manager=work_manager, debug=args.debug)
        windows.setWindowTitle("")
        windows.log_manager.info(
            f"{speedwagon.__name__.title()} {speedwagon.__version__}"
        )
        windows.log_manager.addHandler(splash_message_handler)

        # ==================================================
        # Load configurations
        windows.log_manager.debug("Loading settings")
        platform_settings = speedwagon.config.get_platform_settings()

        # Make sure required directories exists
        data_dir = platform_settings.get("user_data_directory")
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)
            windows.log_manager.debug("Created directory {}".format(data_dir))

        app_data_dir = platform_settings.get("app_data_directory")

        if app_data_dir is not None and not os.path.exists(app_data_dir):
            os.makedirs(app_data_dir)
            windows.log_manager.debug("Created {}".format(app_data_dir))

        config_file = os.path.join(
            platform_settings.get_app_data_directory(), "config.ini")

        if not os.path.exists(config_file):
            speedwagon.config.generate_default(config_file)

        with speedwagon.config.ConfigManager(config_file) as f:
            platform_settings._data.update(f.global_settings)

        if args.debug:
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
            workflows = job.available_workflows()
            windows.add_tab("Workflows", workflows)
        workflow_errors_msg = loading_workflows_stream.getvalue().strip()

        if workflow_errors_msg:
            for line in workflow_errors_msg.split("\n"):
                windows.log_manager.warn(line)

        # ==================================================
        windows.log_manager.debug("Loading User Interface")
        windows.show()

        windows.log_manager.removeHandler(splash_message_handler)
        if args:
            if args.start_tab:
                windows.set_current_tab(tab_name=args.start_tab)
        splash.finish(windows)

        windows.log_manager.info("Ready")
        rc = app.exec_()
    sys.exit(rc)


if __name__ == '__main__':
    main()
