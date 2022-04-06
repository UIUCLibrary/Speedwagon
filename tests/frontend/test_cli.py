from unittest.mock import Mock, MagicMock

import pytest
from uiucprescon.packager.packages import collection
from speedwagon.frontend import cli
from speedwagon.frontend.cli.user_interaction import \
    CLIConfirmFilesystemItemRemoval
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


class TestCLIConfirmFilesystemItemRemoval:
    def test_get_user_response_for_no_results(self):
        widget = CLIConfirmFilesystemItemRemoval()
        pretask_results = [
            Mock(spec=speedwagon.tasks.Result, data=[])
        ]
        response = widget.get_user_response(
            options={},
            pretask_results=pretask_results
        )
        assert len(response['items']) == 0

    def test_get_user_response_returns_files(self, monkeypatch):
        def accept_all_items(self, items, *args, **kwargs):
            return items

        monkeypatch.setattr(
            CLIConfirmFilesystemItemRemoval,
            "user_resolve_items",
            accept_all_items
        )

        widget = CLIConfirmFilesystemItemRemoval()

        pretask_results = [
            Mock(
                spec=speedwagon.tasks.Result,
                data=[
                    ".DS_Store"
                ]
            )
        ]

        response = widget.get_user_response(
            options={},
            pretask_results=pretask_results
        )
        items = response['items']
        assert len(items) == 1 and items[0] == ".DS_Store"

    def test_get_user_response_calls_resolve_items(self, monkeypatch):
        user_resolve_items = Mock()

        monkeypatch.setattr(CLIConfirmFilesystemItemRemoval,
            "user_resolve_items",
            user_resolve_items
        )

        widget = CLIConfirmFilesystemItemRemoval()
        pretask_results = [
            Mock(
                spec=speedwagon.tasks.Result,
                data=[
                    ".DS_Store"
                ]
            )
        ]
        widget.get_user_response(
            options={},
            pretask_results=pretask_results
        )
        assert user_resolve_items.called is True

    def test_user_resolve_items_resolves_yes(self):
        user_resolve_items = cli.user_interaction\
            .CLIConfirmFilesystemItemRemoval \
            .user_resolve_items

        files_tests = [
            "file1.txt"
        ]

        yes = CLIConfirmFilesystemItemRemoval.Confirm.YES

        assert user_resolve_items(
            files_tests,
            confirm_strategy=lambda _: yes
        ) == files_tests

    def test_user_resolve_items_resolves_no(self):
        confirm = CLIConfirmFilesystemItemRemoval.Confirm
        user_resolve_items = CLIConfirmFilesystemItemRemoval.user_resolve_items

        assert user_resolve_items(
            items=["file1.txt"],
            confirm_strategy=lambda _: confirm.NO
        ) == []

    def test_user_resolve_items_resolves_all(self):
        confirm = CLIConfirmFilesystemItemRemoval.Confirm
        user_resolve_items = CLIConfirmFilesystemItemRemoval.user_resolve_items
        files = [
            "file1.txt",
            "file2.txt"
        ]
        assert user_resolve_items(
            items=files,
            confirm_strategy=lambda _: confirm.YES_ALL
        ) == files

    def test_user_resolve_items_throw_if_bad_user_option(self):
        user_resolve_items = CLIConfirmFilesystemItemRemoval.user_resolve_items
        files = [
            "file1.txt",
            "file2.txt"
        ]
        with pytest.raises(TypeError):
            user_resolve_items(
                items=files,
                confirm_strategy=lambda _: "invalid"
            )


@pytest.mark.parametrize(
    "key_press, expected_response",
    [
        ("y", CLIConfirmFilesystemItemRemoval.Confirm.YES),
        ("Y", CLIConfirmFilesystemItemRemoval.Confirm.YES),
        ("n", CLIConfirmFilesystemItemRemoval.Confirm.NO),
        ("N", CLIConfirmFilesystemItemRemoval.Confirm.NO),
        ("a", CLIConfirmFilesystemItemRemoval.Confirm.YES_ALL),
        ("A", CLIConfirmFilesystemItemRemoval.Confirm.YES_ALL),
    ]
)
def test_user_confirm_removal_stdin(key_press, expected_response):
    stdin_request_strategy = lambda: key_press
    result = cli.user_interaction.user_confirm_removal_stdin(
        "file.txt",
        stdin_request_strategy=stdin_request_strategy
    )
    assert result == expected_response
