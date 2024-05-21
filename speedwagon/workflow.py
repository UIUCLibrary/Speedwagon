"""Toolkit for generating new workflows."""
from __future__ import annotations
import abc
import dataclasses
import json
import os
import typing
from typing import (
    Any, Dict, List, Optional, Union, TYPE_CHECKING, Callable, TypeVar
)

import speedwagon.config
import speedwagon.job
if TYPE_CHECKING:
    from speedwagon.validators import AbsOutputValidation

UserDataType = Union[str, bool, int, None]
UserData = Dict[str, UserDataType]

_T = TypeVar('_T')

__all__ = [
    'AbsOutputOptionDataType',
    "ChoiceSelection",
    "FileSelectData",
    "TextLineEditData",
    "DirectorySelect",
    "BooleanSelect"
]


@dataclasses.dataclass
class ValidationRequirement(typing.Generic[_T]):
    validation: AbsOutputValidation[_T, str]
    condition: Callable[[_T, UserData], bool]


class AbsOutputOptionDataType(abc.ABC, typing.Generic[_T]):
    """Base case for generating user option types."""

    label: str
    widget_name: str
    setting_name: Optional[str]
    required: bool

    def __init_subclass__(cls) -> None:
        """Verify that any subclass has a widget_name defined."""
        if not hasattr(cls, "widget_name"):
            raise TypeError(
                f"Can't instantiate abstract class {cls.__name__} "
                f"without abstract property widget_name"
            )
        return super().__init_subclass__()

    def __init__(self, label: str, required: bool) -> None:
        """Create a new output time with a given label."""
        super().__init__()
        self.label = label
        self._value_has_been_set = False
        self._value: Optional[_T] = None
        self.placeholder_text: Optional[str] = None
        self.required = required
        self.setting_name: Optional[str] = None
        self.default_value: Optional[_T] = None
        self._validators: List[ValidationRequirement[_T]] = []

    @property
    def value(self) -> Optional[_T]:  # noqa: D102
        return self._value

    @value.setter
    def value(self, value: _T) -> None:
        self._value = value
        self._value_has_been_set = True

    def serialize(self) -> Dict[str, Any]:
        """Serialize the data."""
        data = {
            "widget_type": self.widget_name,
            "label": self.label,
            "required": self.required,
            "setting_name": self.setting_name or self.label.replace(" ", "_"),
        }
        if self.value is not None:
            data["value"] = self.value

        if self.placeholder_text is not None:
            data["placeholder_text"] = self.placeholder_text
        return data

    def build_json_data(self) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.serialize())

    def add_validation(
        self,
        validator: AbsOutputValidation[_T, str],
        condition: Optional[Callable[[_T, UserData], bool]] = None
    ) -> None:
        """Include a validation for the value of this object."""
        def default_condition(_: Optional[_T], __: UserData) -> bool:
            return True

        self._validators.append(
            ValidationRequirement(validator, condition or default_condition)
        )

    def get_findings(self, job_args: Optional[UserData] = None) -> List[str]:
        """Get findings from the data using the assigned validators.

        Args:
            job_args: All job argument values.

        Returns: Returns a list of findings discovered by the validator.

        """
        findings: List[str] = []
        for validator in self._validators:
            if (
                    self._value_has_been_set and
                    not validator.condition(
                        typing.cast(_T, self._value), (job_args or {})
                    )
            ):
                continue
            validator.validation.candidate = self._value
            validator.validation.validate(job_args)
            findings += validator.validation.findings
            validator.validation.reset()
        return findings


class ChoiceSelection(AbsOutputOptionDataType):
    """Choice of predefined strings."""

    widget_name: str = "ChoiceSelection"

    def __init__(self, label: str, required=True) -> None:
        """Present the user with a possible selection of choices."""
        super().__init__(label, required)
        self._selections: List[str] = []

    def add_selection(self, label: str) -> None:
        """Add a possible choice for the user to select."""
        self._selections.append(label)

    def serialize(self) -> Dict[str, Any]:
        """Serialize the data.

        Notes:
            placeholder_text and selections are added here.
        """
        data = super().serialize()
        if self.placeholder_text is not None:
            data["placeholder_text"] = self.placeholder_text
        data["selections"] = self._selections
        return data


class FileSelectData(AbsOutputOptionDataType):
    r"""File selection.

    Attributes:
        filter:
            File selection type filter. This uses the same convention used
            by Qt

            See https://doc.qt.io/qt-6/qfiledialog.html for more info.

            For example: "Checksum files (\*.md5)"
    """

    widget_name: str = "FileSelect"
    filter: Optional[str]

    def __init__(self, label: str, required: bool = True) -> None:
        """Select a file."""
        super().__init__(label, required)
        self.filter: Optional[str] = None

    def serialize(self) -> Dict[str, Any]:
        """Serialize the data.

        Notes:
            filter is added for selecting certain file types.
        """
        data = super().serialize()
        data["filter"] = self.filter
        return data


class TextLineEditData(AbsOutputOptionDataType):
    """Single text line."""

    def __init__(self, label: str, required: bool = True) -> None:
        """Create a new TextLineEditData object."""
        super().__init__(label, required)

    widget_name = "TextInput"


class DirectorySelect(AbsOutputOptionDataType):
    """Directory path selection."""

    def __init__(self, label: str, required: bool = True) -> None:
        """Create a new directory selection object."""
        super().__init__(label, required)

    widget_name = "DirectorySelect"


class BooleanSelect(AbsOutputOptionDataType):
    """Boolean selection."""

    def __init__(self, label: str, required: bool = False) -> None:
        """Create a new BooleanSelect object."""
        super().__init__(label, required)

    widget_name = "BooleanSelect"

    def serialize(self) -> Dict[str, Any]:
        """Serialize."""
        data = super().serialize()
        if self.value is None:
            data["value"] = False
        return data


def initialize_workflows() -> List[speedwagon.job.Workflow]:
    """Initialize workflow for use."""
    config_strategy = speedwagon.config.StandardConfigFileLocator()
    workflows = []
    backend_yaml = os.path.join(
        config_strategy.get_app_data_dir(),
        speedwagon.config.WORKFLOWS_SETTINGS_YML_FILE_NAME,
    )
    for workflow_klass in sorted(
        speedwagon.job.available_workflows().values(),
        key=lambda workflow: workflow.name,
    ):
        config_backend = speedwagon.config.YAMLWorkflowConfigBackend()
        workflow = workflow_klass()
        config_backend.workflow = workflow
        config_backend.yaml_file = backend_yaml
        workflow.set_options_backend(config_backend)
        workflows.append(workflow)
    return workflows
