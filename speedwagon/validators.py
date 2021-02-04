import abc
import os


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

    def __init__(self, key) -> None:
        self._key = key

    @staticmethod
    def destination_exists(path) -> bool:
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
    def __init__(self):
        self._validators = {}

    def register_validator(self, key, validator):
        self._validators[key] = validator

    def create(self, key, **kwargs):
        builder = self._validators.get(key)
        if not builder:
            raise ValueError(key)
        return builder


class OptionValidator(OptionValidatorFactory):
    def get(self, service_id, **kwargs):
        return self.create(service_id, **kwargs)
