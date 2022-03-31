from unittest.mock import Mock, MagicMock

import pytest
from uiucprescon.packager.packages import collection
from speedwagon.frontend import cli
import speedwagon


class TestCLIPackageBrowserWidget:
    def test_get_package_files(self):
        package_widget = cli.user_interaction.CLIPackageBrowserWidget()

        package_object = MagicMock()
        item = MagicMock()
        instance = Mock(
            spec=collection.Instantiation
        )
        instance.files = [
            "file1.jp2",
            "file2.jp2",
        ]
        item.instantiations.values.return_value = [
                instance
        ]

        package_object.__iter__.return_value = [
            item
        ]
        files = package_widget.get_package_files(package_object)
        assert files == [
            "file1.jp2",
            "file2.jp2",
        ]

    def test_ask_user_to_select_title_page(self):
        package_widget = cli.user_interaction.CLIPackageBrowserWidget()
        files = [
            "file1.jp2",
            "file2.jp2",
            "file3.jp2",
        ]
        title_page = package_widget.ask_user_to_select_title_page(
            files, strategy=lambda: 1
        )
        assert title_page == "file1.jp2"

    def test_ask_user_to_select_title_cancels(self):
        package_widget = cli.user_interaction.CLIPackageBrowserWidget()
        files = [
            "file1.jp2",
            "file2.jp2",
            "file3.jp2",
        ]

        def user_hits_control_c():
            raise KeyboardInterrupt()

        with pytest.raises(speedwagon.JobCancelled):
            package_widget.ask_user_to_select_title_page(
                files,
                strategy=user_hits_control_c
            )

    def test_ask_user_to_select_title_zero(self):
        package_widget = cli.user_interaction.CLIPackageBrowserWidget()
        files = [
            "file1.jp2",
            "file2.jp2",
            "file3.jp2",
        ]

        selections = iter([
            0,
            1
        ])

        def user_selections():
            return next(selections)

        title_page = package_widget.ask_user_to_select_title_page(
            files,
            strategy=user_selections
        )
        assert title_page == "file1.jp2"

    def test_get_user_response(self, monkeypatch):
        package_widget = cli.user_interaction.CLIPackageBrowserWidget()
        package_data = MagicMock()

        monkeypatch.setattr(
            package_widget,
            "get_packages",
            lambda root_dir, image_type: [package_data]
        )

        monkeypatch.setattr(
            package_widget,
            "ask_user_to_select_title_page",
            lambda files, strategy=None: None
        )

        options = {
            "input": "somepath",
            "Image File Type": "TIFF"
        }
        pretask_result = []
        response = package_widget.get_user_response(options, pretask_result)
        assert "packages" in response
