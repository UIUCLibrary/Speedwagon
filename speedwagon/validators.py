"""Shared validation code."""

import abc
import os
from typing import Dict, Any


class AbsOptionValidator(abc.ABC):
    """Base class for option validators."""

    @abc.abstractmethod
    def is_valid(self, **user_data: Any) -> bool:
        """Evaluate if the kwargs are valid."""

    @abc.abstractmethod
    def explanation(self, **user_data: Any) -> str:
        """Get reason for is_valid.

        Args:
            **user_data: user data to inspect.

        Returns:
            returns a message explaining why something isn't valid, otherwise
                produce the message "ok"
        """


class DirectoryValidation(AbsOptionValidator):
    """Validate directory user input."""

    def __init__(self, key: str) -> None:
        """Create a new directory validator."""
        self._key: str = key

    @staticmethod
    def destination_exists(path: str) -> bool:
        """Check if destination exists."""
        return os.path.exists(path)

    def is_valid(self, **user_data: Any) -> bool:
        """Check if the user data is valid."""
        if self._key not in user_data:
            return False
        output = user_data[self._key]
        if not isinstance(output, str):
            return False
        if self.destination_exists(output) is False:
            return False
        return True

    def explanation(self, **user_data: Any) -> str:
        """Get a human readable explanation about the current status."""
        destination = user_data[self._key]
        if destination is None:
            return f"{self._key} None"
        if not isinstance(destination, str):
            raise TypeError(f"{self._key} not a string")

        if self.destination_exists(destination) is False:
            return f'Directory "{destination}" does not exist'
        return "ok"


class OptionValidatorFactory:
    """Option validator factory."""

    def __init__(self) -> None:
        """Create an option validator factory."""
        self._validators: Dict[str, AbsOptionValidator] = {}

    def register_validator(
        self, key: str, validator: AbsOptionValidator
    ) -> None:
        """Register validator."""
        self._validators[key] = validator

    def create(self, key: str) -> AbsOptionValidator:
        """Create a new option validator."""
        builder = self._validators.get(key)
        if not builder:
            raise ValueError(key)
        return builder


class OptionValidator(OptionValidatorFactory):
    """Option validator."""

    def get(self, key: str) -> AbsOptionValidator:
        """Get option validator."""
        return self.create(key)
