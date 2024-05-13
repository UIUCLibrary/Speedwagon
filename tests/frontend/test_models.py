import json
import os
from typing import List, Any, Dict, Optional
from unittest.mock import Mock
import sys


if sys.version_info < (3, 10):
    import importlib_metadata as metadata
else:
    from importlib import metadata


import pytest
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QtCore = pytest.importorskip("PySide6.QtCore")
QtGui = pytest.importorskip("PySide6.QtGui")
import speedwagon.config
from speedwagon import workflow
from speedwagon.frontend.qtwidgets import models
from speedwagon.frontend.qtwidgets.models.settings import (
    build_setting_qt_model,
    WorkflowSettingsModel,
)


def test_build_setting_model_missing_file(tmpdir):
    dummy = str(os.path.join(tmpdir, "config.ini"))
    with pytest.raises(FileNotFoundError):
        build_setting_qt_model(dummy)


class TestSettingsModel:
    @pytest.fixture()
    def model(self):
        return models.SettingsModel(None)

    @pytest.mark.parametrize(
        "role",
        [
            QtCore.Qt.DisplayRole,
            QtCore.Qt.EditRole,
        ],
    )
    def test_data(self, role, model):
        model.add_setting("spam", "eggs")
        assert model.data(model.index(0, 0), role=role) == "spam"

    @pytest.mark.parametrize(
        "index, expected",
        [
            (0, "Key"),
            (1, "Value"),
        ],
    )
    def test_header_data(self, index, expected, model):
        value = model.headerData(
            index, QtCore.Qt.Horizontal, role=QtCore.Qt.DisplayRole
        )

        assert value == expected

    def test_set_data(self, model):
        model.add_setting("spam", "eggs")
        model.setData(model.index(0, 0), data="dumb")
        assert model._data[0][1] == "dumb"

    @pytest.mark.parametrize(
        "column, expected",
        [
            (0, QtCore.Qt.NoItemFlags),
            (1, QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable),
        ],
    )
    def test_flags(self, column, expected, model):
        model.add_setting("spam", "eggs")
        flags = model.flags(model.index(0, column))
        assert flags == expected

    def test_settings_model_empty(self, model):
        assert model.rowCount() == 0
        assert model.columnCount() == 2
        index = model.index(0, 0)
        assert index.data() is None

    def test_settings_model_added(self, model):
        model.add_setting("mysetting", "eggs")
        assert model.rowCount() == 1
        assert model.columnCount() == 2
        assert model.index(0, 0).data() == "mysetting"
        assert model.index(0, 1).data() == "eggs"

        index = model.index(0, 1)
        assert model.data(index) is None

    def test_modified(self, model):
        model.add_setting("spam", "eggs")
        model.setData(model.index(0, 0), data="dumb")
        assert model.data_modified is True

    def test_not_modified(self, model):
        model.add_setting("spam", "eggs")
        assert model.data_modified is False

    def test_not_modified_after_reverted(self, model):
        model.add_setting("spam", "eggs")
        model.setData(model.index(0, 0), data="dumb")
        # revert back to original
        model.setData(model.index(0, 0), data="eggs")
        assert model.data_modified is False

    def test_data_for_invalid_index_is_none(self, model):
        index = model.index(-1, -1)
        assert model.data(index) is None

    def test_no_vertical_header_data(self, model):
        assert model.headerData(0, QtCore.Qt.Orientation.Vertical) is None

    def test_set_data_on_invalid_data_returns_false(self, model):
        index = model.index(-1, -1)
        assert model.setData(index, "data") is False


class TestToolOptionsModel4:
    @pytest.fixture()
    def dialog_box(self, qtbot):
        dialog = QtWidgets.QDialog()
        dialog.setFixedWidth(300)
        dialog.setFixedHeight(300)
        qtbot.addWidget(dialog)
        return dialog

    @pytest.fixture()
    def table_widget(self, dialog_box, qtbot):
        table = QtWidgets.QTableView(parent=dialog_box)
        table.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        table.horizontalHeader().setVisible(False)

        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        v_header = table.verticalHeader()
        v_header.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        v_header.setSectionsClickable(False)
        v_header.setDefaultSectionSize(25)

        qtbot.addWidget(table)
        return table

    @pytest.fixture
    def data(self):
        checksum_select = workflow.FileSelectData("Checksum File")
        checksum_select.filter = "Checksum files (*.md5)"

        options = workflow.ChoiceSelection("Order")
        options.add_selection("Bacon")
        options.add_selection("Bacon eggs")
        options.add_selection("Spam")

        return [checksum_select, options, workflow.DirectorySelect("Eggs")]

    def test_headings(self, qtbot, data):
        model = models.ToolOptionsModel4(data)
        heading = model.headerData(
            0, QtCore.Qt.Vertical, QtCore.Qt.DisplayRole
        )

        assert heading == data[0].label

    def test_horizontal_heading_are_empty(self, data):
        model = models.ToolOptionsModel4(data)
        heading = model.headerData(
            0, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole
        )
        assert heading is None

    def test_rows_match_data_size(self, qtbot, data):
        model = models.ToolOptionsModel4(data)
        assert model.rowCount() == len(data)

    def test_data_json_role_make_parseable_data(self, data):
        model = models.ToolOptionsModel4(data)
        index = model.index(0, 0)

        json_string = model.data(
            index, role=models.ToolOptionsModel4.JsonDataRole
        )

        assert "widget_type" in json.loads(json_string)

    def test_get_data_invalid_index_is_none(self, data):
        model = models.ToolOptionsModel4(data)
        index = model.index(len(data) + 1, 0)
        assert model.data(index) is None

    def test_set_data(self, data):
        model = models.ToolOptionsModel4(data)
        index = model.index(0, 0)

        starting_value = model.data(index)

        model.setData(index, "spam")
        changed_value = model.data(index)
        assert starting_value is None and changed_value == "spam"

    def test_serialize_as(self, data):
        model = models.ToolOptionsModel4(data)

        def standard_serialize_function(
                model_data: Optional[List[workflow.AbsOutputOptionDataType]]
        ) -> Dict[str, str]:
            return (
                    {d.label: d.value for d in model_data}
                    if model_data is not None else {}
            )
        assert "Checksum File" in model.get_as(standard_serialize_function)


def test_build_setting_model(tmpdir):

    dummy = str(os.path.join(tmpdir, "config.ini"))
    empty_config_data = """[GLOBAL]
debug: False
        """
    with open(dummy, "w") as wf:
        wf.write(empty_config_data)
    model = build_setting_qt_model(dummy)
    assert isinstance(model, models.SettingsModel)

    assert model is not None


class TestPluginActivationModel:
    def test_adding_plugin_adds_row(self):
        plugin_model = models.PluginActivationModel()
        assert plugin_model.rowCount() == 0
        plugin_entry = Mock(spec=metadata.EntryPoint)
        plugin_model.add_entry_point(plugin_entry)
        assert plugin_model.rowCount() == 1

    def test_name_is_displayed(self):
        plugin_model = models.PluginActivationModel()
        plugin_entry = Mock(spec=metadata.EntryPoint)
        plugin_entry.name = "spam"
        plugin_model.add_entry_point(plugin_entry)
        value = plugin_model.data(
            plugin_model.index(0), QtCore.Qt.ItemDataRole.DisplayRole
        )
        assert "spam" in value

    @pytest.mark.parametrize(
        "expected_flag",
        [
            QtCore.Qt.ItemFlag.ItemIsUserCheckable,
            QtCore.Qt.ItemFlag.ItemIsSelectable,
            QtCore.Qt.ItemFlag.ItemIsEnabled,
        ],
    )
    def test_flags(self, expected_flag):
        plugin_model = models.PluginActivationModel()
        plugin_entry = Mock(spec=metadata.EntryPoint)
        plugin_entry.name = "spam"
        plugin_model.add_entry_point(plugin_entry)
        assert expected_flag in plugin_model.flags(plugin_model.index(0))

    def test_default_checked_role_unchecked(self):
        plugin_model = models.PluginActivationModel()
        plugin_entry = Mock(spec=metadata.EntryPoint)
        plugin_entry.name = "spam"
        plugin_model.add_entry_point(plugin_entry)
        assert (
            plugin_model.data(
                plugin_model.index(0),
                role=QtCore.Qt.ItemDataRole.CheckStateRole,
            )
            == QtCore.Qt.CheckState.Unchecked
        )

    @pytest.mark.parametrize(
        "role, attribute",
        [
            (models.PluginActivationModel.ModuleRole, "module"),
            (QtCore.Qt.ItemDataRole.DisplayRole, "name"),
        ],
    )
    def test_data_role(self, role, attribute):
        plugin_model = models.PluginActivationModel()
        plugin_entry = Mock(spec=metadata.EntryPoint)
        plugin_entry.name = "spam"

        plugin_model.add_entry_point(plugin_entry)
        assert plugin_model.data(plugin_model.index(0), role=role) == getattr(
            plugin_entry, attribute
        )


class TestTabsTreeModel:

    class SpamWorkflow(speedwagon.Workflow):
        name = "spam"
        description = "spam description"

    class BaconWorkflow(speedwagon.Workflow):
        name = "bacon"
        description = "bacon description"

    @pytest.fixture()
    def model(self):
        return models.TabsTreeModel()

    def test_add_empty_tab(self, qtbot, model):
        starting_amount = model.rowCount()
        model.append_workflow_tab("tab_name")
        ending_amount = model.rowCount()
        assert all((starting_amount == 0, ending_amount == 1)), (
            f"Should start with 0, got {starting_amount}. "
            f"Should end with 1, got {ending_amount}"
        )

    def test_add_workflow_tab_with_list_workflows(self, qtbot, model):
        starting_workflow_row_count = model.rowCount(model.index(0, 0))
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
                TestTabsTreeModel.BaconWorkflow,
            ],
        )
        ending_workflow_row_count = model.rowCount(model.index(0, 0))
        assert all(
            (
                starting_workflow_row_count == 0,
                ending_workflow_row_count == 2,
            )
        ), (
            f"Expected starting workflow row 0, "
            f"got {starting_workflow_row_count}. "
            f"Expected workflows in tab after adding 2, "
            f"got{ending_workflow_row_count}"
        )

    def test_get_tab_missing_returns_none(self, qtbot):
        model = models.TabsTreeModel()
        assert model.get_tab(tab_name="Not valid") is None

    def test_get_tab(self, qtbot, model):
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
            ],
        )
        assert model.get_tab("Dummy tab").name == "Dummy tab"

    def test_add_workflow(self, qtbot, model):
        model.append_workflow_tab("Dummy tab")
        assert model.rowCount(model.index(0, 0)) == 0
        model.append_workflow_to_tab(
            "Dummy tab", TestTabsTreeModel.SpamWorkflow
        )
        assert model.rowCount(model.index(0, 0)) == 1

    def test_tab_names(self, qtbot):
        model = models.TabsTreeModel()
        model.append_workflow_tab("Dummy tab")
        assert model.tab_names == ["Dummy tab"]

    def test_remove_row(self):
        model = models.TabsTreeModel()
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
                TestTabsTreeModel.BaconWorkflow,
            ],
        )
        assert model.rowCount() == 1
        model.removeRow(0)
        assert model.rowCount() == 0

    def test_get_item(self, qtbot, model):
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
                TestTabsTreeModel.BaconWorkflow,
            ],
        )
        tab_item: models.TabStandardItem = model.get_item(model.index(0, 0))
        assert all(
            [
                tab_item.child(0).name == "spam",
                tab_item.child(1).name == "bacon",
            ]
        ), (
            f'Expected child 0 to be "spam", got "{tab_item.child(0).name}". '
            f'Expected child 1 to be "bacon", got "{tab_item.child(1).name}".'
        )

    def test_modified(self, model):
        model.append_workflow_tab(
            "Dummy tab",
            [TestTabsTreeModel.SpamWorkflow, TestTabsTreeModel.BaconWorkflow],
        )
        assert model.data_modified is True

    def test_reset_modified(self, model):
        model.append_workflow_tab(
            "Dummy tab",
            [TestTabsTreeModel.SpamWorkflow, TestTabsTreeModel.BaconWorkflow],
        )
        model.reset_modified()
        assert model.data_modified is False

    def test_len_tabs(self, model):
        model.append_workflow_tab(
            "Dummy tab",
            [TestTabsTreeModel.SpamWorkflow, TestTabsTreeModel.BaconWorkflow],
        )
        assert len(model) == 1

    def test_index(self, model):
        model.append_workflow_tab(
            "Dummy tab",
            [TestTabsTreeModel.SpamWorkflow, TestTabsTreeModel.BaconWorkflow],
        )
        assert model[0].name == "Dummy tab"

    def test_invalid_index_raises(self):
        model = models.TabsTreeModel()
        with pytest.raises(IndexError):
            model[0]

    def test_modified_children(self, model):
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
            ],
        )
        model.reset_modified()
        dummy_tab = model[0]
        dummy_tab.append_workflow(TestTabsTreeModel.BaconWorkflow)
        assert model.data_modified is True

    def test_tab_information(self, model):
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
            ],
        )
        assert model.tab_information()[0].tab_name == "Dummy tab"

    @pytest.mark.parametrize(
        "top_row, sub_row, sub_column, expected_value",
        [
            (0, 0, 0, "spam"),
            (0, 1, 0, "bacon"),
            (0, 1, 1, "bacon description"),
        ],
    )
    def test_data(self, top_row, sub_row, sub_column, expected_value, model):
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
                TestTabsTreeModel.BaconWorkflow,
            ],
        )
        assert (
            model.data(
                model.index(
                    sub_row, sub_column, parent=model.index(top_row, 0)
                ),
            )
            == expected_value
        )

    def test_data_with_invalid_index_get_none(self, model):
        assert model.data(model.index(-1)) is None

    def test_data_with_WorkflowClassRole(self, model):
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
                TestTabsTreeModel.BaconWorkflow,
            ],
        )
        assert (
            model.data(
                model.index(0, 0, parent=model.index(0, 0)),
                role=models.WorkflowClassRole,
            )
            == TestTabsTreeModel.SpamWorkflow
        )

    @pytest.mark.parametrize(
        "section, expected_value",
        [
            (0, "Name"),
            (1, "Description"),
        ],
    )
    def test_header_data(self, section, expected_value, model):
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
            ],
        )
        assert (
            model.headerData(
                section,
                QtCore.Qt.Orientation.Horizontal,
                QtCore.Qt.ItemDataRole.DisplayRole,
            )
            == expected_value
        )

    def test_parent_no_child(self, model):
        assert model.parent().isValid() is False

    def test_parent_child_not_valid(self):
        model = models.TabsTreeModel()
        child = Mock(isValid=Mock(return_value=False))
        assert isinstance(model.parent(child), QtCore.QModelIndex)

    def test_parent_child_valid_child(self, model):
        model.get_item = Mock(return_value=models.TabStandardItem())
        child = Mock(isValid=Mock(return_value=True))
        assert isinstance(model.parent(child), QtCore.QModelIndex)

    def test_clear(self, model):
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
            ],
        )
        assert model.rowCount() == 1
        model.clear()
        assert model.rowCount() == 0

    def test_parent_not_valid_child(self, model):
        assert model.parent(model.index(-1, -1)).isValid() is False

    def test_set_data(self, model):
        index = model.index(0)
        assert (
            model.setData(
                index,
                value=self.SpamWorkflow,
                role=models.common.WorkflowClassRole,
            )
            is True
        )

    def test_set_data_text(self, model):
        index = model.index(0)
        assert (
            model.setData(
                index,
                value="Invalid data for this role",
                role=QtGui.Qt.ItemDataRole.CheckStateRole,
            )
            is False
        )

    def test_row_count_higher_column_parent(self, model):
        index = Mock(
            isValid=Mock(return_value=True), column=Mock(return_value=3)
        )
        assert model.rowCount(index) == 0


class TestTabStandardItem:
    class SpamWorkflow(speedwagon.Workflow):
        name = "spam"

    def test_append_increase_row_count(self):
        item = models.TabStandardItem()
        assert item.rowCount() == 0
        item.append_workflow(TestTabStandardItem.SpamWorkflow)
        assert item.rowCount() == 1

    def test_unable_to_append_workflow_already_added(self):

        item = models.TabStandardItem()
        assert item.rowCount() == 0
        item.append_workflow(TestTabStandardItem.SpamWorkflow)
        item.append_workflow(TestTabStandardItem.SpamWorkflow)
        assert item.rowCount() == 1

    def test_remove_decreases_row_count(self):

        item = models.TabStandardItem()
        item.append_workflow(TestTabStandardItem.SpamWorkflow)
        item.remove_workflow(TestTabStandardItem.SpamWorkflow)
        assert item.rowCount() == 0

    def test_data_changed(self, qtbot):

        item = models.TabStandardItem()
        model = QtGui.QStandardItemModel()
        model.appendRow(item)
        with qtbot.wait_signal(model.dataChanged):
            item.append_workflow(TestTabStandardItem.SpamWorkflow)


class TestWorkflowListProxyModel:

    class DummyWorkflow(speedwagon.Workflow):
        name = "dummy 1"

    class SpamWorkflow(speedwagon.Workflow):
        name = "Span"

    def test_name_no_model(self, qtbot):
        proxy_model = models.WorkflowListProxyModel()
        assert proxy_model.current_tab_name is None

    def test_invalid_set_by_name_raises(self, qtbot):
        base_model = models.TabsTreeModel()
        proxy_model = models.WorkflowListProxyModel()
        proxy_model.setSourceModel(base_model)
        with pytest.raises(ValueError):
            proxy_model.set_by_name("not a valid tab")

    @pytest.mark.parametrize("tab_name", (["Spam tab", "Bacon tab"]))
    def test_set_by_name(self, qtbot, tab_name):
        base_model = models.TabsTreeModel()

        base_model.append_workflow_tab(
            "Spam tab",
            [
                TestWorkflowListProxyModel.DummyWorkflow,
            ],
        )
        base_model.append_workflow_tab(
            "Bacon tab",
            [
                TestWorkflowListProxyModel.DummyWorkflow,
            ],
        )
        proxy_model = models.WorkflowListProxyModel()
        proxy_model.setSourceModel(base_model)
        proxy_model.set_by_name(tab_name)
        assert proxy_model.current_tab_name == tab_name

    def test_map_to_source(self, qtbot):
        base_model = models.TabsTreeModel()
        base_model.append_workflow_tab(
            "Dummy tab",
            [
                TestWorkflowListProxyModel.DummyWorkflow,
                TestWorkflowListProxyModel.SpamWorkflow,
            ],
        )
        item_index = base_model.index(0, 0, parent=base_model.index(0, 0))
        workflow_item: models.WorkflowItem = base_model.get_item(item_index)
        assert workflow_item.name == "dummy 1"

        proxy_model = models.WorkflowListProxyModel()
        proxy_model.setSourceModel(base_model)
        proxy_index = proxy_model.index(0, 0)
        assert proxy_model.data(proxy_index) == "dummy 1"
        assert proxy_model.mapToSource(proxy_index) == item_index

    def test_map_to_source_with_no_model_produces_index(self):
        proxy_model = models.WorkflowListProxyModel()
        assert isinstance(
            proxy_model.mapToSource(proxy_model.index(0, 0)),
            QtCore.QModelIndex,
        )

    def test_map_from_source_with_invalid_index_produces_index(self):
        proxy_model = models.WorkflowListProxyModel()
        proxy_index = Mock()
        proxy_index.isValid = Mock(return_value=False)
        assert isinstance(
            proxy_model.mapFromSource(proxy_index), QtCore.QModelIndex
        )

    def test_index_invalid_parent(self):
        base_model = models.TabsTreeModel()
        proxy_model = models.WorkflowListProxyModel()
        proxy_model.setSourceModel(base_model)
        parent = Mock(name="parent", isValid=Mock(return_value=True))
        assert isinstance(proxy_model.index(0, 0, parent), QtCore.QModelIndex)

    def test_map_from_source(self, qtbot):
        base_model = models.TabsTreeModel()
        base_model.append_workflow_tab(
            "Dummy tab",
            [TestTabProxyModel.DummyWorkflow, TestTabProxyModel.SpamWorkflow],
        )
        item_index = base_model.index(1, 0, parent=base_model.index(0, 0))
        workflow_item: models.WorkflowItem = base_model.get_item(item_index)
        assert workflow_item.name == "Spam"

        proxy_model = models.WorkflowListProxyModel()
        proxy_model.setSourceModel(base_model)
        proxy_index = proxy_model.index(1, 0)
        assert proxy_model.data(proxy_index) == "Spam"
        assert proxy_model.mapFromSource(item_index) == proxy_index

    def test_add_workflow(self):
        base_model = models.TabsTreeModel()
        base_model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabProxyModel.DummyWorkflow,
            ],
        )

        proxy_model = models.WorkflowListProxyModel()
        proxy_model.setSourceModel(base_model)
        proxy_model.set_by_name("Dummy tab")
        assert proxy_model.current_tab_name == "Dummy tab"
        proxy_model.add_workflow(TestTabProxyModel.SpamWorkflow)
        assert proxy_model.rowCount() == 2

    def test_row_count_no_source_model(self):
        proxy_model = models.WorkflowListProxyModel()
        assert proxy_model.rowCount() == 0

    def test_add_workflow_affects_source(self):
        base_model = models.TabsTreeModel()
        base_model.append_workflow_tab(
            "Dummy tab",
            [
                TestWorkflowListProxyModel.DummyWorkflow,
            ],
        )

        proxy_model = models.WorkflowListProxyModel()
        proxy_model.setSourceModel(base_model)
        proxy_model.set_by_name("Dummy tab")

        starting_row_count = base_model.rowCount(base_model.index(0, 0)) == 1
        proxy_model.add_workflow(TestWorkflowListProxyModel.SpamWorkflow)
        after_appending_row_count = base_model.rowCount(base_model.index(0, 0))

        expected = {
            "start row count": 1,
            "row count after proxy appends workflow": 2,
        }

        actual = {
            "start row count": starting_row_count,
            "row count after proxy appends workflow":
                after_appending_row_count,
        }
        assert expected == actual

    def test_remove_workflow(self):
        base_model = models.TabsTreeModel()
        base_model.append_workflow_tab(
            "Dummy tab",
            [
                TestWorkflowListProxyModel.DummyWorkflow,
            ],
        )

        proxy_model = models.WorkflowListProxyModel()
        proxy_model.setSourceModel(base_model)
        proxy_model.set_by_name("Dummy tab")
        assert proxy_model.current_tab_name == "Dummy tab"
        proxy_model.remove_workflow(TestWorkflowListProxyModel.DummyWorkflow)
        assert proxy_model.rowCount() == 0

    def test_set_index_without_a_model_is_a_noop(self, qtbot):
        proxy_model = models.WorkflowListProxyModel()
        with qtbot.assert_not_emitted(proxy_model.dataChanged):
            proxy_model.set_tab_index(0)

    def test_set_by_name_without_a_model_is_a_noop(self, qtbot):
        proxy_model = models.WorkflowListProxyModel()
        with qtbot.assert_not_emitted(proxy_model.dataChanged):
            proxy_model.set_by_name("spam")

    def test_row_count_for_no_model_is_zero(self):
        proxy_model = models.WorkflowListProxyModel()
        assert proxy_model.rowCount() == 0

    def test_column_count_for_no_model_is_zero(self):
        proxy_model = models.WorkflowListProxyModel()
        assert proxy_model.columnCount() == 0

    def test_column_count_for_any_model_is_one(self):
        main_model = models.TabsTreeModel()
        proxy_model = models.WorkflowListProxyModel()
        proxy_model.setSourceModel(main_model)
        assert proxy_model.columnCount() == 1

    def test_parent_q_object(self):
        proxy_model = models.WorkflowListProxyModel()
        assert isinstance(proxy_model.parent(), QtCore.QObject)

    def test_parent_index(self):
        proxy_model = models.WorkflowListProxyModel()
        index = proxy_model.createIndex(0, 0, 0)
        assert isinstance(proxy_model.parent(index), QtCore.QModelIndex)

    def test_append_workflow_without_a_model_is_a_runtime_error(self):
        proxy_model = models.WorkflowListProxyModel()
        with pytest.raises(RuntimeError):
            proxy_model.add_workflow(TestWorkflowListProxyModel.DummyWorkflow)

    def test_remove_workflow_without_a_model_is_a_runtime_error(self):
        proxy_model = models.WorkflowListProxyModel()
        with pytest.raises(RuntimeError):
            proxy_model.remove_workflow(
                TestWorkflowListProxyModel.DummyWorkflow
            )
class TestTabProxyModel:

    class DummyWorkflow(speedwagon.Workflow):
        name = "Dummy 1"

    class SpamWorkflow(speedwagon.Workflow):
        name = "Spam"

    @pytest.fixture()
    def base_model(self):
        return models.TabsTreeModel()

    def test_set_source_tab(self, base_model):

        base_model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabProxyModel.DummyWorkflow,
            ],
        )
        tab_model = models.TabProxyModel()

        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Dummy tab")

        assert tab_model.rowCount() == 1

    def test_mapFromSource(self, base_model):
        base_model.append_workflow_tab(
            "Dummy tab", [TestTabProxyModel.DummyWorkflow]
        )

        base_model.append_workflow_tab(
            "Spam tab", [TestTabProxyModel.SpamWorkflow]
        )
        tab_model = models.TabProxyModel()

        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Spam tab")
        source_index = base_model.index(0, 0, parent=base_model.index(1))
        assert tab_model.mapFromSource(source_index).row() == 0

    def test_mapFromSource_name(self, base_model):

        base_model.append_workflow_tab(
            "Dummy tab", [TestTabProxyModel.DummyWorkflow]
        )

        base_model.append_workflow_tab(
            "Spam tab", [TestTabProxyModel.SpamWorkflow]
        )

        tab_model = models.TabProxyModel()

        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Spam tab")

        source_index = base_model.index(0, 0, parent=base_model.index(1, 0))

        assert tab_model.data(tab_model.mapFromSource(source_index)) == "Spam"

    def test_mapToSource(self, base_model):

        base_model.append_workflow_tab(
            "Dummy tab", [TestTabProxyModel.DummyWorkflow]
        )

        base_model.append_workflow_tab(
            "Spam tab", [TestTabProxyModel.SpamWorkflow]
        )
        tab_model = models.TabProxyModel()

        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Spam tab")

        assert tab_model.mapToSource(
            tab_model.index(0, 0)
        ) == base_model.index(0, 0, parent=base_model.index(1))

    def test_add_workflow(self, base_model):
        base_model.append_workflow_tab(
            "Dummy tab", [TestTabProxyModel.DummyWorkflow]
        )

        tab_model = models.TabProxyModel()
        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Dummy tab")
        assert base_model.rowCount(base_model.index(0)) == 1
        tab_model.add_workflow(TestTabProxyModel.SpamWorkflow)
        assert base_model.rowCount(base_model.index(0)) == 2
        assert (
            base_model.data(base_model.index(1, 0, parent=base_model.index(0)))
            == "Spam"
        )

    def test_add_workflow_duplicates_is_noop(self, base_model):

        base_model.append_workflow_tab(
            "Dummy tab", [TestTabProxyModel.DummyWorkflow]
        )

        tab_model = models.TabProxyModel()
        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Dummy tab")
        assert base_model.rowCount(base_model.index(0)) == 1

        assert base_model.rowCount(base_model.index(0)) == 1
        tab_model.add_workflow(TestTabProxyModel.SpamWorkflow)
        tab_model.add_workflow(TestTabProxyModel.SpamWorkflow)
        tab_model.add_workflow(TestTabProxyModel.SpamWorkflow)
        assert base_model.rowCount(base_model.index(0)) == 2
        assert (
            base_model.data(base_model.index(1, 0, parent=base_model.index(0)))
            == "Spam"
        )

    def test_remove_workflow(self, base_model):

        base_model.append_workflow_tab(
            "Dummy tab", [TestTabProxyModel.DummyWorkflow]
        )

        tab_model = models.TabProxyModel()
        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Dummy tab")

        assert base_model.rowCount(base_model.index(0)) == 1
        tab_model.remove_workflow(TestTabProxyModel.DummyWorkflow)
        assert base_model.rowCount(base_model.index(0)) == 0

    def test_get_source_tab_index(self, base_model):
        base_model.append_workflow_tab(
            "Dummy tab", [TestTabProxyModel.DummyWorkflow]
        )
        tab_model = models.TabProxyModel()
        tab_model.setSourceModel(base_model)
        assert (
            base_model.data(tab_model.get_source_tab_index("Dummy tab"))
            == "Dummy tab"
        )

    def test_get_source_tab_index_invalid_index(self, base_model):
        tab_model = models.TabProxyModel()
        tab_model.setSourceModel(base_model)
        assert tab_model.get_source_tab_index("Dummy tab").isValid() is False

    def test_add_workflow_without_source_model_raises(self):
        tab_model = models.TabProxyModel()
        with pytest.raises(RuntimeError):
            tab_model.add_workflow(TestTabProxyModel.DummyWorkflow)

    def test_sort(self, base_model):
        base_model.append_workflow_tab(
            "Dummy tab",
            [
                self.SpamWorkflow,
                self.DummyWorkflow,
            ],
        )
        tab_model = models.TabProxyModel()
        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Dummy tab")
        assert tab_model.data(tab_model.index(0)) == "Spam"
        tab_model.sort(0, QtCore.Qt.SortOrder.AscendingOrder)
        assert tab_model.data(tab_model.index(0)) == "Dummy 1"

    def test_sort_noop_on_no_source_tab(self, base_model):
        base_model.append_workflow_tab(
            "Dummy tab",
            [
                self.SpamWorkflow,
                self.DummyWorkflow,
            ],
        )
        tab_model = models.TabProxyModel()
        tab_model.setSourceModel(base_model)
        tab_model.source_tab = None
        tab_model.sort(0)

    def test_sort_no_base_model(self):
        tab_model = models.TabProxyModel()
        tab_model.set_source_tab("invalid tab")
        tab_model.sort(0)


class TestWorkflowList:
    class SpamWorkflow(speedwagon.Workflow):
        name = "Spam"

    def test_add_workflow_adds_row(self):
        model = models.WorkflowList()
        assert model.rowCount() == 0
        model.add_workflow(TestWorkflowList.SpamWorkflow)
        assert model.rowCount() == 1

    def test_add_workflow_get_data(self):
        model = models.WorkflowList()
        assert model.rowCount() == 0
        model.add_workflow(TestWorkflowList.SpamWorkflow)
        assert model.data(model.index(0)) == "Spam"

    def test_insert(self):
        model = models.WorkflowList()
        model.insertRow(model.rowCount())
        assert model.rowCount() == 1

    def test_setData(self):
        model = models.WorkflowList()
        model.insertRow(model.rowCount())
        first_item_index = model.index(0, 0)
        model.setData(first_item_index, TestWorkflowList.SpamWorkflow)
        assert model.data(first_item_index) == "Spam"

    def test_remove(self):
        model = models.WorkflowList()
        model.insertRow(model.rowCount())
        assert model.rowCount() == 1
        model.removeRow(0)
        assert model.rowCount() == 0


class TestWorkflowSettingsModel:
    class SpamWorkflow(speedwagon.Workflow):
        name = "Spam"

        def workflow_options(
            self,
        ) -> List[speedwagon.workflow.AbsOutputOptionDataType]:

            return [
                speedwagon.workflow.TextLineEditData(
                    "Dummy config", required=True
                )
            ]

        def discover_task_metadata(
            self,
            initial_results: List[Any],
            additional_data: Dict[str, Any],
            **user_args,
        ) -> List[dict]:
            return []

    class BaconWorkflow(speedwagon.Workflow):
        name = "Bacon"

        def workflow_options(
            self,
        ) -> List[speedwagon.workflow.AbsOutputOptionDataType]:

            return [
                speedwagon.workflow.TextLineEditData(
                    "Bacon config 1", required=True
                ),
                speedwagon.workflow.TextLineEditData(
                    "Bacon config 2", required=True
                ),
            ]

        def discover_task_metadata(
            self,
            initial_results: List[Any],
            additional_data: Dict[str, Any],
            **user_args,
        ) -> List[dict]:
            return []

    class NoConfigWorkflow(speedwagon.Workflow):
        name = "Workflow that has no config options"

        def discover_task_metadata(
            self,
            initial_results: List[Any],
            additional_data: Dict[str, Any],
            **user_args,
        ) -> List[dict]:
            return []

    @pytest.fixture()
    def model(self):
        return WorkflowSettingsModel()

    def test_starting_column_count(self, model):
        assert model.columnCount() == 2

    def test_column_count(self, model):
        model.add_workflow(self.SpamWorkflow())
        assert model.columnCount() == 2

    def test_column_count_no_items(self, model):
        model.add_workflow(self.NoConfigWorkflow())
        model.add_workflow(self.SpamWorkflow())
        assert model.columnCount() == 2

    def test_column_count_child(self, model):
        model.add_workflow(self.SpamWorkflow())
        assert model.columnCount(model.index(0, 0)) == 2

    def test_starting_row_count(self, model):
        assert model.rowCount() == 0

    def test_row_count_after_adding(self, model, qtbot):
        model.add_workflow(self.SpamWorkflow())
        assert model.rowCount() == 1

    def test_row_count_with_parent_after_adding(self, model):
        model.add_workflow(self.BaconWorkflow())
        model.add_workflow(self.SpamWorkflow())
        index = model.index(0, 0)
        assert model.rowCount(index) == 2

    @pytest.mark.parametrize(
        "row, expected_column_count",
        [
            (0, 2),
            (1, 2),
        ],
    )
    def test_column_count_with_parent_after_adding(
        self, model, row, expected_column_count
    ):
        model.add_workflow(self.BaconWorkflow())
        model.add_workflow(self.SpamWorkflow())
        parent = model.index(row, 0)
        assert model.columnCount(parent) == expected_column_count

    def test_column_count_with_parent(self, model):
        model.add_workflow(self.BaconWorkflow())
        model.add_workflow(self.SpamWorkflow())
        parent = model.index(0, 0)
        index = model.index(0, 0, parent=parent)
        assert model.columnCount(index) == 2

    @pytest.mark.parametrize(
        "row, column, expected_text",
        [
            (0, 0, "Bacon"),
            (1, 0, "Spam"),
            (2, 0, None),
            (0, 1, None),
            (1, 1, None),
            (2, 1, None),
        ],
    )
    def test_data_display_top_level(self, model, row, column, expected_text):
        model.add_workflow(self.BaconWorkflow())
        model.add_workflow(self.SpamWorkflow())
        index = model.index(row, column)
        assert model.data(index) == expected_text

    @pytest.mark.parametrize(
        [
            "workflow_row",
            "workflow_column",
            "child_row",
            "child_column",
            "role",
            "expected_text",
        ],
        [
            (0, 0, 0, 0, QtCore.Qt.DisplayRole, "Bacon config 1"),
            (0, 0, 0, 0, QtCore.Qt.EditRole, "Bacon config 1"),
            (0, 0, 1, 0, QtCore.Qt.DisplayRole, "Bacon config 2"),
            (0, 0, 1, 0, QtCore.Qt.EditRole, "Bacon config 2"),
            (0, 0, 2, 0, QtCore.Qt.DisplayRole, None),
            (1, 0, 0, 0, QtCore.Qt.DisplayRole, "Dummy config"),
            (1, 0, 1, 0, QtCore.Qt.DisplayRole, None),
            (1, 0, 1, 0, QtCore.Qt.DisplayRole, None),
            (0, 1, 0, 0, QtCore.Qt.DisplayRole, None),
            (0, 1, 0, 1, QtCore.Qt.DisplayRole, None),
            (0, 1, 0, 2, QtCore.Qt.DisplayRole, None),
            (0, 1, 1, 0, QtCore.Qt.DisplayRole, None),
            (0, 1, 1, 1, QtCore.Qt.DisplayRole, None),
            (0, 1, 1, 2, QtCore.Qt.DisplayRole, None),
            (0, 2, 0, 0, QtCore.Qt.DisplayRole, None),
            (0, 2, 0, 1, QtCore.Qt.DisplayRole, None),
            (0, 2, 0, 2, QtCore.Qt.DisplayRole, None),
            (0, 0, 0, 1, QtCore.Qt.DisplayRole, None),
            (1, 0, 0, 1, QtCore.Qt.DisplayRole, None),
            (2, 0, 0, 0, QtCore.Qt.DisplayRole, None),
            (0, 1, 0, 0, QtCore.Qt.DisplayRole, None),
            (1, 1, 0, 0, QtCore.Qt.DisplayRole, None),
            (2, 1, 0, 0, QtCore.Qt.DisplayRole, None),
        ],
    )
    def test_data_display_one_level_down(
        self,
        model,
        workflow_row,
        workflow_column,
        child_row,
        child_column,
        role,
        expected_text,
    ):
        model.add_workflow(self.BaconWorkflow())
        model.add_workflow(self.SpamWorkflow())
        parent_index = model.index(workflow_row, workflow_column)
        index = model.index(child_row, child_column, parent=parent_index)
        model.data(index, role=role) == expected_text

    def test_index_without_anything(self, model):
        index = model.index(0, 0)
        assert index.isValid() is False

    @pytest.mark.parametrize(
        "index_values, expected",
        [
            ((0, 0), True),
            ((0, 1), True),
        ],
    )
    def test_index_workflow_level(self, model, index_values, expected):
        model.add_workflow(self.SpamWorkflow())
        index = model.index(*index_values)
        assert index.isValid() is expected

    @pytest.mark.parametrize(
        "workflow_options_index_values, expected",
        [
            ((0, 0), True),
            ((1, 0), False),
        ],
    )
    def test_index_options_level(
        self, model, workflow_options_index_values, expected
    ):
        model.add_workflow(self.SpamWorkflow())
        parent_index = model.index(0, 0)
        index = model.index(
            *workflow_options_index_values, parent=parent_index
        )
        assert (
            index.isValid() is expected
        ), f"data for model = {model.data(index)}"

    @pytest.mark.parametrize(
        "column, expected_valid", [(0, True), (1, True), (2, False)]
    )
    def test_second_level_index(self, model, column, expected_valid):
        model.add_workflow(self.SpamWorkflow())
        parent = model.index(0, 0)
        index = model.index(0, column, parent=parent)
        assert (
            index.isValid() is expected_valid
        ), f"data for model = {model.data(index)}"

    def test_add_workflow(self, model):
        model.add_workflow(self.SpamWorkflow())
        assert model.rowCount() == 1

    def test_remove_workflow(self, model):
        workflow = self.SpamWorkflow()
        model.add_workflow(workflow)
        assert model.rowCount() == 1
        model.remove_workflow(workflow)
        assert model.rowCount() == 0

    @pytest.mark.parametrize(
        "column,expected_value", [(0, "Spam"), (1, None), (2, None)]
    )
    def test_top_level_data(self, model, column, expected_value):
        model.add_workflow(self.SpamWorkflow())
        assert model.data(model.index(0, column)) == expected_value

    @pytest.mark.parametrize(
        "index_values, parent_index_values, expected_value",
        [
            ((0, 0), None, "Spam"),
            ((0, 1), None, None),
            ((0, 2), None, None),
            ((0, 0), (0, 0), "Dummy config"),
        ],
    )
    def test_data(
        self, model, index_values, parent_index_values, expected_value
    ):
        model.add_workflow(self.SpamWorkflow())
        parent_index = (
            model.index(*parent_index_values)
            if parent_index_values is not None
            else QtCore.QModelIndex()
        )
        index = model.index(*index_values, parent=parent_index)
        assert model.data(index) == expected_value

    def test_second_level(self, model):
        model.add_workflow(self.SpamWorkflow())
        workflow_index = model.index(0, 0)
        workflow_metadata_data_index = model.index(0, 0, parent=workflow_index)
        assert model.data(workflow_metadata_data_index) == "Dummy config"

    def test_setting(self, model):
        backend = Mock(
            get=lambda key: "foo" if key == "Dummy config" else None
        )
        workflow = self.SpamWorkflow()
        workflow.set_options_backend(backend)
        model.add_workflow(workflow)
        workflow_index = model.index(0, 0)
        workflow_metadata_data_index = model.index(0, 1, parent=workflow_index)
        assert model.data(workflow_metadata_data_index) == "foo"

    def test_items_with_settings(self, model):
        assert model.rowCount() == 0
        model.add_workflow(self.SpamWorkflow())
        assert model.rowCount() == 1
        model.add_workflow(self.NoConfigWorkflow())
        assert model.rowCount() == 2

    @pytest.mark.parametrize(
        "workflow, expected",
        [(SpamWorkflow(), True), (NoConfigWorkflow(), False)],
    )
    def test_has_children(self, model, workflow, expected):
        model.add_workflow(workflow)
        assert model.hasChildren(model.index(0, 0)) is expected
        assert model.hasChildren(model.index(0, 0)) is expected

    def test_has_children_root(self, model):
        model.add_workflow(self.SpamWorkflow())
        assert model.hasChildren() is True

    def test_clear(self, model):
        model.add_workflow(self.SpamWorkflow())
        assert model.rowCount() == 1
        model.clear()
        assert model.rowCount() == 0

    @pytest.mark.parametrize(
        "workflow, expected_display",
        [
            (SpamWorkflow(), "Spam"),
            (NoConfigWorkflow(), "Workflow that has no config options"),
            (BaconWorkflow(), "Bacon"),
        ],
    )
    def test_data_name(self, model, workflow, expected_display):
        model.add_workflow(workflow)
        assert model.data(model.index(0, 0)) == expected_display

    def test_data_name_multiple_workflows(self, model):
        model.add_workflow(self.SpamWorkflow())
        model.add_workflow(self.NoConfigWorkflow())
        index = model.index(1, 0)
        assert model.data(index) == "Workflow that has no config options"

    @pytest.mark.parametrize(
        "expected_flags, index, parent_index",
        [
            (QtCore.Qt.ItemFlag.ItemIsEnabled, (0, 0), None),
            (QtCore.Qt.ItemFlag.ItemIsEnabled, (0, 1), None),
            (
                (
                    QtCore.Qt.ItemFlag.ItemIsEnabled
                    and QtCore.Qt.ItemFlag.ItemIsSelectable
                    and QtCore.Qt.ItemFlag.ItemIsEditable
                ),
                (0, 1),
                (0, 0),
            ),
            (
                (
                    QtCore.Qt.ItemFlag.ItemIsEnabled
                    and QtCore.Qt.ItemFlag.ItemIsSelectable
                ),
                (0, 0),
                (0, 0),
            ),
        ],
    )
    def test_flags(self, model, expected_flags, index, parent_index):
        model.add_workflow(self.SpamWorkflow())
        if parent_index is not None:
            index = model.index(*index, parent=model.index(*parent_index))
        else:
            index = model.index(*index)
        assert expected_flags in model.flags(index)

    @pytest.mark.parametrize(
        ["section", "orientation", "role", "expected"],
        [
            (
                0,
                QtCore.Qt.Orientation.Horizontal,
                QtCore.Qt.DisplayRole,
                "Property",
            ),
            (0, QtCore.Qt.Orientation.Vertical, QtCore.Qt.DisplayRole, 1),
            (
                1,
                QtCore.Qt.Orientation.Horizontal,
                QtCore.Qt.DisplayRole,
                "Value",
            ),
            (1, QtCore.Qt.Orientation.Vertical, QtCore.Qt.DisplayRole, None),
        ],
    )
    def test_header_data(self, model, section, orientation, role, expected):
        model.add_workflow(self.SpamWorkflow())
        assert model.headerData(section, orientation, role=role) == expected

    def test_index(self, model):
        model.add_workflow(self.SpamWorkflow())
        workflow_index = model.index(0, 0)
        assert workflow_index.isValid()
        option_index = model.index(0, 0, parent=workflow_index)
        assert option_index.isValid()
        is_parent_valid = option_index.parent().isValid()
        assert is_parent_valid is True

    def test_set_data_updates_settings(self, model):
        model.add_workflow(self.SpamWorkflow())
        index = model.index(0, 1, parent=model.index(0, 0))
        model.setData(index, "new edits")
        assert model.data(index) == "new edits"

    def test_set_data_calls_data_changed(self, model, qtbot):
        model.add_workflow(self.SpamWorkflow())
        index = model.index(0, 1, parent=model.index(0, 0))
        with qtbot.wait_signal(model.dataChanged):
            model.setData(index, "new edits")

    @pytest.mark.parametrize(
        "expected_valid, index, parent_index",
        [
            (True, (0, 1), (0, 0)),
            (False, (0, 0), (0, 0)),
            (False, (0, 1), None),
            (False, (1, 0), None),
        ],
    )
    def test_set_data_valid_indexes(
        self, model, expected_valid, index, parent_index
    ):
        model.add_workflow(self.SpamWorkflow())
        if parent_index is None:
            index = model.index(*index)
        else:
            index = model.index(*index, parent=model.index(*parent_index))
        assert model.setData(index, "new edits") is expected_valid

    def test_workflows(self, model):
        model.add_workflow(self.SpamWorkflow())
        assert len(model.workflows) == 1

    def test_results(self, model):
        model.add_workflow(self.SpamWorkflow())
        index = model.index(0, 1, parent=model.index(0, 0))
        model.setData(index, "new edits")
        assert model.results() == {"Spam": {"Dummy config": "new edits"}}

    def test_not_modified_by_default(self, model):
        assert model.modified() is False

    def test_modified_is_true_if_added_workflow(self, model):
        model.add_workflow(self.SpamWorkflow())
        assert model.modified() is True

    def test_not_modified_by_after_reset(self, model):
        model.add_workflow(self.SpamWorkflow())
        model.reset_modified()
        assert model.modified() is False


class TestWorkflowSettingsMetadata:
    @pytest.fixture()
    def empty_model(self):
        return models.settings.WorkflowSettingsMetadata()

    def test_child(self, empty_model):
        child = Mock(name="child_item")
        model = empty_model
        model.child_items.append(child)
        assert model.child(0) == child

    def test_invalid_child(self, empty_model):
        assert empty_model.child(0) is None

    def test_label(self, empty_model):
        model = empty_model
        model.option = workflow.BooleanSelect(label="Spam")
        assert model.label == "Spam"

    def test_label_is_none_on_when_no_options(self, empty_model):
        model = empty_model
        model.option = None
        assert model.label is None

    def test_insert_child_returns_false(self, empty_model):
        assert empty_model.insert_children(0, 1, 0) is False

    def test_remove_child_returns_false(self, empty_model):
        assert empty_model.remove_children(0, 1) is False

    def test_child_number_with_no_parent_is_zero(self, empty_model):
        assert empty_model.child_number() == 0

    def test_child_number(self):
        parent_model = models.settings.WorkflowSettingsItemWorkflow()
        other_item = models.settings.WorkflowSettingsMetadata(
            parent=parent_model
        )
        model = models.settings.WorkflowSettingsMetadata(parent=parent_model)
        parent_model.child_items.append(other_item)
        parent_model.child_items.append(model)
        assert model.child_number() == 1

    def test_last_child(self, empty_model):
        model = empty_model
        child_item = Mock(name="child item")
        model.child_items.append(child_item)
        assert model.last_child() == child_item


class TestWorkflowSettingsRoot:
    @pytest.fixture()
    def model(self):
        return models.settings.WorkflowSettingsRoot()

    def test_insert_children_invalid_index_returns_false(self, model):
        assert model.insert_children(-1, 0, 0) is False

    def test_data_column_none_data_role(self, model):
        assert model.data_column(0, QtCore.Qt.ItemDataRole.FontRole) is None

    def test_data_column_invalid_column(self, model):
        assert model.data_column(-1) is None

    def test_data_column(self, model):
        assert model.data_column(0) == "Property"

    def test_flags(self, model):
        assert (
            model.flags(Mock(name="index")) == QtCore.Qt.ItemFlag.NoItemFlags
        )

    def test_data_invalid_index_is_none(self, model):
        assert model.data(-1) is None

    def test_parent(self, model):
        parent = Mock(name="parent")
        model.parent_item = parent
        assert model.parent() == parent

    def test_child_number_defaults_to_zero(self):
        model = models.settings.WorkflowSettingsRoot()
        assert model.child_number() == 0


class TestWorkflowSettingsItemWorkflow:
    @pytest.fixture()
    def model(self):
        return models.settings.WorkflowSettingsItemWorkflow()

    def test_remove_children(self, model):
        model.child_items.append(Mock())
        model.remove_children(0, 1)
        assert len(model.child_items) == 0

    def test_remove_children_when_empty_returns_false(self, model):
        assert model.remove_children(0, 1) is False


class TestItemsModel:
    @pytest.fixture()
    def column_names(self):
        return ["one", "two"]

    @pytest.fixture()
    def model(self, column_names):
        return models.ItemTableModel(keys=column_names)

    def test_columns(self, model, column_names):
        assert model.columnCount() == len(column_names)

    def test_column_names(self, model, column_names):
        assert (
            model.headerData(0, QtCore.Qt.Orientation.Horizontal)
            == column_names[0]
        )

    def test_row_add(self, model):
        assert model.rowCount() == 0
        model.add_item(("A", "B"))
        assert model.rowCount() == 1

    def test_row_editable(self, model):
        assert model.rowCount() == 0
        model.add_item(("A", "B"))
        model.is_editable_rule = lambda *args: True
        assert QtCore.Qt.ItemFlag.ItemIsEditable in model.flags(
            model.index(0, 0)
        )

    def test_row_not_editable_by_default(self, model):
        model.add_item(("A", "B"))
        assert QtCore.Qt.ItemFlag.ItemIsEditable not in model.flags(
            model.index(0, 0)
        )

    def test_display_data(self, model):
        model.add_item(("A", "B"))
        model.display_role = lambda row, index: row[index.row()]
        assert model.data(model.index(0, 0)) == "A"

    def test_option_role(self, model):
        model.add_item(("A", "B"))
        selections = ["1", "2"]
        model.options_role = lambda *args: selections
        assert (
            model.data(model.index(0, 0), role=model.OptionsRole) == selections
        )

    def test_set_data(self, model):
        model.add_item(("A", "B"))

        def update(value, existing_row, index):
            data = list(existing_row)
            data[index.row()] = value
            return tuple(data)

        model.update_data = update
        model.display_role = lambda item, index: str(item[index.row()])

        index = model.index(0, 0)
        assert model.data(index) == "A"
        assert model.setData(index, "C") is True
        assert model.data(index) == "C"

    def test_set_data_no_change(self, model):
        model.add_item(("A", "B"))

        def update(value, existing_row, index):
            data = list(existing_row)
            data[index.row()] = value
            return tuple(data)

        model.update_data = update
        model.display_role = lambda item, index: str(item[index.row()])

        index = model.index(0, 0)
        assert model.data(index) == "A"
        assert model.setData(index, "A") is False

    def test_results(self, model):
        model.add_item(("A", "B"))
        expected_result = {}
        model.process_results = lambda *args: expected_result
        assert model.results() == expected_result
