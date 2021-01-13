from PyQt5 import QtWidgets
try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore

from speedwagon.dialog import dialogs


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

    with monkeypatch.context() as mp:
        mp.setattr(QtWidgets.QMessageBox, "about", mock_about)
        dialogs.about_dialog_box(None)