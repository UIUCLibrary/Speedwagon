import sys
from multiprocessing import freeze_support


def main():
    import speedwagon.startup
    speedwagon.startup.main()
    sys.exit(0)


if __name__ == '__main__':
    freeze_support()
    main()
