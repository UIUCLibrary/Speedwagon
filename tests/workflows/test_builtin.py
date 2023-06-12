from unittest.mock import Mock

import pytest

from speedwagon.workflows import builtin
import speedwagon

class TestEnsureBuiltinWorkflowConfigFiles:
    @pytest.fixture
    def task(self, monkeypatch):
        new_task = builtin.EnsureBuiltinWorkflowConfigFiles()
        monkeypatch.setattr(new_task, "get_config_file", lambda : "")
        return new_task

    def test_has_description(self, task):
        assert task.description()

    def test_get_settings_manager(self, task):
        manager = task.get_settings_manager()
        assert isinstance(
            manager,
            speedwagon.config.workflow.AbsWorkflowSettingsManager
        )
    def test_run_save_workflow_settings(self, task, monkeypatch):
        manager = Mock(
            name='settings_manager',
            get_workflow_settings=Mock(name='get_workflow_settings', return_value={})
        )
        monkeypatch.setattr(builtin.EnsureBuiltinWorkflowConfigFiles, "default_tesseract_data_path", lambda *args: ".")

        task.get_settings_manager = \
            Mock(return_value=manager)
        task.run()
        manager.save_workflow_settings.assert_called_once()