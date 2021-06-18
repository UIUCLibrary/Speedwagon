"""Entry-point for running speedwagon as an executable module."""

import logging
import sys

import importlib
from typing import List

import speedwagon
import speedwagon.config
import speedwagon.startup
import speedwagon.gui
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def main(argv: List[str] = None) -> None:
    argv = argv or sys.argv

    if len(argv) > 1 and argv[1] == "--pytest":
        pytest = importlib.import_module("pytest")
        sys.exit(pytest.main(argv[2:]))  # type: ignore

    speedwagon.startup.main(argv)


if __name__ == '__main__':
    main()
