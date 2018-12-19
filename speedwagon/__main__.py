import logging
import sys
import speedwagon
import speedwagon.config
import speedwagon.startup
import speedwagon.gui
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        import pytest  # type: ignore
        sys.exit(pytest.main(sys.argv[2:]))

    speedwagon.startup.main()


if __name__ == '__main__':
    main()
