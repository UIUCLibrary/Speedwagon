import os

from speedwagon import startup
from speedwagon.config import AbsConfig
import pytest


class MockConfig(AbsConfig):
        def __init__(self):
            self.user_data_dir = ""
            self.app_data_dir = ""

        def get_user_data_directory(self) -> str:
            return self.user_data_dir

        def get_app_data_directory(self) -> str:
            return self.app_data_dir


@pytest.fixture(scope="module")
def dummy_config(tmpdir_factory):
    root_dir = tmpdir_factory.mktemp("settings")
    dummy = MockConfig()
    dummy.user_data_dir = os.path.join(root_dir, "user_data_dir")
    dummy.app_data_dir = os.path.join(root_dir, "app_data_dir")
    return dummy


def test_get_config(dummy_config):
    config = startup.get_config(dummy_config)
    print(config)
    pass
