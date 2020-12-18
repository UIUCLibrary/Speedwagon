import configparser
import os
import pathlib
import shutil

import speedwagon.config
from speedwagon import config
import pytest

from speedwagon.models import SettingsModel


class MockConfig(config.AbsConfig):
        def __init__(self):

            super().__init__()
            self.user_data_dir = ""
            self.app_data_dir = ""

        def get_user_data_directory(self) -> str:
            return self.user_data_dir

        def get_app_data_directory(self) -> str:
            return self.app_data_dir


@pytest.fixture(scope="module")
def dummy_config(tmpdir_factory):
    root_dir = os.path.join(tmpdir_factory.getbasetemp(), "settings")
    os.makedirs(root_dir)
    dummy = MockConfig()
    dummy.user_data_dir = os.path.join(root_dir, "user_data_directory")
    os.mkdir(dummy.user_data_dir)

    dummy.app_data_dir = os.path.join(root_dir, "app_data_directory")
    os.mkdir(dummy.app_data_dir)

    yield dummy
    shutil.rmtree(root_dir)


def test_get_config(dummy_config):
    config = speedwagon.config.get_platform_settings(dummy_config)
    assert config is not None
    assert isinstance(config, MockConfig)


def test_get_config__getitem__(dummy_config):
    assert os.path.exists(dummy_config['user_data_directory'])
    assert os.path.exists(dummy_config['app_data_directory'])


def test_get_config__contains__(dummy_config):
    assert ("user_data_directory" in dummy_config) is True
    assert ("foo" in dummy_config) is False


def test_get_config__iter__(dummy_config):
    for i in dummy_config:
        print(i)


def test_read_settings(tmpdir):
    config_file = tmpdir.mkdir("settings").join("config.ini")

    global_settings = {
        "tessdata": "~/mytesseractdata"
    }

    with open(config_file, "w") as f:
        cfg_parser = configparser.ConfigParser()
        cfg_parser["GLOBAL"] = global_settings
        cfg_parser.write(f)

    with config.ConfigManager(config_file) as cfg:
        assert cfg.global_settings['tessdata'] == "~/mytesseractdata"

    shutil.rmtree(tmpdir)
    shortcut = os.path.join(tmpdir.dirname, "test_read_settingscurrent")
    if os.path.exists(shortcut):
        os.unlink(shortcut)


def test_serialize_settings_model():

    original_settings = {
        "tessdata": "~/mytesseractdata"
    }

    # Mock up a model
    cfg_parser = configparser.ConfigParser()
    original_settings = cfg_parser["GLOBAL"] = original_settings

    my_model = config.SettingsModel()
    for k, v in original_settings.items():
        my_model.add_setting(k, v)

    # Serialize the model to ini file format
    data = config.serialize_settings_model(my_model)
    assert data is not None

    # Check that the new data is the same as original
    new_config = configparser.ConfigParser()
    new_config.read_string(data)
    assert "GLOBAL" in new_config

    for k, v in original_settings.items():
        assert new_config["GLOBAL"][k] == v


def test_nix_get_app_data_directory(monkeypatch):
    speedwagon_config = speedwagon.config.NixConfig()
    user_path = os.path.join("/Users", "someuser")
    monkeypatch.setattr(
        pathlib.Path,
        "home",
        lambda *args, **kwargs: pathlib.Path(user_path)
    )
    assert speedwagon_config.get_app_data_directory() == os.path.join(
        user_path, ".config", "Speedwagon")


def test_nix_get_user_data_directory(monkeypatch):
    speedwagon_config = speedwagon.config.NixConfig()
    user_path = os.path.join("/Users", "someuser")
    monkeypatch.setattr(
        pathlib.Path,
        "home",
        lambda *args, **kwargs: pathlib.Path(user_path)
    )
    assert speedwagon_config.get_user_data_directory() == os.path.join(user_path, ".config", "Speedwagon", "data")


def test_windows_get_app_data_directory(monkeypatch):
    speedwagon_config = speedwagon.config.WindowsConfig()
    user_path = os.path.join('C:', 'Users', 'someuser')
    monkeypatch.setattr(
        pathlib.Path,
        "home",
        lambda *args, **kwargs: pathlib.Path(user_path)
    )
    local_app_data_path = os.path.join('C:', 'Users', 'someuser', "AppData", 'Local')
    monkeypatch.setattr(
        os,
        "getenv",
        lambda *args, **kwargs: local_app_data_path
    )
    assert speedwagon_config.get_app_data_directory() == os.path.join(local_app_data_path, "Speedwagon")


def test_windows_get_app_data_directory_no_LocalAppData(monkeypatch):
    speedwagon_config = speedwagon.config.WindowsConfig()
    monkeypatch.setattr(
        os,
        "getenv",
        lambda *args, **kwargs: None
    )
    with pytest.raises(FileNotFoundError):
        assert speedwagon_config.get_app_data_directory() == os.path.join(local_app_data_path, "Speedwagon")


def test_windows_get_user_data_directory(monkeypatch):
    speedwagon_config = speedwagon.config.WindowsConfig()
    app_data_local = os.path.join('C:', 'Users', 'someuser', 'AppData', 'Local')
    monkeypatch.setattr(
        pathlib.Path,
        "home",
        lambda *args, **kwargs: pathlib.Path(app_data_local)
    )
    assert speedwagon_config.get_user_data_directory() == os.path.join(app_data_local, "Speedwagon", "data")


def test_generate_default_creates_file(tmpdir):
     config_file = os.path.join(str(tmpdir),   "config.ini")
     config.generate_default(str(config_file))
     assert os.path.exists(config_file)


def test_build_setting_model_missing_file(tmpdir):
    dummy = str(os.path.join(tmpdir, "config.ini"))
    with pytest.raises(FileNotFoundError):
        speedwagon.config.build_setting_model(dummy)


def test_build_setting_model(tmpdir):
    dummy = str(os.path.join(tmpdir, "config.ini"))
    empty_config_data = """[GLOBAL]
        """
    with open(dummy, "w") as wf:
        wf.write(empty_config_data)
    model = speedwagon.config.build_setting_model(dummy)
    assert isinstance(model, SettingsModel)

