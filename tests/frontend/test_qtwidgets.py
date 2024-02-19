import warnings
from unittest.mock import MagicMock, Mock

import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QtCore = pytest.importorskip("PySide6.QtCore")
import speedwagon
import speedwagon.exceptions
from speedwagon.frontend import qtwidgets, interaction
from speedwagon.frontend.qtwidgets import widgets, models
from speedwagon.config import StandardConfigFileLocator


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



class TestSelectWorkflow:
    def test_add_workflow_adds_to_model(self, qtbot):
        parent = QtWidgets.QWidget()
        selector = widgets.SelectWorkflow(parent)
        qtbot.addWidget(selector)
        class FakeWorkflow(speedwagon.Workflow):
            pass
        assert selector.model.rowCount() == 0
        selector.add_workflow(FakeWorkflow)
        assert selector.model.rowCount() == 1

    def test_set_current_by_name(self, qtbot):
        parent = QtWidgets.QWidget()
        selector = widgets.SelectWorkflow(parent)
        qtbot.addWidget(selector)

        class FakeWorkflow(speedwagon.Workflow):
            name = "dummy"

        assert selector.model.rowCount() == 0
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
    def test_model(self, qtbot):
        selector = widgets.SelectWorkflow()
        model = models.WorkflowList()
        class FakeWorkflow(speedwagon.Workflow):
            name = "dummy"
        model.add_workflow(FakeWorkflow)
        selector.model = model
        assert selector.workflowSelectionView.model().rowCount() == 1

    def test_selected_index_changed(self, qtbot):
        class BaconWorkflow(speedwagon.Workflow):
            name = "Bacon"

        class SpamWorkflow(speedwagon.Workflow):
            name = "Spam"

        selector = widgets.SelectWorkflow()
        model = models.WorkflowList()
        model.add_workflow(BaconWorkflow)
        model.add_workflow(SpamWorkflow)
        selector.model = model
        index = selector.model.index(0, 0)
        with qtbot.wait_signal(selector.selected_index_changed) as signal:
            qtbot.mouseClick(
                selector.workflowSelectionView.viewport(),
                QtCore.Qt.LeftButton,
                pos=selector.workflowSelectionView.visualRect(
                    index
                ).center()
            )
        assert signal.args[0] == index


class TestWorkflowsTab3:
    @pytest.fixture()
    def tab_widget(self, monkeypatch):
        monkeypatch.setattr(
            StandardConfigFileLocator,
            "get_app_data_dir",
            lambda _ : "."
        )
        return qtwidgets.tabs.WorkflowsTab3()
    def test_set_current_workflow_settings_before_workflow_raises(
            self,
            qtbot,
            tab_widget
    ):
        with pytest.raises(ValueError):
            tab_widget.set_current_workflow_settings({"does not exists": True})

    def test_add_workflows(self, qtbot, tab_widget):
        class Spam(speedwagon.Workflow):
            name = "spam"
            def discover_task_metadata(self, *args, **kwargs):
                return []

        assert len(tab_widget.workflows) == 0

        tab_widget.add_workflow(Spam)
        assert "spam" in tab_widget.workflows
        # tab.workflows = {"spam": Spam}
        assert tab_widget.workflows["spam"] == Spam

    def test_set_current_workflow(self, qtbot, tab_widget):
        class Spam(speedwagon.Workflow):
            name = "spam"

            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                assert kwargs['global_settings']['spam'] == "eggs"

            def discover_task_metadata(self, *args, **kwargs):
                return []

        tab_widget.app_settings_lookup_strategy = Mock(
            settings=Mock(
                return_value={"GLOBAL": {"spam": "eggs"}}
            )
        )
        tab_widget.workspace.app_settings_lookup_strategy =  Mock(
            settings=Mock(
                return_value={"GLOBAL": {"spam": "eggs"}}
            )
        )
        with qtbot.wait_signal(tab_widget.model().dataChanged):
            tab_widget.add_workflow(Spam)
        with qtbot.wait_signal(tab_widget.workflow_selected):
            tab_widget.set_current_workflow('spam')
        assert tab_widget.current_workflow() == "spam"
    def test_workflows(self, qtbot, tab_widget):
        class DummyWorkflow(speedwagon.Workflow):
            name = "dummy 1"

        base_model = models.TabsTreeModel()
        base_model.append_workflow_tab(
            "Dummy tab",
            [
                DummyWorkflow,
            ]
        )

        model = models.TabProxyModel()
        model.setSourceModel(base_model)
        model.set_source_tab("Dummy tab")
        tab = qtwidgets.tabs.WorkflowsTab3()
        tab.set_model(model)
        assert "dummy 1" in tab.workflows

    def test_workflow_selected(self, qtbot, tab_widget):
        class DummyWorkflow(speedwagon.Workflow):
            name = "dummy 1"
            description = "Dummy Description"
            def discover_task_metadata(self, *args, **kwargs):
                return []

        tab_widget.add_workflow(DummyWorkflow)
        tab_widget.workspace.app_settings_lookup_strategy = \
            Mock(
                speedwagon.config.AbsConfigSettings,
                settings=Mock(return_value={})
        )
        with qtbot.wait_signal(tab_widget.workflow_selected):
            qtbot.mouseClick(
                tab_widget.workflow_selector.workflowSelectionView.viewport(),
                QtCore.Qt.LeftButton,
                pos=tab_widget.workflow_selector.workflowSelectionView.visualRect(
                    tab_widget.workflow_selector.model.index(0, 0)
                ).center()
            )

    def test_workflow_selected_updates_workspace(self, qtbot, tab_widget):
        class DummyWorkflow(speedwagon.Workflow):
            name = "dummy 1"
            description = "Dummy Description"

            def discover_task_metadata(self, *args, **kwargs):
                return []

        tab_widget.workspace.app_settings_lookup_strategy = Mock(
            speedwagon.config.AbsConfigSettings,
            settings=Mock(return_value={})
        )
        tab_widget.add_workflow(DummyWorkflow)

        with qtbot.wait_signal(tab_widget.workflow_selected):
            qtbot.mouseClick(
                tab_widget.workflow_selector.workflowSelectionView.viewport(),
                QtCore.Qt.LeftButton,
                pos=tab_widget.workflow_selector.workflowSelectionView.visualRect(
                    tab_widget.workflow_selector.model.index(0, 0)
                ).center()
            )
        assert tab_widget.workspace.name == "dummy 1"

class TestToolConsole:
    def test_add_message(self, qtbot):
        console = speedwagon.frontend.qtwidgets.widgets.ToolConsole(None)
        qtbot.addWidget(console)
        console.add_message("I'm a message")
        assert "I'm a message" in console.text
