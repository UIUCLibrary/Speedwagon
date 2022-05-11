from unittest.mock import MagicMock, Mock

import pytest
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QtCore = pytest.importorskip("PySide6.QtCore")

# from PySide6 import QtWidgets, QtCore

import speedwagon
import speedwagon.exceptions
from speedwagon.frontend import qtwidgets, interaction
from speedwagon.frontend.qtwidgets.dialog import title_page_selection


class TestQtWidgetPackageBrowserWidget:
    def test_get_user_response_invalid_file_format_raises(
            self,
            qtbot,
            monkeypatch
    ):
        package_widget = \
            qtwidgets.user_interaction.QtWidgetPackageBrowserWidget(None)

        with pytest.raises(KeyError) as error:
            package_widget.get_user_response(
                options={
                    'input': "somepath",
                    "Image File Type": "some bonkers non-supported format"
                },
                pretask_results=[]
            )
        assert "some bonkers non-supported format" in str(error.value)

    def test_get_user_response(self, qtbot, monkeypatch):
        package_data = MagicMock()
        package_widget = \
            qtwidgets.user_interaction.QtWidgetPackageBrowserWidget(None)

        monkeypatch.setattr(
            package_widget,
            "get_packages",
            lambda root_dir, image_type: [package_data]
        )

        monkeypatch.setattr(
            package_widget,
            "get_packages",
            lambda root_dir, image_type: [package_data]
        )

        options = {
            "input": "somepath",
            "Image File Type": "TIFF"
        }
        pretask_result = []
        packages = [
            Mock()
        ]

        monkeypatch.setattr(
            package_widget,
            "get_data_with_dialog_box",
            lambda root_dir, image_type: packages
        )

        response = package_widget.get_user_response(options, pretask_result)

        assert response == {
            "packages": packages
        }

    def test_get_data_with_dialog_box(self, monkeypatch):
        package_widget = \
            qtwidgets.user_interaction.QtWidgetPackageBrowserWidget(None)

        mock_dialog_box = Mock(spec=title_page_selection.PackageBrowser)

        mock_dialog_box_type = Mock(return_value=mock_dialog_box)

        monkeypatch.setattr(
            package_widget,
            "get_packages",
            lambda root_dir, image_type: [Mock()]
        )
        package_widget.get_data_with_dialog_box(
            root_dir="somePath",
            image_type=interaction.SupportedImagePackageFormats.JP2,
            dialog_box=mock_dialog_box_type
        )
        assert mock_dialog_box_type.called is True and \
               mock_dialog_box.exec.called is True


class TestConfirmListModel:
    def test_model_check(self, qtmodeltester):
        items = [
            "./file1.txt",
            "/directory/"
        ]
        model = qtwidgets.user_interaction.ConfirmListModel(items)
        qtmodeltester.check(model)

    def test_all_data_defaults_to_checked(self):
        items = [
            "./file1.txt",
            "/directory/"
        ]
        model = qtwidgets.user_interaction.ConfirmListModel(items)
        assert model.selected() == items

    def test_unchecking_item(self):
        items = [
            "./file1.txt",
            "/directory/"
        ]
        model = qtwidgets.user_interaction.ConfirmListModel(items)

        model.setData(
            index=model.index(0),
            value=QtCore.Qt.Unchecked,
            role=QtCore.Qt.CheckStateRole
        )

        assert model.selected() == ["/directory/"]


class TestConfirmDeleteDialog:
    def test_okay_button_accepts(self, qtbot):
        items = []
        dialog_box = \
            qtwidgets.user_interaction.ConfirmDeleteDialog(items)

        okay_button = \
            dialog_box.button_box.button(QtWidgets.QDialogButtonBox.Ok)

        with qtbot.wait_signal(dialog_box.accepted):
            okay_button.setEnabled(True)
            okay_button.click()

    @pytest.mark.parametrize(
        "items, expected_enabled",
        [
            ([], False),
            ([Mock()], True)
        ]
    )
    def test_active_okay_button(self, qtbot, items, expected_enabled):
        dialog_box = \
            qtwidgets.user_interaction.ConfirmDeleteDialog(items)
        dialog_box.update_buttons()
        ok_button = \
            dialog_box.button_box.button(QtWidgets.QDialogButtonBox.Ok)
        assert ok_button.isEnabled() is expected_enabled

    def test_cancel_button_rejects(self, qtbot):
        items = []
        dialog_box = \
            qtwidgets.user_interaction.ConfirmDeleteDialog(items)

        cancel_button = \
            dialog_box.button_box.button(QtWidgets.QDialogButtonBox.Cancel)

        with qtbot.wait_signal(dialog_box.rejected):
            cancel_button.click()


class TestQtWidgetConfirmFileSystemRemoval:
    @pytest.fixture()
    def widget(self, qtbot):
        parent = QtWidgets.QWidget()
        return \
            qtwidgets.user_interaction.QtWidgetConfirmFileSystemRemoval(parent)

    def test_get_user_response(self, widget, monkeypatch):
        monkeypatch.setattr(widget, "use_dialog_box", lambda *_, **__: [
            ".DS_Store"
        ])
        result = widget.get_user_response({}, pretask_results=[MagicMock()])
        assert result == {
            "items": ['.DS_Store']
        }

    def test_use_dialog_box(self, widget):
        dialog_box = Mock(spec=qtwidgets.user_interaction.ConfirmDeleteDialog)
        dialog_box.data = Mock(return_value=[".DS_Store"])
        assert widget.use_dialog_box(
            [".DS_Store"],
            dialog_box=Mock(return_value=dialog_box)
        ) == [".DS_Store"]

    def test_use_dialog_box_abort_throw_cancel_job(self, widget):
        dialog_box = Mock(spec=qtwidgets.user_interaction.ConfirmDeleteDialog)
        dialog_box.data = Mock(return_value=[".DS_Store"])
        dialog_box.exec = Mock(return_value=QtWidgets.QDialog.Rejected)

        with pytest.raises(speedwagon.exceptions.JobCancelled):
            widget.use_dialog_box(
                [".DS_Store"],
                dialog_box=Mock(return_value=dialog_box)
            )
