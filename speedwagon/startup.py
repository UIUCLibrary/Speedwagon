import argparse
import os
from typing import Dict, Optional

import speedwagon
from speedwagon import config


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


def get_config(configuration: Optional[config.AbsConfig] = None) -> Dict[
    str, str]:
    """Load a configuration """
    if not configuration:
        current_config = config.WindowsConfig()
    else:
        current_config = configuration
    config_settings = {
        "user_data_dir": current_config.get_user_data_directory(),
        "app_data_dir": current_config.get_app_data_directory()
    }
    print(config_settings["app_data_dir"])
    return config_settings
