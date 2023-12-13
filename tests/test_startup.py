import argparse
import os.path

from unittest.mock import Mock, MagicMock, mock_open, patch

import logging
import os
import importlib
import yaml
import pytest

import speedwagon.exceptions
import speedwagon.startup
import speedwagon.config
import speedwagon.job
import speedwagon.runner_strategies


def test_version_exits_after_being_called(monkeypatch):

    parser = speedwagon.config.config.CliArgsSetter.get_arg_parser()
    version_exit_mock = Mock()

    with monkeypatch.context() as m:
        m.setattr(argparse.ArgumentParser, "exit", version_exit_mock)
        parser.parse_args(["--version"])

    version_exit_mock.assert_called()


@pytest.mark.skip("This might be changing")
def test_start_up_calls_default(monkeypatch):
    StartupDefault_ = MagicMock()
    monkeypatch.setattr(speedwagon.startup, "StartupDefault", StartupDefault_)
    with pytest.raises(SystemExit):
        speedwagon.startup.main()
        StartupDefault_.assert_called()


def test_load_as_module(monkeypatch):

    monkeypatch.setattr(logging, "getLogger", Mock())
    import speedwagon.__main__
    main_mock = Mock()
    monkeypatch.setattr(speedwagon.startup, "main", main_mock)
    speedwagon.__main__.main()
    assert main_mock.called is True


def test_load_module_self_test(monkeypatch):
    monkeypatch.setattr(logging, "getLogger", Mock())

    pytest_mock = MagicMock()
    monkeypatch.setattr(importlib, "import_module", lambda x: pytest_mock)
    import speedwagon.__main__

    with pytest.raises(SystemExit):
        speedwagon.__main__.main(["_", "--pytest"])
    assert pytest_mock.main.called is True


def test_get_custom_tabs_missing_file(capsys, monkeypatch):
    all_workflows = {
        "my workflow": Mock()
    }
    monkeypatch.setattr(speedwagon.config.tabs.CustomTabsYamlConfig, "data", Mock(side_effect=FileNotFoundError))
    list(speedwagon.startup.get_custom_tabs(all_workflows, "not_a_real_file"))
    captured = capsys.readouterr()
    assert "file not found" in captured.err


def test_missing_workflow(monkeypatch, capsys):
    test_file = "test.yml"
    monkeypatch.setattr(os.path, "exists", lambda x: x == test_file)

    # These workflows are not valid
    tabs_config_data = {
        "my workflow": [
            "spam",
            "bacon",
            "eggs"
        ]
    }
    load = Mock(name="load", return_value=tabs_config_data)
    load.__class__ = dict
    monkeypatch.setattr(yaml, "load", load)
    def read_file(*args, **kwargs):
        return """
current:
- Medusa Preingest Curation
"""
    monkeypatch.setattr(
        speedwagon.config.tabs.TabsYamlFileReader,
        "read_file",
        read_file
    )

    list(
        speedwagon.startup.get_custom_tabs(
            {
                "my workflow": Mock()
            },
            test_file
        )
    )
    captured = capsys.readouterr()
    assert "Unable to load workflow" in captured.err


def test_get_custom_tabs_loads_workflows_from_file(monkeypatch):
    test_file = "test.yml"
    monkeypatch.setattr(os.path, "exists", lambda x: x == test_file)
    all_workflows = {
        "spam": Mock(active=True)
    }
    tabs_config_data = {
        "my workflow": [
            "spam",
        ]
    }
    load = Mock(name="load", return_value=tabs_config_data)
    monkeypatch.setattr(yaml, "load", load)
    def read_file(*args, **kwargs):
        return """
my workflow:
- spam
"""
    monkeypatch.setattr(
        speedwagon.config.tabs.TabsYamlFileReader,
        "read_file",
        read_file
    )
    with patch('speedwagon.config.open', mock_open()):
        tab_name, workflows = next(
            speedwagon.startup.get_custom_tabs(all_workflows, test_file)
        )
    assert tab_name == "my workflow" and "spam" in workflows


class TestCustomTabsFileReader:
    def test_load_custom_tabs_file_not_found(self, capsys):
        all_workflows = Mock()
        reader = speedwagon.startup.CustomTabsFileReader(all_workflows)

        def read_file():
            raise FileNotFoundError("File not found")

        tabs_config_strategy = \
            speedwagon.config.tabs.CustomTabsYamlConfig("fake_file.yml")

        tabs_config_strategy.data_reader = read_file
        all(reader.load_custom_tabs(strategy=tabs_config_strategy))
        captured = capsys.readouterr()
        assert "Custom tabs file fake_file.yml not found" in captured.err

    def test_load_custom_tabs_file_attribute_error(self, capsys):
        all_workflows = Mock()
        reader = speedwagon.startup.CustomTabsFileReader(all_workflows)

        tabs_config_strategy = \
            speedwagon.config.tabs.CustomTabsYamlConfig("fake_file")
        def read_file():
            raise AttributeError()
        tabs_config_strategy.data_reader = read_file

        all(reader.load_custom_tabs(tabs_config_strategy))
        captured = capsys.readouterr()
        assert "Custom tabs failed to load" in captured.err

    def test_load_custom_tabs_file_yaml_error(self, capsys, monkeypatch):

        all_workflows = Mock()
        reader = speedwagon.startup.CustomTabsFileReader(all_workflows)
        class YamlReader(speedwagon.config.tabs.AbsTabsYamlFileReader):
            def read_file(self, file_name) -> str:
                return ""
            def decode_tab_settings_yml_data(self, data):
                raise yaml.YAMLError()
        strategy = speedwagon.config.tabs.CustomTabsYamlConfig("fake_file")
        strategy.file_reader_strategy = YamlReader()
        all(reader.load_custom_tabs(strategy))
        captured = capsys.readouterr()
        assert "file failed to load" in captured.err

    def test_load_custom_tabs_file_error_loading_tab(self, capsys):
        all_workflows = Mock()
        reader = speedwagon.startup.CustomTabsFileReader(all_workflows)
        strategy = speedwagon.config.tabs.CustomTabsYamlConfig("fake_file")
        def read_file() -> str:
            raise TypeError()
        strategy.data_reader = read_file
        all(reader.load_custom_tabs(strategy))

        captured = capsys.readouterr()
        assert "Custom tabs failed to load" in captured.err


def test_run_command_invalid():
    with pytest.raises(ValueError) as error:
        speedwagon.startup.run_command(command_name="bad", args=Mock())
    assert "bad" in str(error.value).lower()


def test_run_command_valid(monkeypatch):
    good = Mock()
    command = Mock(return_value=good)
    monkeypatch.setattr(speedwagon.config.config.sys, "argv", ["speedwagon", "run"])
    monkeypatch.setattr(speedwagon.config.config.sys, "argv", ["speedwagon", "run"])
    monkeypatch.setattr(speedwagon.config.config.pathlib.Path, "home", lambda: "/home/dummy")
    monkeypatch.setattr(speedwagon.startup, "get_global_options", lambda: {})

    monkeypatch.setattr(
        speedwagon.config.config.WindowsConfig,
        "get_app_data_directory",
        lambda _: "c:\\Users\\dummy"
    )

    speedwagon.startup.run_command(
        command_name="good",
        args=Mock(),
        command=command
    )
    assert good.run.called is True
