import configparser

from unittest.mock import Mock, patch, mock_open

import pytest

pytest.importorskip("PySide6.QtWidgets")
pytest.importorskip("PySide6.QtCore")

from speedwagon.frontend.qtwidgets import export
def test_write_workflow_settings_to_file():
     yaml_file = "yaml_file.yml"
     data = Mock(name="data")
     on_success_save_updated_settings = Mock(name="on_success_save_updated_settings", return_value="")
     serialization_strategy = Mock(
          name="serialization_strategy",
          return_value=""
     )
     with patch('speedwagon.frontend.qtwidgets.export', mock_open()):
          assert export.write_workflow_settings_to_file(
               yaml_file,
               data,
               on_success_save_updated_settings,
               serialization_strategy
          ) is True
          on_success_save_updated_settings.assert_called_once()


def test_write_plugins_config_file():
     config_file = "config.ini"
     data = Mock(name="data")
     on_success_save_updated_settings = Mock(name="on_success_save_updated_settings", return_value="")
     serialization_strategy = Mock(
          name="serialization_strategy",
          return_value=""
     )
     with patch('speedwagon.frontend.qtwidgets.export', mock_open()):
          assert export.write_plugins_config_file(
               config_file,
               data,
               on_success_save_updated_settings,
               serialization_strategy
          ) is True
          on_success_save_updated_settings.assert_called_once()

def test_write_customized_tab_data():
     yaml_file = "yaml_file.yml"
     data = Mock(name="data")
     on_success_save_updated_settings = Mock(name="on_success_save_updated_settings", return_value="")
     serialization_strategy = Mock(
          name="serialization_strategy",
          return_value=""
     )
     with patch('speedwagon.frontend.qtwidgets.export', mock_open()):
          assert export.write_customized_tab_data(
               yaml_file,
               data,
               on_success_save_updated_settings,
               serialization_strategy
          ) is True
          on_success_save_updated_settings.assert_called_once()

def test_write_global_settings_to_config_file(monkeypatch):
     data = Mock(name="data")
     on_success_save_updated_settings = Mock(name="on_success_save_updated_settings", return_value="")
     serialization_strategy = Mock(
          name="serialization_strategy",
          return_value=""
     )
     save = Mock(name="save")
     monkeypatch.setattr(export.config.IniConfigManager, "save", save)
     assert export.write_global_settings_to_config_file(
          "config.ini",
          data,
          on_success_save_updated_settings,
     ) is True
     on_success_save_updated_settings.assert_called_once()
     save.assert_called_once()

def test_serialize_workflow_settings():
     assert isinstance(
          export.serialize_workflow_settings({"my_workflow": {"spam": True}}),
          str
     )

def test_plugins_config_file_serialization(monkeypatch):
     config_file = "dummy.ini"
     data = {"plugin": []}
     read = Mock(name="read")
     monkeypatch.setattr(configparser.ConfigParser, "read", read)
     assert isinstance(
          export.plugins_config_file_serialization(
               config_file,
               data
          ),
          str
     )
     read.assert_called_once()

def test_serialize_tab_data():
     data = []
     assert isinstance(export.serialize_tab_data(data), str)

def test_write_error_returns_false():
     @export.report_write_success
     def dummy():
          raise IOError("no working")
     assert dummy() is False