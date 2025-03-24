from unittest.mock import Mock, ANY
from speedwagon.tasks import system
from speedwagon.config.config import AbsSettingLocator, AbsConfigSettings
import pytest


@pytest.mark.parametrize(
    "task, init_args",
    [
        (system.CallbackSystemTask, [Mock(name="callback")]),
        (system.EnsureGlobalConfigFiles, [Mock(name="logger")]),
    ],
)
def test_tasks_have_descriptions(task, init_args):
    assert isinstance(task(*init_args).description(), str)


class TestEnsureGlobalConfigFiles:
    def test_ensure_settings_files_called(self, monkeypatch):
        logger = Mock()
        ensure_settings_files = Mock()
        monkeypatch.setattr(
            system, "ensure_settings_files", ensure_settings_files
        )
        task = system.EnsureGlobalConfigFiles(logger)
        task.run()
        ensure_settings_files.assert_called_once()


@pytest.mark.parametrize(
    "expected_key",
    ["user_data_directory", "app_data_directory", "tab_config_file"],
)
def test_resolve_config_file_location(expected_key):
    assert expected_key in system.resolve_config_file_location(
        Mock(name="locator", spec=AbsSettingLocator)
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


class TestSystemTaskDecorator:
    @pytest.fixture
    def task_return_value(self):
        return 1

    @pytest.fixture
    def task_with_no_description(self, task_return_value):
        @system.system_task
        def my_task(config, config_file_locations):
            return task_return_value

        return my_task

    def test_task_decorator_with_no_description(
        self, task_with_no_description
    ):
        assert isinstance(task_with_no_description, system.CallbackSystemTask)

    def test_task_decorator_with_no_description_has_default_description(
        self, task_with_no_description
    ):
        assert task_with_no_description.description() == "Callback task"

    def test_task_decorator_with_no_description_return_value(
        self, task_with_no_description, task_return_value
    ):
        config = Mock()
        config_file_locator = Mock()
        assert (
            task_with_no_description(config, config_file_locator)
            == task_return_value
        )

    @pytest.fixture
    def task_description(self):
        return "My Task description"

    @pytest.fixture
    def task_with_description(self, task_return_value, task_description):
        @system.system_task(description=task_description)
        def my_task(config, config_file_locations):
            return task_return_value

        return my_task

    def test_task_decorator_with_description(self, task_with_description):
        assert isinstance(task_with_description, system.CallbackSystemTask)

    def test_task_decorator_with_description_return_value(
        self, task_with_description, task_return_value
    ):
        config = Mock()
        config_file_locator = Mock()
        assert (
            task_with_description(config, config_file_locator)
            == task_return_value
        )

    def test_task_decorator_with_description_has_description(self, task_with_description, task_description):
        assert task_with_description.description() == task_description
