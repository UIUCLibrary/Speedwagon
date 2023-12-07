import os

import pytest

from speedwagon import utils
import pathlib


def test_get_desktop_path_finds_valid(monkeypatch):
    fake_home = os.path.join("usr", "home")
    monkeypatch.setattr(
        pathlib.Path, "home", lambda: pathlib.Path(fake_home)
    )

    def exists(path):
        return str(path) == os.path.join(fake_home, "Desktop")

    monkeypatch.setattr(os.path, "exists", exists)
    assert utils.get_desktop_path()


def test_get_desktop_path_not_found_throws(monkeypatch):
    fake_home = os.path.join("usr", "home")

    monkeypatch.setattr(
        pathlib.Path, "home", lambda: pathlib.Path(fake_home)
    )

    monkeypatch.setattr(os.path, "exists", lambda _: False)
    with pytest.raises(FileNotFoundError):
        utils.get_desktop_path()
