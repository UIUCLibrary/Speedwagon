import sys

from forseti import gui


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        import pytest  # type: ignore
        sys.exit(pytest.main(sys.argv[2:]))
    else:
        gui.main()


if __name__ == '__main__':
    main()
