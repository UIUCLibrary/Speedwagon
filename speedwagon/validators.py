"""Validation code.

This contains mainly code for validating input.
"""
from __future__ import annotations
import abc
import os
import sys
import warnings
from typing import (
    Dict,
    Any,
    Generic,
    Optional,
    List,
    TypeVar,
    Union,
    Callable, TYPE_CHECKING, Tuple
)

if TYPE_CHECKING:
    from speedwagon.workflow import UserDataType
    if sys.version_info >= (3, 10):
        from typing import TypeAlias
    else:
        from typing_extensions import TypeAlias


__all__ = [
    'AbsOutputValidation',
    'ExistsOnFileSystem',
    'IsDirectory',
    "CustomValidation",
]

NO_CANDIDATE_MESSAGE = "No candidate given to investigate"

FilePath: TypeAlias = Union[
    str,
    bytes,
    os.PathLike[str],
    os.PathLike[bytes]
]


class AbsOptionValidator(abc.ABC):
    """Base class for option validators."""

    def __init__(self):
        warnings.warn(
            "Use AbsOutputValidation instead",
            DeprecationWarning,
            stacklevel=1)
        super().__init__()

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
        super().__init__()
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


_T = TypeVar("_T")
ReportT = TypeVar("ReportT")

JobOptionsType: TypeAlias = Dict[str, Union[str, Any]]


class AbsOutputValidation(abc.ABC, Generic[_T, ReportT]):
    """Generic abstract base class for user options validations.

    If validate() is called or the "candidate" property is read prior to
    setting the candidate property, a ValueError will be thrown.

    To subclass, implement the investigate() method.
    """

    def __init__(self) -> None:
        """Create a new validation object with no results."""
        super().__init__()
        self.is_valid: Optional[bool] = None
        self._is_set = False

        # self._candidate is default is None but the value is saved as a
        # single item tuple once it is set. This is so that the set value can
        # be None and still throw a ValueError if explicitly read before it is
        # set.
        self._candidate: Optional[Tuple[Optional[_T]]] = None
        self.findings: List[ReportT] = []

    @property
    def candidate(self) -> Optional[_T]:
        """Get candidate.

        If not set prior, this will raise a ValueError
        """
        if self._candidate is None:
            raise ValueError("candidate value not defined")

        return self._candidate[0]

    @candidate.setter
    def candidate(self, value: Optional[_T]) -> None:
        self._is_set = True
        self._candidate = (value,)

    @abc.abstractmethod
    def investigate(
        self,
        candidate: Optional[_T],
        job_options: Dict[str, UserDataType]
    ) -> List[ReportT]:
        """Test that returns any findings in the generic report format.

        This needs to be implemented in any subclass.

        Args:
            candidate: Anything that is being validated.
            job_options: dictionary of the keys and values of other user
                arguments used by the job.

        Returns:
            Returns a list of findings if any found, otherwise it returns an
            empty list.
        """

    def validate(self, job_options: Optional[JobOptionsType] = None) -> None:
        """Set is_valid and findings."""
        self.findings = (
            self.investigate(self.candidate, job_options=job_options or {})
        )

        self.is_valid = len(self.findings) == 0

    def reset(self) -> None:
        """Reset any findings stored by the validation instance."""
        self.findings.clear()
        self.is_valid = None


class ExistsOnFileSystem(AbsOutputValidation[FilePath, str]):
    """Validate a file or folder exists on the file system."""

    default_message_template = "{} does not exist"

    def __init__(self, message_template=default_message_template) -> None:
        """Create a new validation that checks for existence on file system.

        Args:
            message_template: Message template when candidate fails validation.
                Note: There is a single value in the template for the
                input value.
        """
        super().__init__()
        self.file_not_exist_message = message_template

    @staticmethod
    def path_exists(path: FilePath) -> bool:
        """Return the existence of a file or directory at a given path."""
        return os.path.exists(path)

    def investigate(
        self,
        candidate: Optional[FilePath],
        job_options: JobOptionsType
    ) -> List[str]:
        """Investigate the existence of the candidate's file path.

        Only a single response in this validation. If the candidate exists on
        the filesystem, no message is returned. If it does not exist, a message
        string explains that.
        """
        if candidate is None:
            raise ValueError(NO_CANDIDATE_MESSAGE)
        if not self.path_exists(candidate):
            return [self.file_not_exist_message.format(candidate)]
        return []


class IsDirectory(AbsOutputValidation[FilePath, str]):
    """Validation for the string pointing to a directory."""

    def __init__(
        self,
        message_template="{} is not a directory",
    ) -> None:
        """Create a new validation for string pointing to directory.

        Args:
            message_template: Message template when candidate fails validation.
                Note: There is a single value in the template for the
                input value.
        """
        super().__init__()
        self.invalid_input_message_template = message_template
        self.checking_strategy = os.path.isdir

    def investigate(
        self,
        candidate: Optional[FilePath],
        job_options: JobOptionsType
    ) -> List[str]:
        """Validate the candidate is a directory."""
        if candidate is None:
            raise ValueError(NO_CANDIDATE_MESSAGE)
        if not self.is_dir(candidate):
            return [self.invalid_input_message_template.format(candidate)]
        return []

    def is_dir(self, path: FilePath) -> bool:
        """Return if the path provided is a directory."""
        return self.checking_strategy(path)


class CustomValidation(AbsOutputValidation[_T, str]):
    """Allows for simple custom validation.

    Examples:
        .. testsetup:: *

            from speedwagon.validators import *

        >>> validation = CustomValidation(
        ...     query=lambda candidate, _: candidate.isalpha(),
        ...     failure_message_function=lambda candidate:(
        ...        f"{candidate} contains non-alphanumerical characters"
        ...         )
        ... )
        >>> validation.investigate("s1", {})
        ['s1 contains non-alphanumerical characters']
    """

    def __init__(
        self,
        query: Callable[[Optional[_T], JobOptionsType], bool],
        failure_message_function: Optional[
            Callable[[Optional[_T]], str]
        ] = None
    ) -> None:
        """Create a custom validation object.

        Args:
            query: Callable function that validates the candidate and
                returns True or False based on the success of failure of
                the validation.
            failure_message_function: Callable function that takes the
                failed candidate as an argument and returns a string to explain
                the validation failed.

        """
        super().__init__()
        self.query = query
        self.generate_finding_message = (
            failure_message_function or
            (lambda candidate: f"{candidate} failed validation")
        )

    def investigate(
        self,
        candidate: Optional[_T],
        job_options: JobOptionsType
    ) -> List[str]:
        """Use the custom query message to validate."""
        if self.query(candidate, job_options) is False:
            return [self.generate_finding_message(candidate)]
        return []


class IsFile(AbsOutputValidation[FilePath, str]):
    default_message_template = "{} is not a file"

    def __init__(self, message_template=default_message_template) -> None:
        super().__init__()
        self.invalid_input_message_template = message_template
        self.checking_strategy = os.path.isfile

    def is_file(self, candidate: FilePath) -> bool:
        return self.checking_strategy(candidate)

    def investigate(
        self,
        candidate: Optional[FilePath],
        job_options: Dict[str, UserDataType]
    ) -> List[str]:
        if candidate is None:
            raise ValueError(NO_CANDIDATE_MESSAGE)
        if not self.is_file(candidate):
            return [self.invalid_input_message_template.format(candidate)]
        return []
