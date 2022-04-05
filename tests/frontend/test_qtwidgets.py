from unittest.mock import MagicMock, Mock

from speedwagon.frontend import qtwidgets, interaction
from speedwagon.workflows import title_page_selection


class TestQtWidgetPackageBrowserWidget:
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
