import logging
import sys
import forseti
import forseti.gui
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def main():
    print("{}: {}".format(forseti.__name__, forseti.__version__))

    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        import pytest  # type: ignore
        sys.exit(pytest.main(sys.argv[2:]))
    else:
        forseti.gui.main()


if __name__ == '__main__':
    main()
