import configparser
import os
import pathlib
import platform
import shutil

import speedwagon.config
import pytest

from speedwagon.models import SettingsModel
from speedwagon.job import all_required_workflow_keys


class MockConfig(speedwagon.config.AbsConfig):
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

    with speedwagon.config.ConfigManager(config_file) as cfg:
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

    my_model = speedwagon.config.SettingsModel()
    for k, v in original_settings.items():
        my_model.add_setting(k, v)

    # Serialize the model to ini file format
    data = speedwagon.config.serialize_settings_model(my_model)
    assert data is not None

    # Check that the new data is the same as original
    new_config = configparser.ConfigParser()
    new_config.read_string(data)
    assert "GLOBAL" in new_config

    for k, v in original_settings.items():
        assert new_config["GLOBAL"][k] == v


@pytest.mark.skipif(platform.system() == "Windows",
                    reason="Test for unix file systems only")
def test_nix_get_app_data_directory(monkeypatch):
    speedwagon_config = speedwagon.config.NixConfig()
    user_path = os.path.join(os.sep, "Users", "someuser")
    monkeypatch.setattr(
        pathlib.Path,
        "home",
        lambda *args, **kwargs: pathlib.Path(user_path)
    )
    assert speedwagon_config.get_app_data_directory() == os.path.join(
        user_path, ".config", "Speedwagon")


@pytest.mark.skipif(platform.system() == "Windows",
                    reason="Test for unix file systems only")
def test_nix_get_user_data_directory(monkeypatch):
    speedwagon_config = speedwagon.config.NixConfig()
    user_path = os.path.join(os.sep, "Users", "someuser")
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
        speedwagon_config.get_app_data_directory()


def test_windows_get_user_data_directory(monkeypatch):
    speedwagon_config = speedwagon.config.WindowsConfig()
    app_data_local = os.path.join('C:', 'Users', 'someuser', 'AppData', 'Local')
    monkeypatch.setattr(
        pathlib.Path,
        "home",
        lambda *args, **kwargs: pathlib.Path(app_data_local)
    )
    assert speedwagon_config.get_user_data_directory() == os.path.join(app_data_local, "Speedwagon", "data")


@pytest.fixture()
def default_config_file(tmpdir, monkeypatch):
    # =========================================================================
    # Patch for unix systems. Otherwise if the uid is missing this will fail,
    #   such as in a CI
    #
    def mocked_get_user_data_directory(*args, **kwargs):
        data_dir = tmpdir / "data"
        data_dir.ensure()
        return str(data_dir)

    monkeypatch.setattr(
        speedwagon.config.NixConfig,
        "get_user_data_directory",
        mocked_get_user_data_directory
    )
    # =========================================================================
    config_file = os.path.join(str(tmpdir), "config.ini")
    speedwagon.config.generate_default(str(config_file))
    return config_file


def test_generate_default_creates_file(default_config_file):
    assert os.path.exists(default_config_file)


@pytest.mark.parametrize("expected_key", all_required_workflow_keys())
def test_generate_default_contains_workflow_keys(default_config_file,
                                                 expected_key):
    config_data = configparser.ConfigParser()
    config_data.read(default_config_file)
    global_settings = config_data['GLOBAL']
    assert expected_key in global_settings


def test_generate_default_contains_global(default_config_file):
    config_data = configparser.ConfigParser()
    config_data.read(default_config_file)
    assert "GLOBAL" in config_data


def test_build_setting_model_missing_file(tmpdir):
    dummy = str(os.path.join(tmpdir, "config.ini"))
    with pytest.raises(FileNotFoundError):
        speedwagon.config.build_setting_model(dummy)


def test_build_setting_model(tmpdir):
    dummy = str(os.path.join(tmpdir, "config.ini"))
    empty_config_data = """[GLOBAL]
debug: False
        """
    with open(dummy, "w") as wf:
        wf.write(empty_config_data)
    model = speedwagon.config.build_setting_model(dummy)
    assert isinstance(model, SettingsModel)

    assert model is not None


def test_find_missing_configs(tmpdir):
    config_file = str(os.path.join(tmpdir, "config.ini"))
    speedwagon.config.generate_default(config_file)
    keys_that_dont_exist = {"spam", "bacon", "eggs"}

    missing_keys = speedwagon.config.find_missing_global_entries(
        config_file=config_file,
        expected_keys=keys_that_dont_exist
    )
    assert missing_keys == keys_that_dont_exist


def test_find_no_missing_configs(tmpdir):
    config_file = str(os.path.join(tmpdir, "config.ini"))
    speedwagon.config.generate_default(config_file)
    keys_that_exist = {"spam", "bacon", "eggs"}
    with open(config_file, "a+") as wf:
        for k in keys_that_exist:
            wf.write(f"{k}=\n")

    missing_keys = speedwagon.config.find_missing_global_entries(
        config_file=config_file,
        expected_keys=keys_that_exist
    )
    assert missing_keys is None


def test_add_empty_keys_if_missing(tmpdir):
    config_file = str(os.path.join(tmpdir, "config.ini"))
    speedwagon.config.generate_default(config_file)
    keys_that_dont_exist = {"spam", "bacon"}
    keys_that_exist = {"eggs"}
    with open(config_file, "a+") as wf:
        for k in keys_that_exist:
            wf.write(f"{k}=somedata\n")

    added_keys = speedwagon.config.ensure_keys(
        config_file=config_file,
        keys=keys_that_exist.union(keys_that_dont_exist)
    )

    assert added_keys == keys_that_dont_exist

    missing_keys = speedwagon.config.find_missing_global_entries(
        config_file=config_file,
        expected_keys=keys_that_exist.union(keys_that_dont_exist)
    )
    assert missing_keys is None
