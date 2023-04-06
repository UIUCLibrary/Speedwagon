import warnings
from unittest.mock import MagicMock, Mock

import pytest
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QtCore = pytest.importorskip("PySide6.QtCore")
from uiucprescon.packager.common import Metadata as PackageMetadata
# from PySide6 import QtWidgets, QtCore

import speedwagon
import speedwagon.exceptions
from speedwagon.frontend import qtwidgets, interaction
from speedwagon.frontend.qtwidgets import widgets
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

    def test_cancel(self, qtbot, monkeypatch):
        parent = QtWidgets.QWidget()

        def get_packages(*_, **__):
            return []

        monkeypatch.setattr(
            qtwidgets.user_interaction.QtWidgetPackageBrowserWidget,
            "get_packages",
            get_packages
        )

        browse_widget = \
            qtwidgets.user_interaction.QtWidgetPackageBrowserWidget(parent)

        monkeypatch.setattr(
            qtwidgets.user_interaction.PackageBrowser,
            "exec",
            lambda _self: _self.reject()
        )
        with pytest.raises(speedwagon.exceptions.JobCancelled):
            browse_widget.get_data_with_dialog_box(
                root_dir="somePath",
                image_type=interaction.SupportedImagePackageFormats.JP2,
            )

    def test_success(self, qtbot, monkeypatch):
        parent = QtWidgets.QWidget()

        def get_packages(*_, **__):
            return []

        monkeypatch.setattr(
            qtwidgets.user_interaction.QtWidgetPackageBrowserWidget,
            "get_packages",
            get_packages
        )
        browse_widget = \
            qtwidgets.user_interaction.QtWidgetPackageBrowserWidget(parent)

        monkeypatch.setattr(
            qtwidgets.user_interaction.PackageBrowser,
            "exec",
            lambda _self: _self.accept()
        )
        data = browse_widget.get_data_with_dialog_box(
            root_dir="somePath",
            image_type=interaction.SupportedImagePackageFormats.JP2,
        )
        assert data == []


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


class TestSelectWorkflow:
    def test_add_workflow_adds_to_model(self, qtbot):
        parent = QtWidgets.QWidget()
        selector = widgets.SelectWorkflow(parent)
        qtbot.addWidget(selector)
        class FakeWorkflow(speedwagon.Workflow):
            pass
        assert selector.workflowSelectionView.model().rowCount() == 0
        selector.add_workflow(FakeWorkflow)
        assert selector.workflowSelectionView.model().rowCount() == 1

    def test_set_current_by_name(self, qtbot):
        parent = QtWidgets.QWidget()
        selector = widgets.SelectWorkflow(parent)
        qtbot.addWidget(selector)

        class FakeWorkflow(speedwagon.Workflow):
            name = "dummy"

        assert selector.workflowSelectionView.model().rowCount() == 0
        selector.add_workflow(FakeWorkflow)
        selector.set_current_by_name("dummy")
        assert selector.get_current_workflow_type() == FakeWorkflow

    def test_set_current_by_name_invalid_raises(self, qtbot):
        parent = QtWidgets.QWidget()
        selector = widgets.SelectWorkflow(parent)
        qtbot.addWidget(selector)

        class FakeWorkflow(speedwagon.Workflow):
            name = "dummy"

        assert selector.workflowSelectionView.model().rowCount() == 0
        selector.add_workflow(FakeWorkflow)
        with pytest.raises(ValueError):
            selector.set_current_by_name("invalid workflow")


class TestWorkflowsTab3:
    def test_set_current_workflow_settings_before_workflow_raises(
            self,
            qtbot
    ):
        tab = qtwidgets.tabs.WorkflowsTab3()
        with pytest.raises(ValueError):
            tab.set_current_workflow_settings({"does not exists": True})

    def test_add_workflows(self, qtbot):
        class Spam(speedwagon.Workflow):
            name = "spam"
            def discover_task_metadata(self, *args, **kwargs):
                return []

        tab = qtwidgets.tabs.WorkflowsTab3()
        assert len(tab.workflows) == 0
        tab.workflows = {"spam": Spam}
        assert tab.workflows["spam"] == Spam

    def test_set_current_workflow(self, qtbot):
        class Spam(speedwagon.Workflow):
            name = "spam"

            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                assert kwargs['global_settings']['spam'] == "eggs"

            def discover_task_metadata(self, *args, **kwargs):
                return []

        tab = qtwidgets.tabs.WorkflowsTab3()
        tab.app_settings_lookup_strategy = Mock(settings=Mock(return_value={"spam": "eggs"}))
        tab.workflows = {"spam": Spam}
        tab.set_current_workflow('spam')