from unittest.mock import Mock, ANY
from speedwagon.tasks import system
from speedwagon.config.config import AbsSettingLocator, AbsConfigSettings
import pytest

@pytest.mark.parametrize(
    "task, init_args",
    [
        (system.CallbackSystemTask, [Mock(name="callback")]),
        (system.EnsureGlobalConfigFiles, [Mock(name="logger")]),
    ]
)
def test_tasks_have_descriptions(task, init_args):

    assert isinstance(task(*init_args).description(), str)

class TestEnsureGlobalConfigFiles:
    def test_ensure_settings_files_called(self, monkeypatch):
        logger = Mock()
        ensure_settings_files = Mock()
        monkeypatch.setattr(system, "ensure_settings_files", ensure_settings_files)
        task = system.EnsureGlobalConfigFiles(logger)
        task.run()
        ensure_settings_files.assert_called_once()
@pytest.mark.parametrize(
    "expected_key",
    [
        'user_data_directory',
        'app_data_directory',
        'tab_config_file'
    ]
)
def test_resolve_config_file_location(expected_key):
    assert expected_key in system.resolve_config_file_location(
        Mock(name='locator', spec=AbsSettingLocator)
    )

class TestCallbackSystemTask:
    def test_callback_called(self):
        callback = Mock()

        task = system.CallbackSystemTask(callback)

        config_backend = Mock(spec_set=AbsConfigSettings)
        task.set_config_backend(config_backend)

        config_file_locator = Mock(spec_set=AbsSettingLocator)
        task.set_config_file_locator(config_file_locator)

        task.run()

        callback.assert_called_once_with(config_backend, ANY)

    def test_missing_config_backend_raises(self):
        task = system.CallbackSystemTask(Mock())
        with pytest.raises(ValueError):
            task.run()
    def test_missing_config_file_locator_raises(self):
        task = system.CallbackSystemTask(Mock())
        task.set_config_backend(Mock(spec_set=AbsConfigSettings))
        with pytest.raises(ValueError):
            task.run()