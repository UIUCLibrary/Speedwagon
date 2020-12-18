"""Load and save user configurations"""
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
import platform
from speedwagon.models import SettingsModel


class AbsConfig(collections.abc.Mapping):
    """Abstract class for defining where speedwagon should locate data files"""

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


class NixConfig(AbsConfig):

    def get_user_data_directory(self) -> str:
        data_dir = os.path.join(self._get_app_dir(), "data")
        return data_dir

    def get_app_data_directory(self) -> str:
        data_dir = self._get_app_dir()
        return data_dir

    @staticmethod
    def _get_app_dir() -> str:
        return os.path.join(str(Path.home()), ".config", "Speedwagon")


class WindowsConfig(AbsConfig):
    """Speedwagon configuration for running on Microsoft Windows machine

    It uses a subfolder in the user's home directory to store data such as
    tesseract ocr data. For example:
    ``C:\\\\Users\\\\johndoe\\\\Speedwagon\\\\data``

    It uses ``%LocalAppData%`` for app data

    """

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
        pass

    @property
    def global_settings(self) -> dict:

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
    """Generate config file with default settings"""

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
        "getmarc_server_url": "",
        "starting-tab": "Tools",
        "debug": False
    }
    with open(config_file, "w") as f:
        config.write(f)


def get_platform_settings(configuration: Optional[AbsConfig] = None) -> \
        AbsConfig:
    """Load a configuration of config.AbsConfig
    If no argument is included, it will try to guess the best one."""
    configurations = {
        "Windows": WindowsConfig,
        "Darwin": NixConfig,
        "Linux": NixConfig,
    }
    if configuration is None:
        system_config = configurations.get(platform.system())
        if system_config is None:
            raise ValueError(f"Platform {platform.system()} not supported")
        return system_config()
    return configuration


def build_setting_model(config_file) -> SettingsModel:
    """Read a configuration file and generate a SettingsModel"""

    config = configparser.ConfigParser()
    config.read(config_file)
    global_settings = config["GLOBAL"]
    my_model = SettingsModel()
    for k, v in global_settings.items():
        my_model.add_setting(k, v)
    return my_model


def serialize_settings_model(model: SettingsModel) -> str:
    """Convert a SettingsModel into a data format that can be written to a
    file.

    Note:
        This only generates and returns a string. You are still responsible to
        write that data to a file.

    """
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
