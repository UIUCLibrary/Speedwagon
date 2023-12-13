from __future__ import annotations
from typing import Optional, List, TYPE_CHECKING, Any, Dict
from unittest.mock import Mock, patch, mock_open, ANY, call

import pytest

import speedwagon.config
from yaml import YAMLError


if TYPE_CHECKING:
    from speedwagon.workflow import AbsOutputOptionDataType
    from speedwagon.config import FullSettingsData, SettingsData


class TestCustomTabsYamlConfig:
    def test_load_single_tab(self):
        def data_reader():
            return """Dummy:
- Convert HathiTrust limited view to Digital library
- Generate MARC.XML Files
- Generate OCR Files
- Make JP2
- Medusa Preingest Curation"""
        config_loader = speedwagon.config.tabs.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.data_reader = data_reader
        assert len(config_loader.data()) == 1

    def test_yaml_errors_throws_tab_load_failure(self, monkeypatch):
        def data_reader():
            return "garblygoock"

        config_loader = \
            speedwagon.config.tabs.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.data_reader = data_reader
        monkeypatch.setattr(speedwagon.config.tabs.yaml, "load", Mock(side_effect=YAMLError))
        with pytest.raises(speedwagon.exceptions.TabLoadFailure):
            config_loader.data()

    def test_file_format_error_throws_tab_load_failure(self, monkeypatch):
        def data_reader():
            return "garblygoock"

        config_loader = \
            speedwagon.config.tabs.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.data_reader = data_reader
        monkeypatch.setattr(config_loader, "decode_data", Mock(side_effect=speedwagon.exceptions.FileFormatError("Failed to parse file")))
        with pytest.raises(speedwagon.exceptions.TabLoadFailure):
            config_loader.data()

    def test_file_not_found_raises_tab_load_failure(self):
        def data_reader():
            raise FileNotFoundError

        config_loader = \
            speedwagon.config.tabs.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.data_reader = data_reader
        with pytest.raises(speedwagon.exceptions.TabLoadFailure):
            config_loader.data()

    def test_invalid_yml_data(self, monkeypatch):
        def data_reader():
            return ""

        config_loader = \
            speedwagon.config.tabs.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.data_reader = data_reader
        monkeypatch.setattr(
            speedwagon.config.tabs.yaml,
            "load",
            Mock(return_value="dummy")
        )

        with pytest.raises(speedwagon.exceptions.FileFormatError):
            config_loader.file_reader_strategy.decode_tab_settings_yml_data(
                "stuff"
            )

    def test_decode_data(self):
        config_loader = \
            speedwagon.config.tabs.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.file_reader_strategy = \
            Mock(
                speedwagon.config.tabs.AbsTabsYamlFileReader,
                name="file_reader_strategy"
            )
        config_loader.decode_data("data")
        assert config_loader.file_reader_strategy.decode_tab_settings_yml_data.called is True

    def test_save(self):
        config_loader = \
            speedwagon.config.tabs.CustomTabsYamlConfig(yaml_file="myfaketabs.yml")
        config_loader.file_writer_strategy = \
            Mock(speedwagon.config.tabs.AbsTabWriter, name="file_writer_strategy")
        config_loader.save([])
        assert config_loader.file_writer_strategy.save.called is True

    def test_load_empty_file(self):
        config_loader = \
            speedwagon.config.tabs.CustomTabsYamlConfig(yaml_file="tabs.yml")
        config_loader.file_reader_strategy.read_file = Mock(return_value="")
        assert config_loader.data() == []

class TestTabsWriteStrategy:
    def test_write_data_is_called(self, monkeypatch):
        strategy = speedwagon.config.tabs.TabsYamlWriter()
        write_data = Mock()
        monkeypatch.setattr(strategy, "write_data", write_data)
        strategy.save("fake_file.yml", [])
        assert write_data.called is True

    def test_write_data(self, monkeypatch):
        strategy = speedwagon.config.tabs.TabsYamlWriter()
        write_data = Mock()
        serialize_tabs_yaml = Mock()
        monkeypatch.setattr(strategy, "write_data", write_data)
        monkeypatch.setattr(strategy, "serialize", serialize_tabs_yaml)
        strategy.save("fake_file.yml", [("dummy", [])])
        assert write_data.called is True

    def test_serialize_tabs_yaml(self):
        strategy = speedwagon.config.tabs.TabsYamlWriter()

        tabs = [
            speedwagon.config.tabs.CustomTabData(
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
        config_manager.saver = Mock(speedwagon.config.config.AbsConfigSaver)
        config_manager.save(Mock())
        config_manager.saver.assert_not_called()

    def test_load(self):
        class FakeLoader(speedwagon.config.config.AbsConfigLoader):
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
            (0, speedwagon.config.config.DefaultsSetter),
            (1, speedwagon.config.config.ConfigFileSetter),
            (2, speedwagon.config.config.CliArgsSetter),
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
        custom_config_order = [speedwagon.config.config.DefaultsSetter()]
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
            speedwagon.config.config.MixedConfigLoader
        )

    def test_loader_strategy_set(self):
        config_manager = speedwagon.config.IniConfigManager()
        config_manager.loader = Mock(name="loader")
        assert config_manager.loader_strategy() == config_manager.loader

    def test_default_saver_strategy(self):
        config_manager = speedwagon.config.IniConfigManager()
        assert isinstance(
            config_manager.save_strategy(),
            speedwagon.config.config.IniConfigSaver
        )

    def test_save_strategy_set(self):
        config_manager = speedwagon.config.IniConfigManager()
        config_manager.saver = Mock(name="saver")
        assert config_manager.save_strategy() == config_manager.saver


class TestIniConfigSaver:
    def test_save(self, monkeypatch):
        saver_strategy = speedwagon.config.config.IniConfigSaver()
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
        class MockConfigSetter(speedwagon.config.config.AbsSetting):
            def update(self, settings: Optional[FullSettingsData] = None):
                return {
                    "GLOBAL": {
                        "starting-tab": "Dummy",
                        "debug": False,
                    }
                }

        saver_strategy = speedwagon.config.config.MixedConfigLoader()
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
        saver_strategy = speedwagon.config.config.ConfigFileSetter("config.ini")
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
        with patch('speedwagon.config.config.open', mock_open()) as mocked_file:
            speedwagon.config.config.ConfigFileSetter.read_config_data("config.ini")
            mocked_file.assert_called_once()

class TestCliArgsSetter:
    def test_update(self):
        saver_strategy = speedwagon.config.config.CliArgsSetter()
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
        monkeypatch.setattr(speedwagon.config.config.os.path, "exists", lambda path: False)
        monkeypatch.setattr(speedwagon.config.config,
            "generate_default",
            generate_default
        )

        ensure_file = speedwagon.config.config.CreateBasicMissingConfigFile()
        ensure_file.ensure_config_file("dummy.ini")
        assert generate_default.called is True

    def test_ensure_tabs_file(self, monkeypatch):
        touch = Mock()
        monkeypatch.setattr(
            speedwagon.config.config.pathlib.Path,
            "touch",
            touch
        )
        ensure_file = speedwagon.config.config.CreateBasicMissingConfigFile()
        ensure_file.ensure_tabs_file("dummy.yml")
        assert touch.called is True


class TestDefaultsSetter:
    def test_update_has_globals(self):
        setter = speedwagon.config.config.DefaultsSetter()
        results = setter.update()
        assert "GLOBAL" in results


class TestStandardConfig:
    def test_resolve_settings(self, monkeypatch):
        config_settings = speedwagon.config.StandardConfig()
        monkeypatch.setattr(
            speedwagon.config.config.CliArgsSetter,
            "update",
            Mock(name='CliArgsSetter.update', return_value={})
        )
        monkeypatch.setattr(
            speedwagon.config.config.ConfigFileSetter,
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
            Mock(speedwagon.config.config.AbsConfigLoader)

        config_settings.settings()
        assert \
            config_settings.config_loader_strategy.get_settings.called is True


class TestTabsYamlFileReader:
    def test_read_file(self):
        with patch('builtins.open', mock_open()) as mocked_file:
            speedwagon.config.tabs.TabsYamlFileReader.read_file("dummy.yml")
            mocked_file.assert_called_once()

    def test_decode_tab_settings_yml_data(self):
        reader = speedwagon.config.tabs.TabsYamlFileReader()
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


class TestAbsWorkflowSettingsManager:
    class DummyWorkflow(speedwagon.Workflow):
        name = "Dummy"

        def discover_task_metadata(self, initial_results: List[Any],
                                   additional_data: Dict[str, Any],
                                   **user_args) -> List[dict]:
            return []

        def workflow_options(self) -> List[AbsOutputOptionDataType]:
            input_path = speedwagon.workflow.DirectorySelect(
                "Some input path"
            )
            return [input_path]

    def test_get_workflow_settings(self, monkeypatch):
        class DummyResolver(speedwagon.config.workflow.AbsWorkflowSettingsResolver):
            def get_response(
                    self,
                    options: List[AbsOutputOptionDataType]
            ) -> SettingsData:
                return {
                    "Some input path": "some path"
                }

        workflow = self.DummyWorkflow()

        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            "get_app_data_dir",
            lambda *_: "."
        )
        settings_manager = speedwagon.config.WorkflowSettingsManager()
        settings_manager.settings_getter_strategy = DummyResolver()
        results = settings_manager.get_workflow_settings(workflow)
        assert "Some input path" in results


class TestWorkflowSettingsYAMLResolver:
    class BaconWorkflow(speedwagon.Workflow):
        name = "Bacon"

        def discover_task_metadata(self, initial_results: List[Any],
                                   additional_data: Dict[str, Any],
                                   **user_args) -> List[dict]:
            return []

        def workflow_options(self) -> List[AbsOutputOptionDataType]:
            input_path = speedwagon.workflow.DirectorySelect(
                "Some input path"
            )
            return [input_path]

    def test_get_config_data(self, monkeypatch):
        resolver = speedwagon.config.WorkflowSettingsYAMLResolver("workflows.yml")
        text = """
Bacon:
  - name: Some input path
    value: /home/dummy/spam
    
"""
        monkeypatch.setattr(resolver, 'read_file', lambda _: text)
        monkeypatch.setattr(speedwagon.config.config.os.path, "exists", lambda _: True)
        assert "Bacon" in resolver.get_config_data()

    def test_get_response(self, monkeypatch):

        workflow = TestWorkflowSettingsYAMLResolver.BaconWorkflow()
        resolver = \
            speedwagon.config.WorkflowSettingsYAMLResolver("workflows.yml")

        config_data = {
            "Bacon": [
                {
                    "name": "Some input path",
                    "value": "/home/dummy/spam"
                }
            ]
        }
        monkeypatch.setattr(resolver, "get_config_data", lambda: config_data)
        response = resolver.get_response(workflow)
        assert "Some input path" in response


class TestSettingsYamlSerializer:
    @pytest.fixture()
    def serializer(self):
        return speedwagon.config.workflow.SettingsYamlSerializer()

    def test_structure_workflow_data(self, serializer):
        assert serializer.structure_workflow_data(
            {'Some input path': '/home/dummy/spam'}
        ) == [
            {'name': 'Some input path', 'value': '/home/dummy/spam'}
        ]

    def test_serialize_structure_to_yaml(self, serializer):
        data = {
            'Dummy': [{'name': 'Some input path', 'value': '/home/dummy/spam'}]
        }
        assert serializer.serialize_structure_to_yaml(data) == """Dummy:
  - name: Some input path
    value: /home/dummy/spam
"""
class TestWorkflowSettingsYamlExporter:
    class DummyWorkflow(speedwagon.Workflow):
        name = "Dummy"

        def discover_task_metadata(self, initial_results: List[Any],
                                   additional_data: Dict[str, Any],
                                   **user_args) -> List[dict]:
            return []

        def workflow_options(self) -> List[AbsOutputOptionDataType]:
            input_path = speedwagon.workflow.DirectorySelect(
                "Some input path"
            )
            return [input_path]

    # class SpamWorkflow(speedwagon.Workflow):
    #     name = "Spam"
    #
    #     def discover_task_metadata(self, initial_results: List[Any],
    #                                additional_data: Dict[str, Any],
    #                                **user_args) -> List[dict]:
    #         return []
    #
    #     def configuration_options(self) -> List[AbsOutputOptionDataType]:
    #         input_path = speedwagon.workflow.DirectorySelect(
    #             "Some other path"
    #         )
    #         return [input_path]

    def test_save_calls_write_data_to_file(self):
        exporter = speedwagon.config.WorkflowSettingsYamlExporter("dummy.yml")
        def write_data_to_file(data: str, file_name: str): pass

        exporter.write_data_to_file = Mock(spec=write_data_to_file)
        workflow = TestWorkflowSettingsYamlExporter.DummyWorkflow()
        args: SettingsData = {
            "Some input path": "/home/dummy/spam"
        }
        exporter.save(workflow, args)
        assert exporter.write_data_to_file.called is True
        exporter.write_data_to_file.assert_called_once_with(ANY, "dummy.yml")

    def test_save_appending(self, monkeypatch):
        def load(file_name, Loader):
            return {
                "Spam": [
                    {"name": "Some other path", "value": "/home/dummy/spam"}
                ]
            }
        # monkeypatch.setattr(speedwagon.config.yaml, "load", load)
        exporter = speedwagon.config.WorkflowSettingsYamlExporter("dummy.yml")
        def write_data_to_file(data: str, file_name: str): pass

        exporter.write_data_to_file = Mock(spec=write_data_to_file)

        workflow = TestWorkflowSettingsYamlExporter.DummyWorkflow()
        args: SettingsData = {
            "Some input path": "/home/dummy/Bacon"
        }
        exporter.get_existing_data = Mock(return_value={
            "Spam": [
                {"name": "Some other path", "value": "/home/dummy/spam"}
            ]
        })
        exporter.save(workflow, args)
        expected_text = """Dummy:
  - name: Some input path
    value: /home/dummy/Bacon
Spam:
  - name: Some other path
    value: /home/dummy/spam
"""
        exporter.write_data_to_file.assert_any_call(expected_text, ANY)

    def test_serialize_settings_data(self):
        exporter = speedwagon.config.WorkflowSettingsYamlExporter("dummy.yml")
        expected_text = """Dummy:
  - name: Some input path
    value: /home/dummy/spam
"""
        result = exporter.serialize_settings_data(
            workflow=TestWorkflowSettingsYamlExporter.DummyWorkflow(),
            settings={
                "Some input path": "/home/dummy/spam"
            }
        )
        assert result == expected_text

    def test_write_data_to_file(self):
        mocked_open = mock_open()
        with patch('speedwagon.config.workflow.open', mocked_open) as mocked_file:
            speedwagon.config.WorkflowSettingsYamlExporter.write_data_to_file("dummy data", "workflows.yml")
            handle = mocked_file()
        handle.write.assert_called_once_with("dummy data")

class TestYAMLWorkflowConfigBackend:
    class SpamWorkflow(speedwagon.Workflow):
        name = "Spam"

        def workflow_options(self) -> List[AbsOutputOptionDataType]:
            tesseract_path = speedwagon.workflow.DirectorySelect(label="Tesseract data file location")
            tesseract_path.required = True
            return [tesseract_path]


        def discover_task_metadata(self, initial_results, additional_data, **user_args):
            return []

    def test_get(self):
        config = speedwagon.config.YAMLWorkflowConfigBackend()
        config.workflow = TestYAMLWorkflowConfigBackend.SpamWorkflow()
        config.yaml_file = "dummy.yml"
        config.settings_resolver = \
            Mock(
                name='settings_resolver',
                get_response=Mock(
                    name='get_response',
                    return_value=Mock(
                        name="get",
                        get=lambda key: {"Tesseract data file location": "/some/path"}.get(key)
                    )
                )
            )

        assert config.get("Tesseract data file location") == "/some/path"