import configparser
import contextlib
import os
import sys
from collections import OrderedDict
from pathlib import Path
import io
import abc
import collections.abc
from typing import Optional, Dict

from speedwagon.models import SettingsModel


class AbsConfig(collections.abc.Mapping):

    def __init__(self) -> None:
        super().__init__()
        self._data: Dict[str, str] = dict()

    @abc.abstractmethod
    def get_user_data_directory(self) -> str:
        """Location for user data"""

    @abc.abstractmethod
    def get_app_data_directory(self) -> str:
        """Location to the application data. Such as .ini file"""

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __contains__(self, x: object) -> bool:

        if x == "app_data_directory":
            return True

        if x == "user_data_directory":
            return True

        return x in self._data

    def __getitem__(self, k):

        if k == "user_data_directory":
            return self.get_user_data_directory()

        if k == "app_data_directory":
            return self.get_app_data_directory()

        return self._data[k]


class WindowsConfig(AbsConfig):

    def get_user_data_directory(self) -> str:
        return os.path.join(str(Path.home()), "Speedwagon", "data")

    def get_app_data_directory(self) -> str:
        data_path = os.getenv("LocalAppData")
        if data_path:
            return os.path.join(data_path, "Speedwagon")
        else:
            raise FileNotFoundError("Unable to located data_directory")


class ConfigManager(contextlib.AbstractContextManager):
    BOOLEAN_SETTINGS = [
            "debug",
        ]

    def __init__(self, config_file):
        self._config_file = config_file

    def __enter__(self):
        self.cfg_parser = configparser.ConfigParser()
        self.cfg_parser.read(self._config_file)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("Note: Only able to read settings. "
              "To change any settings, edit {}".format(self._config_file),
              file=sys.stderr)

    @property
    def global_settings(self)->dict:

        global_settings = dict()
        try:
            global_section = self.cfg_parser["GLOBAL"]
            for setting in ConfigManager.BOOLEAN_SETTINGS:
                if setting in global_section:
                    global_settings[setting] = \
                        global_section.getboolean(setting)

            for k, v in global_section.items():
                if k not in ConfigManager.BOOLEAN_SETTINGS:
                    global_settings[k] = v

        except KeyError:
            print("Unable to load global settings.", file=sys.stderr)
        return global_settings


def generate_default(config_file):
    base_directory = os.path.dirname(config_file)
    if base_directory and not os.path.exists(base_directory):
        os.makedirs(base_directory)

    platform_settings = get_platform_settings()
    data_dir = platform_settings.get("user_data_directory")
    tessdata = os.path.join(data_dir, "tessdata")

    config = configparser.ConfigParser(allow_no_value=True)
    config.add_section("GLOBAL")
    config['GLOBAL'] = {
        "tessdata": tessdata,
        "starting-tab": "Tools",
        "debug": False
    }
    with open(config_file, "w") as f:
        config.write(f)
        # f.write("[GLOBAL]\n")


def get_platform_settings(configuration: Optional[AbsConfig] = None) -> \
        AbsConfig:

    """Load a configuration of config.AbsConfig
    If no argument is included, it will try to guess the best one."""

    if configuration is None:
        return WindowsConfig()
    else:
        return configuration


def build_setting_model(config_file):

    config = configparser.ConfigParser()
    config.read(config_file)
    global_settings = config["GLOBAL"]
    my_model = SettingsModel()
    for k, v in global_settings.items():
        my_model.add_setting(k, v)
    return my_model


def serialize_settings_model(model: SettingsModel):
    config_data = configparser.ConfigParser()
    config_data["GLOBAL"] = {}
    global_data: Dict[str, str] = OrderedDict()

    for i in range(model.rowCount()):
        key = model.index(i, 0).data()
        value = model.index(i, 1).data()
        global_data[key] = value
    config_data["GLOBAL"] = global_data

    with io.StringIO() as f:
        config_data.write(f)
        return f.getvalue()
