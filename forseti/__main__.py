import sys
import pkg_resources
from forseti import gui

def main():
    try:
        dist = pkg_resources.get_distribution("forseti")
        print("{}: {}".format(dist.project_name, dist.version))
    except pkg_resources.DistributionNotFound:
        print("Development version")

    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        import pytest  # type: ignore
        sys.exit(pytest.main(sys.argv[2:]))
    else:
        gui.main()


if __name__ == '__main__':
    main()
