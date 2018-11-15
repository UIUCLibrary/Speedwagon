import os
from pathlib import Path

import abc
import collections.abc


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
            return self.get_app_data_directory()

        if k == "app_data_directory":
            return self.get_app_data_directory()

        return self._data[k]


class WindowsConfig(AbsConfig):

    def get_user_data_directory(self) -> str:
        return os.path.join(str(Path.home()), "Speedwagon", "data")

    def get_app_data_directory(self) -> str:
        return os.path.join(os.getenv("LocalAppData"), "Speedwagon")
