from typing import Optional
from unittest.mock import Mock, patch, mock_open

import pytest

import speedwagon.config
from yaml import YAMLError

from speedwagon.config import FullSettingsData


class TestCustomTabsYamlConfig:
    def test_load_single_tab(self):
        def data_reader():
            return """Dummy:
- Convert HathiTrust limited view to Digital library
- Generate MARC.XML Files
- Generate OCR Files
- Make JP2
- Medusa Preingest Curation"""
        config_loader = speedwagon.config.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.data_reader = data_reader
        assert len(config_loader.data()) == 1

    def test_yaml_errors_throws_tab_load_failure(self, monkeypatch):
        def data_reader():
            return ""

        config_loader = \
            speedwagon.config.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.data_reader = data_reader
        monkeypatch.setattr(speedwagon.config.yaml, "load", Mock(side_effect=YAMLError))
        with pytest.raises(speedwagon.exceptions.TabLoadFailure):
            config_loader.data()

    def test_file_format_error_throws_tab_load_failure(self, monkeypatch):
        def data_reader():
            return ""

        config_loader = \
            speedwagon.config.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.data_reader = data_reader
        monkeypatch.setattr(config_loader, "decode_data", Mock(side_effect=speedwagon.exceptions.FileFormatError("Failed to parse file")))
        with pytest.raises(speedwagon.exceptions.TabLoadFailure):
            config_loader.data()

    def test_file_not_found_raises_tab_load_failure(self):
        def data_reader():
            raise FileNotFoundError

        config_loader = \
            speedwagon.config.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.data_reader = data_reader
        with pytest.raises(speedwagon.exceptions.TabLoadFailure):
            config_loader.data()

    def test_invalid_yml_data(self, monkeypatch):
        def data_reader():
            return ""

        config_loader = \
            speedwagon.config.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.data_reader = data_reader
        monkeypatch.setattr(
            speedwagon.config.yaml,
            "load",
            Mock(return_value="dummy")
        )

        with pytest.raises(speedwagon.exceptions.FileFormatError):
            config_loader.file_reader_strategy.decode_tab_settings_yml_data(
                "stuff"
            )

    def test_decode_data(self):
        config_loader = \
            speedwagon.config.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.file_reader_strategy = \
            Mock(
                speedwagon.config.AbsTabsYamlFileReader,
                name="file_reader_strategy"
            )
        config_loader.decode_data("data")
        assert config_loader.file_reader_strategy.decode_tab_settings_yml_data.called is True

    def test_save(self):
        config_loader = \
            speedwagon.config.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.file_writer_strategy = \
            Mock(speedwagon.config.AbsTabWriter, name="file_writer_strategy")
        config_loader.save([])
        assert config_loader.file_writer_strategy.save.called is True


class TestTabsWriteStrategy:
    def test_write_data_is_called(self, monkeypatch):
        strategy = speedwagon.config.TabsYamlWriter()
        write_data = Mock()
        monkeypatch.setattr(strategy, "write_data", write_data)
        strategy.save("fake_file.yml", [])
        assert write_data.called is True

    def test_write_data(self, monkeypatch):
        strategy = speedwagon.config.TabsYamlWriter()
        write_data = Mock()
        serialize_tabs_yaml = Mock()
        monkeypatch.setattr(strategy, "write_data", write_data)
        monkeypatch.setattr(strategy, "serialize", serialize_tabs_yaml)
        strategy.save("fake_file.yml", [("dummy", [])])
        assert write_data.called is True

    def test_serialize_tabs_yaml(self):
        strategy = speedwagon.config.TabsYamlWriter()

        tabs = [
            speedwagon.config.CustomTabData(
                "Spam",
                [
                    "Convert HathiTrust limited view to Digital library",
                    "Generate MARC.XML Files"
                ]
            )
        ]
        result = strategy.serialize(tabs)
        assert result == """Spam:
- Convert HathiTrust limited view to Digital library
- Generate MARC.XML Files
"""


class TestIniFileGlobalConfigManager:
    def test_save(self):
        test_ini_file = "sample.ini"
        config_manager = speedwagon.config.IniConfigManager()
        config_manager.config_file = test_ini_file
        config_manager.saver = Mock()
        data = {
            "GLOBAL": {
                "debug": False,
                'starting-tab': 'Dummy'
            }
        }
        config_manager.save(data)
        assert config_manager.saver.save.called is True

    def test_save_without_config_file_is_noop(self):
        config_manager = speedwagon.config.IniConfigManager()
        config_manager.saver = Mock(speedwagon.config.AbsConfigSaver)
        config_manager.save(Mock())
        config_manager.saver.assert_not_called()

    def test_load(self):
        class FakeLoader(speedwagon.config.AbsConfigLoader):
            def get_settings(self):
                return {
                    "GLOBAL": {
                        "debug": False,
                        'starting-tab': 'Dummy'
                    }
                }
        config_manager = speedwagon.config.IniConfigManager()
        config_manager.loader = FakeLoader()
        expected = {
            "GLOBAL": {'debug': False, 'starting-tab': 'Dummy'}
        }
        assert config_manager.data() == expected

    @pytest.mark.parametrize(
        "index, setter_type",
        [
            (0, speedwagon.config.DefaultsSetter),
            (1, speedwagon.config.ConfigFileSetter),
            (2, speedwagon.config.CliArgsSetter),
        ]
    )
    def test_default_get_resolution_order(self, monkeypatch, index, setter_type):
        config_manager = speedwagon.config.IniConfigManager()
        config_manager.config_file = "dummy.ini"
        assert isinstance(
            config_manager.get_resolution_order()[index],
            setter_type
        )

    def test_get_resolution_order_with_setting_value(self):
        config_manager = speedwagon.config.IniConfigManager()
        custom_config_order = [speedwagon.config.DefaultsSetter()]
        config_manager.config_resolution_order = custom_config_order
        assert config_manager.get_resolution_order() == custom_config_order

    def test_default_loader_strategy(self, monkeypatch):
        config_manager = speedwagon.config.IniConfigManager()
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            "get_config_file",
            Mock(return_value="sample.ini"))
        assert isinstance(
            config_manager.loader_strategy(),
            speedwagon.config.MixedConfigLoader
        )

    def test_loader_strategy_set(self):
        config_manager = speedwagon.config.IniConfigManager()
        config_manager.loader = Mock(name="loader")
        assert config_manager.loader_strategy() == config_manager.loader

    def test_default_saver_strategy(self):
        config_manager = speedwagon.config.IniConfigManager()
        assert isinstance(
            config_manager.save_strategy(),
            speedwagon.config.IniConfigSaver
        )

    def test_save_strategy_set(self):
        config_manager = speedwagon.config.IniConfigManager()
        config_manager.saver = Mock(name="saver")
        assert config_manager.save_strategy() == config_manager.saver


class TestIniConfigSaver:
    def test_save(self, monkeypatch):
        saver_strategy = speedwagon.config.IniConfigSaver()
        saver_strategy.write_data_to_file = Mock()
        saver_strategy.save(
            "dummy.ini",
            {
                "GLOBAL": {
                    'debug': False,
                    'starting-tab': 'Dummy'
                }
            }
        )
        expected = """[GLOBAL]
debug = False
starting-tab = Dummy

"""
        saver_strategy.write_data_to_file.assert_called_once_with(
            "dummy.ini",
            serialized_data=expected
        )


class TestConfigLoader:
    def test_load(self):
        class MockConfigSetter(speedwagon.config.AbsSetting):
            def update(self, settings: Optional[FullSettingsData] = None):
                return {
                    "GLOBAL": {
                        "starting-tab": "Dummy",
                        "debug": False,
                    }
                }

        saver_strategy = speedwagon.config.MixedConfigLoader()
        saver_strategy.resolution_strategy_order = [
            MockConfigSetter()
        ]
        assert saver_strategy.get_settings() == {
            "GLOBAL": {
                "starting-tab": "Dummy",
                "debug": False,
            }
        }


class TestConfigFileSetter:
    def test_update(self):
        saver_strategy = speedwagon.config.ConfigFileSetter("config.ini")
        fake_data = """[GLOBAL]
starting-tab = Dummy
debug = False
"""
        saver_strategy.read_config_data = Mock(return_value=fake_data)
        assert saver_strategy.update() == {
            'GLOBAL': {
                'debug': False,
                'starting-tab': 'Dummy',
            }
        }
    def test_read_config_data(self):
        with patch('speedwagon.config.open', mock_open()) as mocked_file:
            speedwagon.config.ConfigFileSetter.read_config_data("config.ini")
            mocked_file.assert_called_once()

class TestCliArgsSetter:
    def test_update(self):
        saver_strategy = speedwagon.config.CliArgsSetter()
        saver_strategy.args = ['--debug']
        result = saver_strategy.update()
        assert result == {
            'GLOBAL': {
                'debug': True,
            }
        }


class TestCreateBasicMissingConfigFile:
    def test_ensure_config_file_calls_generate_default(self, monkeypatch):
        generate_default = Mock()
        monkeypatch.setattr(
            speedwagon.config,
            "generate_default",
            generate_default
        )
        ensure_file = speedwagon.config.CreateBasicMissingConfigFile()
        ensure_file.ensure_config_file("dummy.ini")
        assert generate_default.called is True

    def test_ensure_tabs_file(self, monkeypatch):
        touch = Mock()
        monkeypatch.setattr(
            speedwagon.config.pathlib.Path,
            "touch",
            touch
        )
        ensure_file = speedwagon.config.CreateBasicMissingConfigFile()
        ensure_file.ensure_tabs_file("dummy.yml")
        assert touch.called is True


class TestDefaultsSetter:
    def test_update_has_globals(self):
        setter = speedwagon.config.DefaultsSetter()
        results = setter.update()
        assert "GLOBAL" in results


class TestStandardConfig:
    def test_resolve_settings(self, monkeypatch):
        config_settings = speedwagon.config.StandardConfig()
        monkeypatch.setattr(
            speedwagon.config.CliArgsSetter,
            "update",
            Mock(name='CliArgsSetter.update', return_value={})
        )
        monkeypatch.setattr(
            speedwagon.config.ConfigFileSetter,
            "update",
            Mock(name='ConfigFileSetter.update', return_value={})
        )
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            "get_config_file",
            Mock(name='StandardConfigFileLocator.get_config_file', return_value="foo.ini")
        )

        assert isinstance(config_settings.resolve_settings(), dict)

    def test_resolve_settings_with_config_loader_strategy_set(self):
        config_settings = speedwagon.config.StandardConfig()
        config_settings.config_loader_strategy = \
            Mock(speedwagon.config.AbsConfigLoader)

        config_settings.settings()
        assert \
            config_settings.config_loader_strategy.get_settings.called is True


class TestTabsYamlFileReader:
    def test_read_file(self):
        with patch('speedwagon.config.open', mock_open()) as mocked_file:
            speedwagon.config.TabsYamlFileReader.read_file("dummy.yml")
            mocked_file.assert_called_once()

    def test_decode_tab_settings_yml_data(self):
        reader = speedwagon.config.TabsYamlFileReader()
        sample_data = """Spam:
- Convert HathiTrust limited view to Digital library
- Generate MARC.XML Files
"""
        assert reader.decode_tab_settings_yml_data(sample_data) == {
            "Spam": [
                "Convert HathiTrust limited view to Digital library",
                "Generate MARC.XML Files"
            ]
        }