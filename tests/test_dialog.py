from PyQt5 import QtWidgets

from speedwagon.dialog import dialogs


def test_about_dialog_box(qtbot, monkeypatch):
    def mock_about(parent, title, message):
        assert "Speedwagon" in message

    with monkeypatch.context() as mp:
        mp.setattr(QtWidgets.QMessageBox, "about", mock_about)
        dialogs.about_dialog_box(None)