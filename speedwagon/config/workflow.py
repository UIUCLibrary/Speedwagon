"""Workflow configurations."""

from __future__ import annotations
import abc
import os
import io
from typing import Optional, Dict, List, TYPE_CHECKING

try:  # pragma: no cover
    from typing import TypedDict
except ImportError:  # pragma: no cover
    from typing_extensions import TypedDict
import yaml
import yaml.emitter

from .config import StandardConfigFileLocator

if TYPE_CHECKING:
    from .common import SettingsData, SettingsDataType
    from speedwagon.job import Workflow

__all__ = [
    "WORKFLOWS_SETTINGS_YML_FILE_NAME",
    "get_config_backend",
    "WorkflowSettingsManager",
    "WorkflowSettingsYamlExporter",
    "WorkflowSettingsYAMLResolver",
    "YAMLWorkflowConfigBackend",
]


class AbsSettingsSerializer(abc.ABC):  # pylint: disable=R0903
    @abc.abstractmethod
    def serialize(
        self, workflow: Workflow, settings: SettingsData
    ) -> str:
        """Serialize workflow settings."""


class WorkflowSettingsNameValuePair(TypedDict):
    name: str
    value: SettingsDataType


StructuredWorkflowSettings = Dict[str, List[WorkflowSettingsNameValuePair]]
WORKFLOWS_SETTINGS_YML_FILE_NAME = "workflows_settings.yml"


class AbsWorkflowBackend(abc.ABC):  # pylint: disable=R0903
    def __init__(self) -> None:
        self.workflow: Optional[Workflow] = None

    @abc.abstractmethod
    def get(self, key: str) -> Optional[SettingsDataType]:
        """Get data for some key."""


class AbsWorkflowSettingsResolver(abc.ABC):  # pylint: disable=R0903
    @abc.abstractmethod
    def get_response(self, workflow: Workflow) -> SettingsData:
        """Get settings data from workflow."""


class AbsYamlConfigFileManager:
    def __init__(self, yaml_file: str) -> None:
        super().__init__()
        self.yaml_file = yaml_file


class AbsWorkflowSettingsManager(abc.ABC):
    @abc.abstractmethod
    def get_workflow_settings(self, workflow: Workflow) -> SettingsData:
        """Get settings for a workflow configured through the application."""

    @abc.abstractmethod
    def save_workflow_settings(
        self, workflow: Workflow, settings: SettingsData
    ) -> None:
        """Save workflow settings."""


class IndentingEmitter(yaml.emitter.Emitter):  # pylint: disable=R0903
    def increase_indent(
        self, flow: bool = False, indentless: bool = False
    ) -> None:
        """Ensure that lists items are always indented."""
        super().increase_indent(flow=False, indentless=False)


class IndentedYAMLDumper(yaml.Dumper):  # pylint: disable=R0903
    def increase_indent(
        self, flow: bool = False, indentless: bool = False
    ) -> None:
        super().increase_indent(flow, False)


class AbsWorkflowSettingsExporter(abc.ABC):  # pylint: disable=R0903
    @abc.abstractmethod
    def save(self, workflow: Workflow, settings: SettingsData) -> None:
        """Save settings."""


class WorkflowSettingsYAMLResolver(
    AbsYamlConfigFileManager, AbsWorkflowSettingsResolver
):
    """Workflow settings YAML resolver."""

    @staticmethod
    def read_file(file_name: str) -> str:
        """Read file."""
        with open(file_name, "r", encoding="utf-8") as file_handle:
            return file_handle.read()

    def get_config_data(
        self,
    ) -> Dict[str, List[WorkflowSettingsNameValuePair]]:
        """Get config data."""
        config_file = self.yaml_file
        return (
            yaml.load(self.read_file(config_file), Loader=yaml.SafeLoader)
            if os.path.exists(config_file)
            else {}
        )

    def get_response(self, workflow: Workflow) -> SettingsData:
        """Get response."""
        config_data = self.get_config_data()
        if workflow.name not in config_data:
            return {}
        valid_options = [
            i.setting_name if i.setting_name is not None else i.label
            for i in workflow.workflow_options()
        ]
        return {
            item["name"]: item["value"]
            for item in config_data[workflow.name]
            if item["name"] in valid_options
        }


class SettingsYamlSerializer(AbsSettingsSerializer):
    def __init__(
        self, existing_data: Optional[StructuredWorkflowSettings] = None
    ) -> None:
        super().__init__()
        self.starting_data = existing_data or {}

    @staticmethod
    def serialize_structure_to_yaml(data: StructuredWorkflowSettings) -> str:
        with io.StringIO() as file_handle:
            yaml.dump(
                dict(sorted(data.items())),
                file_handle,
                Dumper=IndentedYAMLDumper,
            )
            return file_handle.getvalue()

    @staticmethod
    def structure_workflow_data(
        settings: SettingsData,
    ) -> List[WorkflowSettingsNameValuePair]:
        return [
            {"name": key, "value": value} for key, value in settings.items()
        ]

    def serialize(self, workflow: Workflow, settings: SettingsData) -> str:
        data: StructuredWorkflowSettings = self.starting_data.copy()
        workflow_name = workflow.name if workflow.name is not None else ""
        if workflow_name in data:
            del data[workflow_name]
        data[workflow_name] = self.structure_workflow_data(settings)
        return self.serialize_structure_to_yaml(data)


class WorkflowSettingsYamlExporter(
    AbsYamlConfigFileManager, AbsWorkflowSettingsExporter
):
    """Workflow settings yaml exporter."""

    def __init__(
        self,
        yaml_file: str,
        yaml_serialization_strategy: Optional[AbsSettingsSerializer] = None,
    ) -> None:
        """Create a new WorkflowSettingsYamlExporter object."""
        super().__init__(yaml_file)
        self.yaml_serialization_strategy = yaml_serialization_strategy

    @staticmethod
    def write_data_to_file(data: str, file_name: str) -> None:
        """Write data to file."""
        with open(file_name, "w", encoding="utf-8") as file_handle:
            file_handle.write(data)

    def get_existing_data(self) -> StructuredWorkflowSettings:
        """Get existing data."""
        if os.path.exists(self.yaml_file):
            with open(self.yaml_file, "r", encoding="utf-8") as handle:
                return yaml.load(handle, Loader=yaml.SafeLoader)
        return {}

    def _get_serializer(self) -> AbsSettingsSerializer:
        if self.yaml_serialization_strategy is not None:
            return self.yaml_serialization_strategy
        return SettingsYamlSerializer(self.get_existing_data())

    def serialize_settings_data(
        self, workflow: Workflow, settings: SettingsData
    ) -> str:
        """Serialize settings data."""
        return self._get_serializer().serialize(workflow, settings)

    def save(self, workflow: Workflow, settings: SettingsData) -> None:
        """Save file."""
        self.write_data_to_file(
            data=self.serialize_settings_data(workflow, settings),
            file_name=self.yaml_file,
        )


class WorkflowSettingsManager(AbsWorkflowSettingsManager):
    """Workflow Settings Manager."""

    def __init__(
        self,
        getter_strategy: Optional[AbsWorkflowSettingsResolver] = None,
        setter_strategy: Optional[AbsWorkflowSettingsExporter] = None,
    ) -> None:
        """Create a new WorkflowSettingsManager object."""
        super().__init__()
        self.settings_getter_strategy: AbsWorkflowSettingsResolver = (
            getter_strategy
            or WorkflowSettingsYAMLResolver(self._get_yaml_file())
        )
        self.settings_saver_strategy: AbsWorkflowSettingsExporter = (
            setter_strategy
            or WorkflowSettingsYamlExporter(self._get_yaml_file())
        )

    @staticmethod
    def _get_yaml_file() -> str:
        return os.path.join(
            StandardConfigFileLocator().get_app_data_dir(),
            WORKFLOWS_SETTINGS_YML_FILE_NAME,
        )

    def get_workflow_settings(self, workflow: Workflow) -> SettingsData:
        """Get workflow settings for the workflow."""
        return self.settings_getter_strategy.get_response(workflow)

    def save_workflow_settings(
        self, workflow: Workflow, settings: SettingsData
    ) -> None:
        """Save workflow settings."""
        self.settings_saver_strategy.save(workflow, settings)


class YAMLWorkflowConfigBackend(AbsWorkflowBackend):
    """Yaml based config backend."""

    def __init__(self) -> None:
        """Create a new object."""
        super().__init__()
        self.yaml_file: Optional[str] = None
        self.settings_resolver: Optional[AbsWorkflowSettingsResolver] = None

    def get_yaml_strategy(self) -> AbsWorkflowSettingsResolver:
        """Get current yaml strategy."""
        if self.settings_resolver is not None:
            return self.settings_resolver
        if self.yaml_file is None:
            raise AttributeError("yaml_file not set")
        return WorkflowSettingsYAMLResolver(self.yaml_file)

    def get(self, key: str) -> Optional[SettingsDataType]:
        """Get value for key."""
        if self.yaml_file is None or self.workflow is None:
            return None
        return self.get_yaml_strategy().get_response(self.workflow).get(key)


def get_config_backend() -> AbsWorkflowBackend:
    """Get config backend."""
    config_backend = YAMLWorkflowConfigBackend()
    config_strategy = StandardConfigFileLocator()
    backend_yaml = os.path.join(
        config_strategy.get_app_data_dir(), WORKFLOWS_SETTINGS_YML_FILE_NAME
    )
    config_backend.yaml_file = backend_yaml
    return config_backend
