import logging
import os
import sys
import speedwagon
import speedwagon.startup
import speedwagon.gui
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def main():
    startup_settings = speedwagon.startup.parse_args()

    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        import pytest  # type: ignore
        sys.exit(pytest.main(sys.argv[2:]))

    # Load configurations
    config_settings = speedwagon.startup.get_config()

    # Make sure required directories exists
    data_dir = config_settings.get("user_data_dir")
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print("Created {}".format(data_dir))

    app_data_dir = config_settings.get("app_data_dir")
    if app_data_dir and not os.path.exists(app_data_dir):
        os.makedirs(app_data_dir)
        print("Created {}".format(app_data_dir))

    # Start up
    print("{}: {}".format(speedwagon.__name__, speedwagon.__version__))
    speedwagon.gui.main(startup_settings)


if __name__ == '__main__':
    main()
