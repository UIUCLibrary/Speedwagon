import logging
import sys
import speedwagon
import speedwagon.gui
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def main():
    print("{}: {}".format(speedwagon.__name__, speedwagon.__version__))

    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        import pytest  # type: ignore
        sys.exit(pytest.main(sys.argv[2:]))
    else:
        speedwagon.gui.main()


if __name__ == '__main__':
    main()
