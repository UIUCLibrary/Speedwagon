"""Built-in workflows."""

from __future__ import annotations
import os
import typing
from typing import Dict, Type, List
from speedwagon.tasks.system import AbsSystemTask

from speedwagon.plugin_hook import hookimpl
import speedwagon.config

from speedwagon.workflows.workflow_ocr import OCRWorkflow
if typing.TYPE_CHECKING:
    from speedwagon import Workflow

__all__ = ['registered_workflows', 'registered_initialization_tasks']


@hookimpl
def registered_workflows() -> Dict[str, Type[Workflow]]:
    """Get workflows registered to this plugin."""
    root = os.path.dirname(__file__)
    finder = speedwagon.job.WorkflowFinder(root)
    return finder.locate()


@hookimpl
def registered_initialization_tasks() -> List[AbsSystemTask]:
    """Get initializing tasks registered to this plugin."""
    return [EnsureBuiltinWorkflowConfigFiles()]


class EnsureBuiltinWorkflowConfigFiles(AbsSystemTask):
    """Ensure built in Workflow Config Files task.

    Note: This will be removed as soon as plugins replace all builtin workflows
    that require a config file.
    """

    def __init__(self) -> None:
        """Create a new EnsureBuiltinWorkflowConfigFiles object."""
        super().__init__()
        self.config_file_location_strategy = (
            speedwagon.config.StandardConfigFileLocator()
        )

    def description(self) -> str:
        """Get human-readable information about current task."""
        return "Ensure builtin workflow configs"

    def get_config_file(self):
        """Get config file path."""
        return os.path.join(
            self.config_file_location_strategy.get_app_data_dir(),
            speedwagon.config.WORKFLOWS_SETTINGS_YML_FILE_NAME,
        )

    def get_settings_manager(
            self
    ) -> speedwagon.config.workflow.AbsWorkflowSettingsManager:
        yaml_file = self.get_config_file()

        getter_strategy = \
            speedwagon.config.WorkflowSettingsYAMLResolver(yaml_file)

        setter_strategy = \
            speedwagon.config.WorkflowSettingsYamlExporter(yaml_file)

        return speedwagon.config.WorkflowSettingsManager(
            getter_strategy=getter_strategy,
            setter_strategy=setter_strategy
        )

    def run(self) -> None:
        """Run a startup task."""
