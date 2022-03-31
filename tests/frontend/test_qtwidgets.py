from unittest.mock import MagicMock, Mock

from speedwagon.frontend import qtwidgets


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
