import abc
import os
from typing import Dict, Mapping, Any, Optional


class AbsOptionValidator(abc.ABC):
    @abc.abstractmethod
    def is_valid(self, **user_data: Mapping[str, Any]) -> bool:
        """Evaluate if the kwargs are valid"""

    @abc.abstractmethod
    def explanation(self, **user_data: Mapping[str, Any]) -> str:
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

    def is_valid(self, **user_data: Mapping[str, Any]) -> bool:
        if self._key not in user_data:
            return False
        output = user_data[self._key]
        if not isinstance(output, str):
            return False
        if self.destination_exists(output) is False:
            return False
        return True

    def explanation(self, **user_data: Mapping[str, Any]) -> str:
        destination = user_data[self._key]
        if not isinstance(destination, str):
            raise TypeError(f"{self._key} not a string")

        if self.destination_exists(destination) is False:
            return f"Directory {destination} does not exist"
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
