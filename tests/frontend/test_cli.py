import warnings
from typing import Sequence, Dict, List
from unittest.mock import Mock, MagicMock

import pytest
# import uiucprescon.packager.packages.collection
# from uiucprescon.packager.packages import collection

import speedwagon.exceptions
from speedwagon.frontend import cli
from speedwagon.frontend import interaction
from speedwagon.frontend.cli.user_interaction import (
    CLIConfirmFilesystemItemRemoval,
    CLIEditTable,
)
import speedwagon


# class TestCLIPackageBrowserWidget:
#     def test_get_package_files(self):
#         with warnings.catch_warnings():
#             warnings.simplefilter("ignore",category=DeprecationWarning)
#             package_widget = cli.user_interaction.CLIPackageBrowserWidget()
#
#         package_object = MagicMock()
#         item = MagicMock()
#         instance = Mock(spec=collection.Instantiation)
#         instance.files = [
#             "file1.jp2",
#             "file2.jp2",
#         ]
#         item.instantiations.values.return_value = [instance]
#
#         package_object.__iter__.return_value = [item]
#         files = package_widget.get_package_files(package_object)
#         assert files == [
#             "file1.jp2",
#             "file2.jp2",
#         ]
#
#     def test_ask_user_to_select_title_page(self):
#         with warnings.catch_warnings():
#             warnings.simplefilter("ignore",category=DeprecationWarning)
#             package_widget = cli.user_interaction.CLIPackageBrowserWidget()
#         files = [
#             "file1.jp2",
#             "file2.jp2",
#             "file3.jp2",
#         ]
#         title_page = package_widget.ask_user_to_select_title_page(
#             files, strategy=lambda: 1
#         )
#         assert title_page == "file1.jp2"
#
#     def test_ask_user_to_select_title_cancels(self):
#         with warnings.catch_warnings():
#             warnings.simplefilter("ignore",category=DeprecationWarning)
#             package_widget = cli.user_interaction.CLIPackageBrowserWidget()
#         files = [
#             "file1.jp2",
#             "file2.jp2",
#             "file3.jp2",
#         ]
#
#         def user_hits_control_c():
#             raise KeyboardInterrupt()
#
#         with pytest.raises(speedwagon.exceptions.JobCancelled):
#             package_widget.ask_user_to_select_title_page(
#                 files, strategy=user_hits_control_c
#             )
#
#     def test_ask_user_to_select_title_zero(self):
#         with warnings.catch_warnings():
#             warnings.simplefilter("ignore",category=DeprecationWarning)
#             package_widget = cli.user_interaction.CLIPackageBrowserWidget()
#         files = [
#             "file1.jp2",
#             "file2.jp2",
#             "file3.jp2",
#         ]
#
#         selections = iter([0, 1])
#
#         def user_selections():
#             return next(selections)
#
#         title_page = package_widget.ask_user_to_select_title_page(
#             files, strategy=user_selections
#         )
#         assert title_page == "file1.jp2"
#
#     def test_get_user_response(self, monkeypatch):
#         with warnings.catch_warnings():
#             warnings.simplefilter("ignore",category=DeprecationWarning)
#             package_widget = cli.user_interaction.CLIPackageBrowserWidget()
#         package_data = MagicMock()
#
#         monkeypatch.setattr(
#             package_widget,
#             "get_packages",
#             lambda root_dir, image_type: [package_data],
#         )
#
#         monkeypatch.setattr(
#             package_widget,
#             "ask_user_to_select_title_page",
#             lambda files, strategy=None: None,
#         )
#
#         options = {"input": "somepath", "Image File Type": "TIFF"}
#         pretask_result = []
#         response = package_widget.get_user_response(options, pretask_result)
#         assert "packages" in response
#
#     def test_sort_packages(self):
#         with warnings.catch_warnings():
#             warnings.simplefilter("ignore",category=DeprecationWarning)
#             package_widget = cli.user_interaction.CLIPackageBrowserWidget()
#         package = uiucprescon.packager.packages.collection.PackageObject()
#         should_be_first = uiucprescon.packager.packages.collection.Item(
#             package
#         )
#         should_be_first.component_metadata[
#             uiucprescon.packager.Metadata.ITEM_NAME
#         ] = "00000008"
#
#         should_be_second = uiucprescon.packager.packages.collection.Item(
#             package
#         )
#         should_be_second.component_metadata[
#             uiucprescon.packager.Metadata.ITEM_NAME
#         ] = "00000009"
#
#         package.items = [should_be_second, should_be_first]
#         result = package_widget.sort_package(package)
#         assert (
#             result.items[0].metadata[uiucprescon.packager.Metadata.ITEM_NAME]
#             == "00000008"
#             and result.items[1].metadata[
#                 uiucprescon.packager.Metadata.ITEM_NAME
#             ]
#             == "00000009"
#         )


class TestCLIEditTable:
    def test_data_gathering(self):
        pretask_results = [Mock(spec=speedwagon.tasks.Result, data=[])]

        def process_data(
            data: List[Sequence[interaction.DataItem]],
        ) -> List[Sequence[interaction.DataItem]]:
            return data

        def data_gathering(*args, **kwargs):
            return [
                (
                    interaction.DataItem("first", "1"),
                    interaction.DataItem("second", "2"),
                    interaction.DataItem("third", "3"),
                )
            ]

        widget = CLIEditTable[interaction.DataItem, Dict[str, str]](
            enter_data=data_gathering,
            process_data=process_data,
        )

        widget.column_names = ["first", "second", "third"]
        widget.title = "Select title page"
        results = widget.get_user_response(
            options={}, pretask_results=pretask_results
        )
        assert results[0][0].value == "1"

    def test_get_user_response(self):
        pretask_results = [Mock(spec=speedwagon.tasks.Result, data=[])]

        def process_data(data):
            return {}

        widget = CLIEditTable(
            enter_data=lambda *args, **kwargs: [],
            process_data=process_data,
        )
        widget.column_names = ["first", "second", "third"]
        widget.title = "Select title page"
        results = widget.get_user_response(
            options={}, pretask_results=pretask_results
        )
        assert isinstance(results, dict)


class TestCLIConfirmFilesystemItemRemoval:
    def test_get_user_response_for_no_results(self):
        widget = CLIConfirmFilesystemItemRemoval()
        pretask_results = [Mock(spec=speedwagon.tasks.Result, data=[])]
        response = widget.get_user_response(
            options={}, pretask_results=pretask_results
        )
        assert len(response["items"]) == 0

    def test_get_user_response_returns_files(self, monkeypatch):
        def accept_all_items(self, items, *args, **kwargs):
            return items

        monkeypatch.setattr(
            CLIConfirmFilesystemItemRemoval,
            "user_resolve_items",
            accept_all_items,
        )

        widget = CLIConfirmFilesystemItemRemoval()

        pretask_results = [
            Mock(spec=speedwagon.tasks.Result, data=[".DS_Store"])
        ]

        response = widget.get_user_response(
            options={}, pretask_results=pretask_results
        )
        items = response["items"]
        assert len(items) == 1 and items[0] == ".DS_Store"

    def test_get_user_response_calls_resolve_items(self, monkeypatch):
        user_resolve_items = Mock()

        monkeypatch.setattr(
            CLIConfirmFilesystemItemRemoval,
            "user_resolve_items",
            user_resolve_items,
        )

        widget = CLIConfirmFilesystemItemRemoval()
        pretask_results = [
            Mock(spec=speedwagon.tasks.Result, data=[".DS_Store"])
        ]
        widget.get_user_response(options={}, pretask_results=pretask_results)
        assert user_resolve_items.called is True

    def test_user_resolve_items_resolves_yes(self):
        user_resolve_items = CLIConfirmFilesystemItemRemoval.user_resolve_items

        files_tests = ["file1.txt"]

        yes = CLIConfirmFilesystemItemRemoval.Confirm.YES

        assert (
            user_resolve_items(files_tests, confirm_strategy=lambda _: yes)
            == files_tests
        )

    def test_user_resolve_items_resolves_no(self):
        confirm = CLIConfirmFilesystemItemRemoval.Confirm
        user_resolve_items = CLIConfirmFilesystemItemRemoval.user_resolve_items

        assert (
            user_resolve_items(
                items=["file1.txt"], confirm_strategy=lambda _: confirm.NO
            )
            == []
        )

    def test_user_resolve_items_resolves_all(self):
        confirm = CLIConfirmFilesystemItemRemoval.Confirm
        user_resolve_items = CLIConfirmFilesystemItemRemoval.user_resolve_items
        files = ["file1.txt", "file2.txt"]
        assert (
            user_resolve_items(
                items=files, confirm_strategy=lambda _: confirm.YES_ALL
            )
            == files
        )

    def test_user_resolve_items_throw_if_bad_user_option(self):
        user_resolve_items = CLIConfirmFilesystemItemRemoval.user_resolve_items
        files = ["file1.txt", "file2.txt"]
        with pytest.raises(TypeError):
            user_resolve_items(
                items=files, confirm_strategy=lambda _: "invalid"
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
    ],
)
def test_user_confirm_removal_stdin(key_press, expected_response):
    result = cli.user_interaction.user_confirm_removal_stdin(
        "file.txt", stdin_request_strategy=lambda: key_press
    )
    assert result == expected_response


@pytest.mark.parametrize(
    "method_name, args",
    [
        ("table_data_editor",
         {
             "enter_data": lambda: None,
             "process_data": lambda : None,
         }
         ),
        ("confirm_removal", None)
    ]
)
def test_factor_produce_user_widget(method_name, args):
    factory = cli.user_interaction.CLIFactory()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore",category=DeprecationWarning)
        method = getattr(factory, method_name)
        assert isinstance(
            method(**args) if args else method(), interaction.AbsUserWidget
        )


def test_table_data_editor():
    factory = cli.user_interaction.CLIFactory()
    answers = iter(
        [
            "1",
            "2",
        ]
    )
    factory.table_editor.get_selection = lambda: next(answers)

    def process(data):
        rows = []
        for row in data:
            rows.append({row[0].name: row[0].value, row[1].name: row[1].value})
        return rows

    options = {}
    pretask_results = []

    row_one_data_point_one = interaction.DataItem(
        "First", value="Yes", editable=True
    )
    row_one_data_point_one.possible_values = ["Yes", "No"]
    row_one_data_point_two = interaction.DataItem(
        "Second", value="Yes", editable=False
    )

    row_two_data_point_one = interaction.DataItem(
        "First", value="Yes", editable=True
    )
    row_two_data_point_one.possible_values = ["Yes", "No"]
    row_two_data_point_two = interaction.DataItem(
        "Second", value="No", editable=False
    )

    row_one = (row_one_data_point_one, row_one_data_point_two)
    row_two = (row_two_data_point_one, row_two_data_point_two)

    editor = factory.table_data_editor(
        enter_data=lambda *args, **kwargs: [row_one, row_two],
        process_data=process,
    )

    assert editor.get_user_response(
        options=options, pretask_results=pretask_results
    ) == [{"First": "Yes", "Second": "Yes"}, {"First": "No", "Second": "No"}]
