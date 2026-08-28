"""Toolkit for generating new workflows."""

from __future__ import annotations
import abc
import dataclasses
import functools
import json
import os
import typing
from typing import (
    Any,
    Collection,
    Dict,
    List,
    Optional,
    Union,
    Type,
    TYPE_CHECKING,
    Callable,
    TypeVar,
)

import speedwagon.config
import speedwagon.job
import speedwagon.utils
import speedwagon.plugins
import speedwagon.config.plugins as plugins_config

if TYPE_CHECKING:
    from speedwagon.validators import AbsOutputValidation
    from speedwagon.config import FullSettingsData
    from speedwagon.config.plugins import PluginDataType

UserDataType = Union[str, bool, int, None]
UserData = Dict[str, UserDataType]

_T = TypeVar("_T")

__all__ = [
    "AbsOutputOptionDataType",
    "ChoiceSelection",
    "FileSave",
    "FileSelectData",
    "TextLineEditData",
    "DirectorySelect",
    "BooleanSelect",

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
        condition: Optional[Callable[[_T, UserData], bool]] = None,
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
            if self._value_has_been_set and not validator.condition(
                typing.cast(_T, self._value), (job_args or {})
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


class FileSave(AbsOutputOptionDataType):
    r"""File saving.

    Attributes:
        filter:
            File selection type filter. This uses the same convention used
            by Qt

            See https://doc.qt.io/qt-6/qfiledialog.html for more info.

            For example: "Text file (\*.txt)"
    """

    widget_name = "FileSave"

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


def default_back_end_yaml() -> str:
    config_strategy = speedwagon.config.StandardConfigFileLocator(
        speedwagon.config.common.DEFAULT_CONFIG_DIRECTORY_NAME
    )
    return os.path.join(
        config_strategy.get_app_data_dir(),
        speedwagon.config.WORKFLOWS_SETTINGS_YML_FILE_NAME,
    )


def initialize_workflows(
    backend_config_file,
    backend_yaml_file_locator_strategy: Callable[
        [], str
    ] = default_back_end_yaml,
) -> List[speedwagon.job.Workflow]:
    """Initialize workflow for use."""
    workflows_ = []

    plugin_config_data = plugins_config.read_settings_data_plugins(
        speedwagon.utils.read_file(backend_config_file)
    )

    plugin_manager = speedwagon.plugins.get_plugin_manager(
        functools.partial(
            speedwagon.plugins.register_whitelisted_plugins,
            get_whitelist_strategy=lambda: (
                plugins_config.get_whitelisted_plugins_from_config_data(
                    plugin_config_data
                )
            ),
        )
    )
    locate_workflows_strategy =\
        speedwagon.job.FindAllWorkflowsPluggyPluginManagerStrategy(
            plugin_manager
        )

    for workflow_klass in sorted(
        speedwagon.job.available_workflows(locate_workflows_strategy).values(),
        key=lambda workflow: (
            workflow.name if workflow.name
            else str(workflow.__name__)
        )
    ):
        config_backend = speedwagon.config.YAMLWorkflowConfigBackend()
        workflow = workflow_klass()
        config_backend.workflow = workflow
        config_backend.yaml_file = backend_yaml_file_locator_strategy()
        workflow.set_options_backend(config_backend)
        workflows_.append(workflow)
    return workflows_


class AbsLoadWorkflowsConfig(abc.ABC):
    @abc.abstractmethod
    def add_error_logger(self, logger: Callable[[str], None]):
        """Add a logger to log errors."""

    @abc.abstractmethod
    def load(self) -> Dict[str, Type[speedwagon.job.Workflow]]:
        """Load workflows.

        Verify that the workflows are valid and return a dictionary of
        workflows. Invalid workflows do not fail but are logged using the
        error loggers.
        """


class LoadWorkflowsUsingPluginsConfig(AbsLoadWorkflowsConfig):
    def __init__(self) -> None:
        self._error_loggers: List[Callable[[str], None]] = []
        self.plugin_config_data: PluginDataType = {}
        self.workflow_validation_checkers: List[
            Callable[[Type[speedwagon.job.Workflow]], Collection[str]]
        ] = []

    def get_load_strategy(self) -> speedwagon.job.AbsWorkflowFinder:
        return speedwagon.job.OnlyActivatedPluginsWorkflows(
            plugin_settings=self.plugin_config_data
        )

    def add_error_logger(self, logger: Callable[[str], None]):
        self._error_loggers.append(logger)

    def load(self) -> Dict[str, Type[speedwagon.job.Workflow]]:
        all_workflows = speedwagon.job.available_workflows(
            strategy=self.get_load_strategy())
        for workflow_name, workflow in all_workflows.copy().items():
            for validator in self.workflow_validation_checkers:
                errors = validator(workflow)
                if errors:
                    error_message = (
                        f"Unable to load workflow '{workflow_name}'. "
                        f"Reason: {', '.join(errors)}"
                    )
                    for logger in self._error_loggers:
                        logger(error_message)
                    del all_workflows[workflow_name]
        return all_workflows


def load_workflows(
    config: AbsLoadWorkflowsConfig,
    error_loggers: Optional[List[Callable[[str], None]]] = None
) -> Dict[str, Type[speedwagon.job.Workflow]]:
    for logger in error_loggers or []:
        config.add_error_logger(logger)
    return config.load()


def locate_errors_in_workflow(
    workflow: Type[speedwagon.job.Workflow],
    settings: FullSettingsData
) -> List[str]:
    try:
        workflow(global_settings=settings.get("GLOBAL", {}))
    except (
        speedwagon.exceptions.SpeedwagonException,
        AttributeError,
    ) as error:
        return [str(error)]
    return []
