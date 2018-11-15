import os
from pathlib import Path

import abc


class AbsConfig(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_user_data_directory(self) -> str:
        """Location for user data"""

    @abc.abstractmethod
    def get_app_data_directory(self) -> str:
        """Location to the application data. Such as .ini file"""


class WindowsConfig(AbsConfig):

    def get_user_data_directory(self) -> str:
        return os.path.join(str(Path.home()), "Speedwagon", "data")

    def get_app_data_directory(self) -> str:
        return os.path.join(os.getenv("LocalAppData"), "Speedwagon")
