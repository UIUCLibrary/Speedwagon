import logging
import sys
import speedwagon
import speedwagon.config
import speedwagon.startup
import speedwagon.gui
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def main(argv=None) -> None:
    argv = argv or sys.argv

    if len(argv) > 1 and argv[1] == "--pytest":
        import pytest  # type: ignore  # noqa
        sys.exit(pytest.main(argv[2:]))

    speedwagon.startup.main(argv)


if __name__ == '__main__':
    main()
