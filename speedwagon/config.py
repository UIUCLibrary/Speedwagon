import configparser
import contextlib
import os
import sys
from pathlib import Path

import abc
import collections.abc
from typing import Optional


class AbsConfig(collections.abc.Mapping):

    def __init__(self) -> None:
        super().__init__()
        self._data = dict()

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
        return os.path.join(os.getenv("LocalAppData"), "Speedwagon")


class ConfigManager(contextlib.AbstractContextManager):
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
        try:
            return self.cfg_parser["GLOBAL"]
        except KeyError:
            print("Unable to load global settings.", file=sys.stderr)
            return dict()


def generate_default(config_file):
    base_directory = os.path.dirname(config_file)
    if base_directory and not os.path.exists(base_directory):
        os.makedirs(base_directory)
    with open(config_file, "w") as f:
        f.write("[GLOBAL]\n")


def get_platform_settings(configuration: Optional[AbsConfig] = None) -> \
        AbsConfig:

    """Load a configuration of config.AbsConfig
    If no argument is included, it will try to guess the best one."""

    if configuration is None:
        return WindowsConfig()
    else:
        return configuration
