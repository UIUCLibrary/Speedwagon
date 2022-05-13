import pytest
from unittest.mock import Mock
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

try:
    from importlib import metadata
    from importlib.metadata import PackageNotFoundError
except ImportError:
    import importlib_metadata as metadata  # type: ignore
    from importlib_metadata import PackageNotFoundError

from speedwagon.frontend.qtwidgets.dialog import dialogs


def test_about_dialog_box(qtbot, monkeypatch):
    fake_metadata = {
        "Summary": "A collection of tools",
        "Version": "1.1"
    }

    def mock_about(parent, title, message):
        assert fake_metadata['Version'] in message and fake_metadata['Summary'] in message

    def mock_metadata(*args, **kwargs):
        return fake_metadata

    with monkeypatch.context() as mp:
        mp.setattr(QtWidgets.QMessageBox, "about", mock_about)
        mp.setattr(metadata, "metadata", mock_metadata)
        dialogs.about_dialog_box(None)


def test_about_dialog_box_no_metadata(qtbot, monkeypatch):
    def mock_about(parent, title, message):
        assert 'Speedwagon' == message

    def mock_metadata(*args, **kwargs):
        raise PackageNotFoundError()

    with monkeypatch.context() as mp:
        mp.setattr(QtWidgets.QMessageBox, "about", mock_about)
        mp.setattr(metadata, "metadata", mock_metadata)
        dialogs.about_dialog_box(None)


def test_get_install_packages(monkeypatch):

    def mock_distributions(*args, **kwargs):
        fake_distributions = [
            {
                "Name": 'Spam',
                "Version": '1.0',
            },
            {
                "Name": 'Bacon',
                "Version": '1.1',
            },
            {
                "Name": 'Eggs',
                "Version": '0.1',
            }
        ]
        return [Mock(metadata=d) for d in fake_distributions]

    with monkeypatch.context() as ctx:
        ctx.setattr(metadata, "distributions", mock_distributions)
        assert dialogs.SystemInfoDialog.get_installed_packages() == [
            'Bacon 1.1',
            'Eggs 0.1',
            'Spam 1.0',
        ]
