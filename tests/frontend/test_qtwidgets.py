import csv
import io
import warnings
from unittest.mock import MagicMock, Mock, ANY

import pytest
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QtCore = pytest.importorskip("PySide6.QtCore")
from uiucprescon.packager.common import Metadata as PackageMetadata
from PySide6 import QtWidgets, QtCore

import speedwagon
import speedwagon.exceptions
from speedwagon.frontend import qtwidgets, interaction
from speedwagon.frontend.qtwidgets.dialog import title_page_selection
from speedwagon.frontend.qtwidgets.user_interaction import (
        ConfirmTableDetailsModel,
        ExportCSVConfirmedDeleted,
        ExportCSVConfirmedAction,
)


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


class TestConfirmTableModel:
    def test_model_mapping(self):
        items = [
            "./file1.txt",
            "/directory/"
        ]
        list_model = qtwidgets.user_interaction.ConfirmListModel()
        model = qtwidgets.user_interaction.ConfirmTableDetailsModel()
        model.setSourceModel(list_model)
        list_model.items = items
        assert model.index(
            0,
            model.DetailsColumns.NAME
        ).data(QtCore.Qt.DisplayRole) == "file1.txt"

    @pytest.mark.parametrize(
        "items,column,sorting_order,expected_file_item",
        [
            (
                [
                    "./file1.txt",
                    "/directory/"
                ],
                ConfirmTableDetailsModel.DetailsColumns.NAME,
                QtCore.Qt.DescendingOrder,
                "file1.txt"
            ),
            (
                [
                    "/directory/",
                    "./file1.txt",
                ],
                ConfirmTableDetailsModel.DetailsColumns.NAME,
                QtCore.Qt.DescendingOrder,
                "file1.txt"
            ),
            (
                [
                    "/directory/",
                    "./file1.txt",
                ],
                ConfirmTableDetailsModel.DetailsColumns.NAME,
                QtCore.Qt.AscendingOrder,
                ""
            ),
            (
                [
                    "/directory/",
                    "./file1.txt",
                ],
                ConfirmTableDetailsModel.DetailsColumns.LOCATION,
                QtCore.Qt.AscendingOrder,
                "."
            ),
            (
                [
                    "/directory/",
                    "./file1.txt",
                ],
                ConfirmTableDetailsModel.DetailsColumns.LOCATION,
                QtCore.Qt.DescendingOrder,
                "/directory"
            ),
        ]
    )
    def test_sort(self, qtbot, items, column, sorting_order, expected_file_item):
        list_model = qtwidgets.user_interaction.ConfirmListModel()
        model = qtwidgets.user_interaction.ConfirmTableDetailsModel()
        model.setSourceModel(list_model)
        list_model.items = items
        table = QtWidgets.QTableView()

        proxy_model = qtwidgets.user_interaction.DetailsSorterProxyModel()
        proxy_model.setSourceModel(model)

        table.setModel(proxy_model)
        table.setSortingEnabled(True)
        table.sortByColumn(column, sorting_order)
        new_data = proxy_model.index(0, column)
        assert new_data.data() == expected_file_item

    def test_sort_checked_ascending(self, qtbot):
        items = [
            "./file1.txt",
            "/directory/more.txt"
        ]
        list_model = qtwidgets.user_interaction.ConfirmListModel()
        details_model = qtwidgets.user_interaction.ConfirmTableDetailsModel()
        details_model.setSourceModel(list_model)
        table = QtWidgets.QTableView()

        proxy_model = qtwidgets.user_interaction.DetailsSorterProxyModel()
        proxy_model.setSourceModel(details_model)

        list_model.items = items
        table.setModel(proxy_model)
        table.setSortingEnabled(True)

        list_model.setData(
            list_model.match(
                list_model.index(0),
                QtCore.Qt.DisplayRole,
                "./file1.txt"
            )[0],
            QtCore.Qt.Checked,
            role=QtCore.Qt.CheckStateRole
        )
        table.sortByColumn(
            ConfirmTableDetailsModel.DetailsColumns.SELECTED,
            QtCore.Qt.AscendingOrder
        )

        new_data = table.model().index(
            1,
            ConfirmTableDetailsModel.DetailsColumns.NAME
        )
        assert new_data.data() == "file1.txt"

    def test_sort_checked_descending(self, qtbot):
        items = [
            "./file1.txt",
            "/directory/more.txt"
        ]
        list_model = qtwidgets.user_interaction.ConfirmListModel()
        details_model = qtwidgets.user_interaction.ConfirmTableDetailsModel()
        details_model.setSourceModel(list_model)
        table = QtWidgets.QTableView()

        proxy_model = qtwidgets.user_interaction.DetailsSorterProxyModel()
        proxy_model.setSourceModel(details_model)

        list_model.items = items
        table.setModel(proxy_model)
        table.setSortingEnabled(True)

        list_model.setData(
            list_model.match(
                list_model.index(0),
                QtCore.Qt.DisplayRole,
                "./file1.txt"
            )[0],
            QtCore.Qt.Checked,
            role=QtCore.Qt.CheckStateRole
        )
        table.sortByColumn(0, QtCore.Qt.DescendingOrder)

        new_data = table.model().index(
            1,
            ConfirmTableDetailsModel.DetailsColumns.NAME
        )
        assert new_data.data() == "more.txt"

    def test_empty_first_column(self, qtbot):
        list_model = qtwidgets.user_interaction.ConfirmListModel()
        model = qtwidgets.user_interaction.ConfirmTableDetailsModel()
        model.setSourceModel(list_model)
        items = [
            "./file1.txt",
            "/directory/"
        ]
        list_model.items = items
        table = QtWidgets.QTableView()

        table.setModel(model)
        table_model = table.model()
        assert table_model.data(
            table_model.index(0, 0),
            role=QtCore.Qt.DisplayRole
        ) is None


class TestConfirmListModel:
    def test_model_check(self, qtmodeltester):
        items = [
            "./file1.txt",
            "/directory/"
        ]
        model = qtwidgets.user_interaction.ConfirmListModel(items)
        qtmodeltester.check(model)

    def test_all_data_defaults_to_unchecked(self):
        items = [
            "./file1.txt",
            "/directory/"
        ]
        model = qtwidgets.user_interaction.ConfirmListModel(items)
        assert model.selected() == []

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
        model.setData(
            index=model.index(1),
            value=QtCore.Qt.Checked,
            role=QtCore.Qt.CheckStateRole
        )

        assert model.selected() == ["/directory/"]


class TestConfirmDeleteDialog:
    def test_okay_button_accepts(self, qtbot):
        items = []
        dialog_box = \
            qtwidgets.user_interaction.ConfirmDeleteDialog(items)

        okay_button = \
            dialog_box.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok)

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
            dialog_box.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok)

        assert ok_button.isEnabled() is expected_enabled

    def test_cancel_button_rejects(self, qtbot):
        items = []
        dialog_box = \
            qtwidgets.user_interaction.ConfirmDeleteDialog(items)

        cancel_button = \
            dialog_box.dialog_button_box.button(
                QtWidgets.QDialogButtonBox.Cancel
            )

        with qtbot.wait_signal(dialog_box.rejected):
            cancel_button.click()

    def test_select_all(self, qtbot):
        items = [
            "./file1.txt",
            "/directory/"
        ]
        dialog_box = \
            qtwidgets.user_interaction.ConfirmDeleteDialog(items)
        dialog_box.select_all_button.click()
        assert dialog_box.model.selected() == items


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


class TestQtWidgetTitlePageSelection:
    def test_selection(self, monkeypatch, qtbot):
        from speedwagon.workflows.workflow_batch_to_HathiTrust_TIFF \
            import FindCaptureOnePackageTask

        widget = \
            qtwidgets.user_interaction.QtWidgetTitlePageSelection(parent=None)

        mock_package = MagicMock()
        mock_data = {
                "ID": "99423682912205899",
                "ITEM_NAME": "",
                "TITLE_PAGE": "99423682912205899_0001.tif",
                "PATH": "/some/random/path/"
            }

        def mock_get_item(obj, key):
            return mock_data.get(key.name, str(key))

        mock_package.metadata.__getitem__ = mock_get_item
        mock_package.__len__ = lambda x: 1

        pretask_result = speedwagon.tasks.Result(
            source=FindCaptureOnePackageTask,
            data=[mock_package]
            )

        data = Mock()
        data.metadata = MagicMock()
        data.metadata.__getitem__ = \
            lambda _, k: mock_data.get(k.name, str(k))

        browser_widget = Mock(name='browser_widget')
        browser_widget.data = Mock(return_value=[data])
        browser_widget.result = \
            Mock(name="result", return_value=QtWidgets.QDialog.Accepted)

        widget.browser_widget = Mock(
            name="browser_widget_type", return_value=browser_widget
        )
        results = widget.get_user_response({}, [pretask_result])
        assert results['title_pages']['99423682912205899'] == \
               "99423682912205899_0001.tif"


def test_package_browser(qtbot):
    mock_package = MagicMock()

    def mock_get_item(obj, key):
        return {
            "ID": "99423682912205899",
            "ITEM_NAME": "",
            "TITLE_PAGE": "99423682912205899_0001.tif",
            "PATH": "/some/random/path/"
        }.get(key.name, str(key))

    mock_package.metadata.__getitem__ = mock_get_item
    mock_package.__len__ = lambda x: 1

    widget = title_page_selection.PackageBrowser([mock_package], None)

    with qtbot.waitSignal(widget.finished) as blocker:
        widget.ok_button.click()
    data = widget.data()

    assert data[0].metadata[PackageMetadata.TITLE_PAGE] == \
           "99423682912205899_0001.tif"


def test_get_additional_info_opens_dialog():
    from speedwagon.workflows import workflow_batch_to_HathiTrust_TIFF as wf
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        workflow = wf.CaptureOneBatchToHathiComplete()

    user_request_factory = Mock(spec=interaction.UserRequestFactory)
    user_request_factory.package_title_page_selection = MagicMock()
    workflow.get_additional_info(
        user_request_factory=user_request_factory,
        options={},
        pretask_results=[MagicMock()]
    )
    assert user_request_factory.package_title_page_selection.called is True


class TestExportConfirmedDeletedAction:

    @pytest.fixture
    def model(self) -> qtwidgets.user_interaction.ConfirmListModel:
        return qtwidgets.user_interaction.ConfirmListModel()

    def test_csv_produces_header(self, model):
        action = ExportCSVConfirmedDeleted(model=model)
        data = action.generate_csv()
        assert all(
            key in data for key in ExportCSVConfirmedDeleted.field_names
        )

    def test_csv_produces_a_string(self, model):
        action = ExportCSVConfirmedDeleted(model=model)
        data = action.generate_csv()
        assert isinstance(data, str)

    def test_output_item_name(self, model):
        action = ExportCSVConfirmedDeleted(model=model)
        model.items = ["dummy"]
        data = action.generate_csv()
        assert "dummy" in data

    @pytest.mark.parametrize(
        'check_state,expected_csv_value',
        [
                (QtCore.Qt.Unchecked, "False"),
                (QtCore.Qt.Checked, "True"),
        ]
    )
    def test_output_selected_for_removal(
            self,
            model,
            check_state,
            expected_csv_value
    ):
        action = ExportCSVConfirmedDeleted(model=model)
        model.items = ["dummy"]
        match =\
            model.match(model.index(0, 0), QtCore.Qt.DisplayRole, "dummy")[0]

        model.setData(match, role=QtCore.Qt.CheckStateRole, value=check_state)
        data = action.generate_csv()
        with io.StringIO() as file_string:
            file_string.write(data)
            file_string.seek(0)
            row = next(csv.DictReader(file_string))
            assert row['selected_for_removal'] == expected_csv_value


class TestExportCSVConfirmedAction:
    @pytest.fixture
    def model(self) -> qtwidgets.user_interaction.ConfirmListModel:
        return qtwidgets.user_interaction.ConfirmListModel()

    def test_calls_getSaveFileName(self, qtbot,model):
        action = ExportCSVConfirmedAction()
        model.items = ["dummy"]
        # action.export_model(model)
        action.dialog.getSaveFileName = Mock(
            return_value=(
                'somefile.csv', 'Comma-separated Values (*.csv)'
            )
        )
        action.get_output_file()
        assert action.dialog.getSaveFileName.called is True

    def test_export_model(self, model):
        model.items = ["dummy"]

        action = ExportCSVConfirmedAction()
        action.dialog.getSaveFileName = Mock(
            return_value=(
                'somefile.csv', 'Comma-separated Values (*.csv)'
            )
        )
        action.save_file_to_disk = Mock()

        strategy = Mock()
        strategy_class = Mock(return_value=strategy)
        action.export_model(model, report_strategy=strategy_class)
        assert strategy.generate.called is True

    def test_export_model_calls_save_file(self, model):
        model.items = ["dummy"]

        action = ExportCSVConfirmedAction()
        action.dialog.getSaveFileName = Mock(
            return_value=(
                'somefile.csv', 'Comma-separated Values (*.csv)'
            )
        )
        action.save_file_to_disk = Mock()

        strategy = Mock()
        strategy_class = Mock(return_value=strategy)
        action.export_model(model, report_strategy=strategy_class)
        action.save_file_to_disk.assert_called_once_with('somefile.csv', ANY)

