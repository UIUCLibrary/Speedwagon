import abc
import os
from typing import Dict


class AbsOptionValidator(abc.ABC):
    @abc.abstractmethod
    def is_valid(self, **user_data) -> bool:
        """Evaluate if the kwargs are valid"""

    @abc.abstractmethod
    def explanation(self, **user_data) -> str:
        """Get reason for is_valid.

        Args:
            **user_data:

        Returns:
            returns a message explaining why something isn't valid, otherwise
                produce the message "ok"
        """


class DirectoryValidation(AbsOptionValidator):

    def __init__(self, key: str) -> None:
        self._key: str = key

    @staticmethod
    def destination_exists(path: str) -> bool:
        return os.path.exists(path)

    def is_valid(self, **user_data) -> bool:
        output = user_data.get(self._key)
        if not output:
            return False
        if self.destination_exists(output) is False:
            return False
        return True

    def explanation(self, **user_data) -> str:
        if self.destination_exists(user_data[self._key]) is False:
            return f"Directory {user_data[self._key]} does not exist"
        return "ok"


class OptionValidatorFactory:
    def __init__(self) -> None:
        self._validators: Dict[str, AbsOptionValidator] = {}

    def register_validator(self,
                           key: str,
                           validator: AbsOptionValidator) -> None:

        self._validators[key] = validator

    def create(self, key: str) -> AbsOptionValidator:
        builder = self._validators.get(key)
        if not builder:
            raise ValueError(key)
        return builder


class OptionValidator(OptionValidatorFactory):
    def get(self, key: str) -> AbsOptionValidator:
        return self.create(key)
