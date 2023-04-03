from unittest.mock import mock_open, patch, Mock

import pytest

import speedwagon.config


class TestConfigLoader:
    def test_loads_from_setting_file(self):
        data = """[GLOBAL]
tessdata = /usr/home/data/tessdata
starting-tab = Tools
debug = True
getmarc_server_url = http://127.0.0.1:5000/
        """
        with patch('configparser.open', mock_open(read_data=data)) as m:
            config_file = "config.ini"
            loader = speedwagon.config.ConfigLoader(config_file)
            loader.resolution_strategy_order = [
                speedwagon.config.DefaultsSetter(),
                speedwagon.config.ConfigFileSetter(config_file),
                speedwagon.config.CliArgsSetter(args=[]),
            ]
            result = loader.get_settings()
            assert result['debug'] is True

    def test_cli_overrides_setting_file(self):
        data = """[GLOBAL]
tessdata = /usr/home/data/tessdata
starting-tab = Tools
debug = False
getmarc_server_url = http://127.0.0.1:5000/
        """
        with patch('configparser.open', mock_open(read_data=data)) as m:
            config_file = "config.ini"
            loader = speedwagon.config.ConfigLoader(config_file)
            loader.resolution_strategy_order = [
                speedwagon.config.DefaultsSetter(),
                speedwagon.config.ConfigFileSetter(config_file),
                speedwagon.config.CliArgsSetter(args=['--debug']),
            ]
            result = loader.get_settings()
            assert result['debug'] is True

    @pytest.fixture
    def sample_config_data_with_plugins(self):
        data = """[GLOBAL]
tessdata = /usr/home/data/tessdata
starting-tab = Tools
debug = False
getmarc_server_url = http://127.0.0.1:5000/

[PLUGINS.mysampleplugin]
myworkflow = True

[PLUGINS.myotherplugin]
variation1 = True
variation2 = True
"""
        return data
    def test_read_plugins(self, sample_config_data_with_plugins):
        with patch(
                'configparser.open',
                mock_open(read_data=sample_config_data_with_plugins)
        ):
            config_file = "config.ini"
            plugins = speedwagon.config.ConfigLoader.read_settings_file_plugins(
                config_file
            )
            expected_plugins = ['mysampleplugin', 'myotherplugin']
            assert all(
                plugin_name in plugins for plugin_name in expected_plugins
            )
    def test_read_plugins_workflows(self, sample_config_data_with_plugins):
        with patch(
                'configparser.open',
                mock_open(read_data=sample_config_data_with_plugins)
        ):
            config_file = "config.ini"
            plugins = \
                speedwagon.config.ConfigLoader.read_settings_file_plugins(
                    config_file
                )
            assert "myworkflow" in plugins['mysampleplugin']


class TestStandardConfig:
    def test_settings_returns_a_dict(self):
        config_strategy = speedwagon.config.StandardConfig()
        config_strategy.config_loader_strategy = Mock(get_settings=Mock(return_value={}))
        assert isinstance(config_strategy.settings(), dict)

    def test_resolution_order(self):
        config_strategy = speedwagon.config.StandardConfig()
        config_loader_strategy = speedwagon.config.ConfigLoader("")
        config_loader_strategy.resolution_strategy_order = [
            Mock(update=Mock(return_value={"debug": True}))
        ]
        config_strategy.config_loader_strategy = config_loader_strategy
        assert config_strategy.settings()['debug'] is True


class TestAbsSetting:
    def test_raises_if_init_without_friendly_name(self):

        with pytest.raises(Exception):
            class Incomplete(speedwagon.config.AbsSetting):
                pass
            Incomplete()
