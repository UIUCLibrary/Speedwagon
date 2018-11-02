import argparse
import speedwagon


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
