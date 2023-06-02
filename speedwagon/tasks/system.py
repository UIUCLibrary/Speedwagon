"""System tasks."""

import abc
import os

import speedwagon
from speedwagon.workflows.workflow_ocr import OCRWorkflow


class AbsSystemTask(abc.ABC):
    """Abstract base class for creating system tasks."""

    @abc.abstractmethod
    def run(self) -> None:
        """Run a startup task."""

    @abc.abstractmethod
    def description(self) -> str:
        """Get human-readable information about current task."""


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

    def run(self) -> None:
        """Run a startup task."""
        yaml_file = self.get_config_file()

        getter_strategy = speedwagon.config.WorkflowSettingsYAMLResolver(
            yaml_file
        )

        setter_strategy = speedwagon.config.WorkflowSettingsYamlExporter(
            yaml_file
        )

        manager = speedwagon.config.WorkflowSettingsManager(
            getter_strategy=getter_strategy,
            setter_strategy=setter_strategy
        )

        workflow_settings: speedwagon.config.SettingsData = {}
        ocr_workflow = OCRWorkflow()
        ocr_existing_options = manager.get_workflow_settings(ocr_workflow)
        if 'Tesseract data file location' not in ocr_existing_options:
            workflow_settings['Tesseract data file location'] = \
                self.default_tesseract_data_path()
        if workflow_settings:
            manager.save_workflow_settings(ocr_workflow, workflow_settings)

    @staticmethod
    def default_tesseract_data_path() -> str:
        """Get the default path to tessdata files."""
        return os.path.join(
            speedwagon.config.StandardConfigFileLocator().get_user_data_dir(),
            "tessdata"
        )


class EnsureGlobalConfigFiles(AbsSystemTask):
    """Task to ensure all global config files are located on system."""

    def __init__(self, logger) -> None:
        """Create a new EnsureGlobalConfigFiles object.

        Args:
            logger: Used to report files being created.
        """
        super().__init__()
        self.logger = logger

    def run(self) -> None:
        """Run the ensure settings files task."""
        speedwagon.config.config.ensure_settings_files(logger=self.logger)

    def description(self) -> str:
        """Get human-readable information about current task."""
        return (
            "Ensuring global settings files are available and creating "
            "defaults where missing."
        )
