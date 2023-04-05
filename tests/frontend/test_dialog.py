import pytest
from unittest.mock import Mock, patch, mock_open
import builtins
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QtCore = pytest.importorskip("PySide6.QtCore")

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


class TestSpeedwagonUnhandledExceptionDialog:
    def test_dialog(self, qtbot):
        dialog = dialogs.SpeedwagonUnhandledExceptionDialog()
        dialog.exception = ValueError("This is wrong")
        assert dialog.informativeText() == "This is wrong"

    def test_export_button(self, qtbot, monkeypatch):
        dialog = dialogs.SpeedwagonUnhandledExceptionDialog()
        qtbot.addWidget(dialog)
        dialog.exception = ValueError("This is wrong")
        assert any(
            button.text() == "Export Details" for button in dialog.buttons()
        )

    def test_export_report(self, qtbot, monkeypatch):
        exec_window = Mock()
        dialog = dialogs.SpeedwagonUnhandledExceptionDialog()
        dialog.save_report_strategy = Mock(name="save_report_strategy")
        qtbot.addWidget(dialog)
        monkeypatch.setattr(dialogs.QtWidgets.QMessageBox, "exec", exec_window)

        qtbot.mouseClick(dialog.export_button, QtCore.Qt.LeftButton)
        assert dialog.save_report_strategy.save.called is True

    def test_exception_property(self, qtbot):
        exception = ValueError("This is wrong")
        dialog = dialogs.SpeedwagonUnhandledExceptionDialog()
        dialog.exception = exception
        assert dialog.exception == exception


class TestSaveReportDialogBox:
    def test_save_calls_write_data(self, qtbot, monkeypatch):
        saver = dialogs.SaveReportDialogBox()
        write_data = Mock()
        monkeypatch.setattr(saver, "write_data", write_data)
        monkeypatch.setattr(
            dialogs.QtWidgets.QFileDialog,
            "getSaveFileName",
            lambda *_, **__: ("bacon.txt", True)
        )
        saver.save("spam")
        assert write_data.called is True

    def test_save_cancels_not_calls_write_data(self, qtbot, monkeypatch):
        saver = dialogs.SaveReportDialogBox()
        write_data = Mock()
        monkeypatch.setattr(saver, "write_data", write_data)
        monkeypatch.setattr(
            dialogs.QtWidgets.QFileDialog,
            "getSaveFileName",
            lambda *_, **__: (None, False)
        )
        saver.save("spam")
        assert write_data.called is False

    def test_save_failing_tries_again(self, qtbot, monkeypatch):
        saver = dialogs.SaveReportDialogBox()

        # ======================================================================
        # simulate putting in file name that produces an error when writing.
        # When the user is prompted again for a file name, they cancel it.

        attempts = 0
        def _write_data(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            return attempts != 1

        write_data = Mock(side_effect=_write_data)
        # ======================================================================
        monkeypatch.setattr(saver, "write_data", write_data)
        getSaveFileName = Mock(return_value=("bacon.txt", True))
        monkeypatch.setattr(
            dialogs.QtWidgets.QFileDialog,
            "getSaveFileName",
            getSaveFileName
        )
        saver.save("spam")
        assert write_data.call_count == 2

    def test_write_data(self, qtbot, monkeypatch):
        saver = dialogs.SaveReportDialogBox()
        with patch('builtins.open', mock_open()) as mocked_file:
            result = saver.write_data("output.txt", "spam")
            mocked_file().write.assert_called_once_with("spam")
        assert result is True

    def test_write_data_failed_returns_false(self, qtbot, monkeypatch):
        saver = dialogs.SaveReportDialogBox()
        mock_open_data = mock_open()
        mock_open_data.side_effect = IOError("Failed")
        message_box = Mock(name="QMessageBox")
        monkeypatch.setattr(dialogs.QtWidgets, "QMessageBox", message_box)
        with patch('builtins.open', mock_open_data) as mocked_file:
            result = saver.write_data("output.txt", "spam")
        assert result is False
