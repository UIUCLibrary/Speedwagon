import argparse
from typing import Optional

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


def get_config(configuration: Optional[config.AbsConfig] = None) -> \
        config.AbsConfig:
    """Load a configuration of config.AbsConfig
    If no argument is included, it will try to guess the best one."""
    if configuration is None:
        return config.WindowsConfig()
    else:
        return configuration
