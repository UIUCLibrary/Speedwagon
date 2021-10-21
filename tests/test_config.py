from unittest.mock import mock_open, patch
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
