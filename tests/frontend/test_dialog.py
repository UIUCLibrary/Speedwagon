import pytest
from unittest.mock import Mock, patch, mock_open
import sys
if sys.version_info >= (3, 10):
    from importlib import metadata
else:
    import importlib_metadata as metadata

import speedwagon.info

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QtCore = pytest.importorskip("PySide6.QtCore")

from speedwagon.frontend.qtwidgets.dialog import dialogs
from speedwagon.frontend.qtwidgets.models import ItemTableModel


def test_about_dialog_box(qtbot, monkeypatch):
    fake_metadata = {"Summary": "A collection of tools", "Version": "1.1"}

    def mock_about(parent, title, message):
        assert (
            fake_metadata["Version"] in message
            and fake_metadata["Summary"] in message
        )

    def mock_metadata(*args, **kwargs):
        return fake_metadata

    with monkeypatch.context() as mp:
        mp.setattr(QtWidgets.QMessageBox, "about", mock_about)
        mp.setattr(metadata, "metadata", mock_metadata)
        dialogs.about_dialog_box(None)


def test_about_dialog_box_no_metadata(qtbot, monkeypatch):
    def mock_about(parent, title, message):
        assert "Speedwagon" == message

    def mock_metadata(*args, **kwargs):
        raise metadata.PackageNotFoundError()

    with monkeypatch.context() as mp:
        mp.setattr(QtWidgets.QMessageBox, "about", mock_about)
        mp.setattr(metadata, "metadata", mock_metadata)
        dialogs.about_dialog_box(None)


class TestSpeedwagonUnhandledExceptionDialog:
    def test_dialog(self, qtbot):
        dialog = dialogs.SpeedwagonExceptionDialog()
        dialog.exception = ValueError("This is wrong")
        assert dialog.informativeText() == "This is wrong"

    def test_export_button(self, qtbot, monkeypatch):
        dialog = dialogs.SpeedwagonExceptionDialog()
        qtbot.addWidget(dialog)
        dialog.exception = ValueError("This is wrong")
        assert any(
            button.text() == "Export Details" for button in dialog.buttons()
        )

    def test_export_report(self, qtbot, monkeypatch):
        exec_window = Mock()
        dialog = dialogs.SpeedwagonExceptionDialog()
        dialog.save_report_strategy = Mock(name="save_report_strategy")
        qtbot.addWidget(dialog)
        monkeypatch.setattr(dialogs.QtWidgets.QMessageBox, "exec", exec_window)

        qtbot.mouseClick(dialog.export_button, QtCore.Qt.LeftButton)
        assert dialog.save_report_strategy.save.called is True

    def test_exception_property(self, qtbot):
        exception = ValueError("This is wrong")
        dialog = dialogs.SpeedwagonExceptionDialog()
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
            lambda *_, **__: ("bacon.txt", True),
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
            lambda *_, **__: (None, False),
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
            dialogs.QtWidgets.QFileDialog, "getSaveFileName", getSaveFileName
        )
        saver.save("spam")
        assert write_data.call_count == 2

    def test_write_data(self, qtbot, monkeypatch):
        saver = dialogs.SaveReportDialogBox()
        with patch("builtins.open", mock_open()) as mocked_file:
            result = saver.write_data("output.txt", "spam")
            mocked_file().write.assert_called_once_with("spam")
        assert result is True

    def test_write_data_failed_returns_false(self, qtbot, monkeypatch):
        saver = dialogs.SaveReportDialogBox()
        mock_open_data = mock_open()
        mock_open_data.side_effect = IOError("Failed")
        message_box = Mock(name="QMessageBox")
        monkeypatch.setattr(dialogs.QtWidgets, "QMessageBox", message_box)
        with patch("builtins.open", mock_open_data):
            result = saver.write_data("output.txt", "spam")
        assert result is False


class TestSystemInfoDialog:

    def test_export_calls_get_export_file_path(self, qtbot):
        system_info = Mock(
            spec=speedwagon.info.SystemInfo,
            get_installed_packages=Mock(return_value=[]),
        )
        dialog_box = dialogs.SystemInfoDialog(system_info)
        dialog_box.request_export_system_information = Mock()
        dialog_box.export_to_file_button.click()
        dialog_box.request_export_system_information.assert_called_once()

    def test_get_export_file_path(self, qtbot):
        system_info = Mock(
            spec=speedwagon.info.SystemInfo,
            get_installed_packages=Mock(return_value=[]),
        )
        dialog_box = dialogs.SystemInfoDialog(system_info)

        def save_dialog_box(*args, **kwargs):
            return "file.txt", "Text (*.txt)"

        with qtbot.waitSignal(dialog_box.export_to_file) as blocker:
            dialog_box.request_export_system_information(
                save_dialog_box=save_dialog_box
            )

        assert blocker.signal_triggered

    def test_get_export_file_path_cancel(self, qtbot):
        system_info = Mock(
            spec=speedwagon.info.SystemInfo,
            get_installed_packages=Mock(return_value=[]),
        )
        dialog_box = dialogs.SystemInfoDialog(system_info)

        def save_dialog_box_gets_canceled(*args, **kwargs):
            return None, None

        with qtbot.assertNotEmitted(dialog_box.export_to_file):
            dialog_box.request_export_system_information(
                save_dialog_box=save_dialog_box_gets_canceled
            )


class TestItemView:
    @pytest.fixture()
    def model(self):
        m = ItemTableModel(keys=["one", "two"])
        m.add_item(("1", "2"))
        m.display_role = lambda row, index: row[index.column()]
        return m

    @pytest.mark.parametrize(
        "column, expected",
        [
            (1, True),
            (0, False),
        ],
    )
    def test_opens_delegate_if_rule_is_valid(
        self, qtbot, model, column, expected
    ):
        view = dialogs.ItemView()
        view.setModel(model)

        def rule(item, index):
            return index.column() == 1

        model.is_editable_rule = rule

        index = model.index(0, column)
        # simulate the click into the view point.
        # else it won't work for testing
        qtbot.mouseClick(
            view.viewport(),
            QtCore.Qt.LeftButton,
            pos=view.visualRect(index).center(),
        )
        qtbot.mouseDClick(
            view.viewport(),
            QtCore.Qt.LeftButton,
            pos=view.visualRect(index).center(),
        )
        assert (
            type(view.indexWidget(view.currentIndex()))
            == dialogs.ItemSelectOptionDelegate.delegate_klass
        ) is expected


class TestTableEditDialog:

    @pytest.fixture()
    def model(self):
        m = ItemTableModel(keys=["one", "two"])
        m.add_item(("1", "2"))
        m.display_role = lambda row, index: row[index.column()]
        return m

    def test_accepted(self, qtbot, model):
        dialog = dialogs.TableEditDialog(model=model)
        with qtbot.waitSignal(dialog.accepted):
            dialog.ok_button.click()

    def test_data_get_from_model(self, qtbot, model):
        return_data = "some_data"
        model.results = Mock(return_value=return_data)
        dialog = dialogs.TableEditDialog(model=model)
        assert dialog.data() == return_data
