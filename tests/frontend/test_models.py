import configparser
import json
import os
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


def test_build_setting_model_missing_file(tmpdir):
    dummy = str(os.path.join(tmpdir, "config.ini"))
    with pytest.raises(FileNotFoundError):
        models.build_setting_qt_model(dummy)


class TestSettingsModel:
    @pytest.mark.parametrize("role", [
        QtCore.Qt.DisplayRole,
        QtCore.Qt.EditRole,
    ])
    def test_data(self, role):
        model = models.SettingsModel(None)
        model.add_setting("spam", "eggs")
        assert model.data(model.index(0, 0), role=role) == "spam"

    @pytest.mark.parametrize("index, expected", [
        (0, "Key"),
        (1, "Value"),
    ])
    def test_header_data(self, index, expected):
        model = models.SettingsModel(None)
        value = model.headerData(index,
                                 QtCore.Qt.Horizontal,
                                 role=QtCore.Qt.DisplayRole)

        assert value == expected

    def test_set_data(self):
        model = models.SettingsModel(None)
        model.add_setting("spam", "eggs")
        model.setData(model.index(0, 0), data="dumb")
        assert model._data[0][1] == "dumb"

    @pytest.mark.parametrize("column, expected", [
        (0, QtCore.Qt.NoItemFlags),
        (1, QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable),
    ])
    def test_flags(self, column, expected):
        model = models.SettingsModel(None)
        model.add_setting("spam", "eggs")
        flags = model.flags(model.index(0, column))
        assert flags == expected

    def test_settings_model_empty(self):
        test_model = models.SettingsModel()
        assert test_model.rowCount() == 0
        assert test_model.columnCount() == 2
        index = test_model.index(0, 0)
        assert index.data() is None

    def test_settings_model_added(self):
        test_model = models.SettingsModel()
        test_model.add_setting("mysetting", "eggs")
        assert test_model.rowCount() == 1
        assert test_model.columnCount() == 2
        assert test_model.index(0, 0).data() == "mysetting"
        assert test_model.index(0, 1).data() == "eggs"

        index = test_model.index(0, 1)
        assert test_model.data(index) is None

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
            QtWidgets.QHeaderView.Stretch)
        v_header = table.verticalHeader()
        v_header.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        v_header.setSectionsClickable(False)
        v_header.setDefaultSectionSize(25)

        qtbot.addWidget(table)
        return table

    @pytest.fixture
    def data(self):
        checksum_select = workflow.FileSelectData('Checksum File')
        checksum_select.filter = "Checksum files (*.md5)"

        options = workflow.ChoiceSelection('Order')
        options.add_selection("Bacon")
        options.add_selection("Bacon eggs")
        options.add_selection("Spam")

        return [
            checksum_select,
            options,
            workflow.DirectorySelect('Eggs')
        ]

    def test_headings(self, qtbot, data):
        model = models.ToolOptionsModel4(data)
        heading = model.headerData(0,
                                   QtCore.Qt.Vertical,
                                   QtCore.Qt.DisplayRole)

        assert heading == data[0].label

    def test_horizontal_heading_are_empty(self, data):
        model = models.ToolOptionsModel4(data)
        heading = model.headerData(0,
                                   QtCore.Qt.Horizontal,
                                   QtCore.Qt.DisplayRole)
        assert heading is None

    def test_rows_match_data_size(self, qtbot, data):
        model = models.ToolOptionsModel4(data)
        assert model.rowCount() == len(data)

    def test_data_json_role_make_parseable_data(self, data):
        model = models.ToolOptionsModel4(data)
        index = model.index(0, 0)

        json_string = model.data(
            index,
            role=models.ToolOptionsModel4.JsonDataRole
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


def test_check_required_settings_have_values_not_required_returns_nothing():
    option_data = Mock(workflow.AbsOutputOptionDataType, required=False)
    result = models.check_required_settings_have_values(option_data)
    assert result is None


def test_check_required_settings_have_values_required_and_has_value_returns_nothing():
    option_data = Mock(workflow.AbsOutputOptionDataType, required=True)
    option_data.value = "something"
    result = models.check_required_settings_have_values(option_data)
    assert result is None


def test_build_setting_model(tmpdir):

    dummy = str(os.path.join(tmpdir, "config.ini"))
    empty_config_data = """[GLOBAL]
debug: False
        """
    with open(dummy, "w") as wf:
        wf.write(empty_config_data)
    model = models.build_setting_qt_model(dummy)
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
        value = plugin_model.data(plugin_model.index(0), QtCore.Qt.ItemDataRole.DisplayRole)
        assert "spam" in value

    @pytest.mark.parametrize(
        "expected_flag",
        [
            QtCore.Qt.ItemFlag.ItemIsUserCheckable,
            QtCore.Qt.ItemFlag.ItemIsSelectable,
            QtCore.Qt.ItemFlag.ItemIsEnabled,
         ]
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
        assert \
            plugin_model.data(
                plugin_model.index(0),
                role=QtCore.Qt.ItemDataRole.CheckStateRole
            ) == QtCore.Qt.CheckState.Unchecked

    @pytest.mark.parametrize(
        "role, attribute",
        [
            (models.PluginActivationModel.ModuleRole, "module"),
            (QtCore.Qt.ItemDataRole.DisplayRole, "name"),
        ]
    )
    def test_data_role(self, role, attribute):
        plugin_model = models.PluginActivationModel()
        plugin_entry = Mock(spec=metadata.EntryPoint)
        plugin_entry.name = "spam"

        plugin_model.add_entry_point(plugin_entry)
        assert \
            plugin_model.data(
                plugin_model.index(0),
                role=role
            ) == getattr(plugin_entry, attribute)


class TestTabsTreeModel:

    class SpamWorkflow(speedwagon.Workflow):
        name = "spam"
        description = "spam description"

    class BaconWorkflow(speedwagon.Workflow):
        name = "bacon"
        description = "bacon description"

    def test_add_empty_tab(self, qtbot):
        model = models.TabsTreeModel()
        starting_amount = model.rowCount()
        model.append_workflow_tab("tab_name")
        ending_amount = model.rowCount()
        assert all(
            (
                starting_amount == 0,
                ending_amount == 1
            )
        ), f"Should start with 0, got {starting_amount}. " \
           f"Should end with 1, got {ending_amount}"

    def test_add_workflow_tab_with_list_workflows(self, qtbot):
        model = models.TabsTreeModel()
        starting_workflow_row_count = model.rowCount(model.index(0, 0))
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
                TestTabsTreeModel.BaconWorkflow,
            ]
        )
        ending_workflow_row_count = model.rowCount(model.index(0, 0))
        assert all(
            (
                starting_workflow_row_count == 0,
                ending_workflow_row_count == 2,
            )
        ), f"Expected starting workflow row 0, got {starting_workflow_row_count}. " \
           f"Expected workflows in tab after adding 2, got{ending_workflow_row_count}"

    def test_get_tab_missing_returns_none(self, qtbot):
        model = models.TabsTreeModel()
        assert model.get_tab(tab_name="Not valid") is None

    def test_get_tab(self, qtbot):
        model = models.TabsTreeModel()

        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
            ]
        )
        assert model.get_tab("Dummy tab").name == "Dummy tab"

    def test_add_workflow(self, qtbot):
        model = models.TabsTreeModel()
        model.append_workflow_tab("Dummy tab")
        assert model.rowCount(model.index(0, 0)) == 0
        model.append_workflow_to_tab(
            "Dummy tab",
            TestTabsTreeModel.SpamWorkflow
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
            ]
        )
        assert model.rowCount() == 1
        model.removeRow(0)
        assert model.rowCount() == 0

    def test_get_item(self, qtbot):
        model = models.TabsTreeModel()
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
                TestTabsTreeModel.BaconWorkflow,
            ]
        )
        tab_item: models.TabStandardItem = model.get_item(model.index(0,0))
        assert all(
         [
             tab_item.child(0).name == "spam",
             tab_item.child(1).name == "bacon"
         ]
        ), f'Expected child 0 to be "spam", got "{tab_item.child(0).name}". ' \
           f'Expected child 1 to be "bacon", got "{tab_item.child(1).name}".'

    def test_modified(self):
        model = models.TabsTreeModel()
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
                TestTabsTreeModel.BaconWorkflow
            ]
        )
        assert model.data_modified is True

    def test_reset_modified(self):
        model = models.TabsTreeModel()
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
                TestTabsTreeModel.BaconWorkflow
            ]
        )
        model.reset_modified()
        assert model.data_modified is False

    def test_len_tabs(self):
        model = models.TabsTreeModel()
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
                TestTabsTreeModel.BaconWorkflow
            ]
        )
        assert len(model) == 1

    def test_index(self):

        model = models.TabsTreeModel()
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
                TestTabsTreeModel.BaconWorkflow
            ]
        )
        assert model[0].name == "Dummy tab"

    def test_invalid_index_raises(self):
        model = models.TabsTreeModel()
        with pytest.raises(IndexError):
            model[0]

    def test_modified_children(self):
        model = models.TabsTreeModel()
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
            ]
        )
        model.reset_modified()
        dummy_tab = model[0]
        dummy_tab.append_workflow(TestTabsTreeModel.BaconWorkflow)
        assert model.data_modified is True

    def test_tab_information(self):
        model = models.TabsTreeModel()
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
            ]
        )
        assert model.tab_information()[0].tab_name == "Dummy tab"

    @pytest.mark.parametrize(
        "top_row, sub_row, sub_column, expected_value",
        [
            (0, 0, 0, "spam"),
            (0, 1, 0, "bacon"),
            (0, 1, 1, "bacon description"),
        ]
    )
    def test_data(self, top_row, sub_row, sub_column, expected_value):
        model = models.TabsTreeModel()
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
                TestTabsTreeModel.BaconWorkflow,
            ]
        )
        assert model.data(
            model.index(sub_row, sub_column, parent=model.index(top_row, 0)),
        ) == expected_value

    def test_data_with_invalid_index_get_none(self):
        model = models.TabsTreeModel()
        assert model.data(model.index(-1)) is None

    def test_data_with_WorkflowClassRole(self):
        model = models.TabsTreeModel()
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
                TestTabsTreeModel.BaconWorkflow,
            ]
        )
        assert model.data(
            model.index(0, 0, parent=model.index(0, 0)),
            role=models.TabsTreeModel.WorkflowClassRole
        ) == TestTabsTreeModel.SpamWorkflow

    @pytest.mark.parametrize(
        "section, expected_value",
        [
            (0, "Name"),
            (1, "Description"),
        ]
    )
    def test_header_data(self, section, expected_value):

        model = models.TabsTreeModel()
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
            ]
        )
        assert \
            model.headerData(
                section,
                QtCore.Qt.Orientation.Horizontal,
                QtCore.Qt.ItemDataRole.DisplayRole
            ) == expected_value

    def test_parent_no_child(self):
        model = models.TabsTreeModel()
        assert model.parent().isValid() is False

    def test_parent_child_not_valid(self):
        model = models.TabsTreeModel()
        child = Mock(isValid=Mock(return_value=False))
        assert isinstance(model.parent(child), QtCore.QModelIndex)

    def test_parent_child_valid_child(self):
        model = models.TabsTreeModel()
        model.get_item = Mock(return_value=models.TabStandardItem())
        child = Mock(isValid=Mock(return_value=True))
        assert isinstance(model.parent(child), QtCore.QModelIndex)

    def test_clear(self):
        model = models.TabsTreeModel()
        model.append_workflow_tab(
            "Dummy tab",
            [
                TestTabsTreeModel.SpamWorkflow,
            ]
        )
        assert model.rowCount() == 1
        model.clear()
        assert model.rowCount() == 0


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

    @pytest.mark.parametrize(
        "tab_name",
        (
            [
                "Spam tab",
                "Bacon tab"
            ]
        )
    )
    def test_set_by_name(self, qtbot, tab_name):
        base_model = models.TabsTreeModel()

        base_model.append_workflow_tab(
            "Spam tab",
            [
                TestWorkflowListProxyModel.DummyWorkflow,
            ]
        )
        base_model.append_workflow_tab(
            "Bacon tab",
            [
                TestWorkflowListProxyModel.DummyWorkflow,
            ]
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
            ]
        )
        item_index = base_model.index(0,0, parent=base_model.index(0,0))
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
            proxy_model.mapToSource(proxy_model.index(0,0)),
            QtCore.QModelIndex
        )

    def test_map_from_source_with_invalid_index_produces_index(self):
        proxy_model = models.WorkflowListProxyModel()
        proxy_index = Mock()
        proxy_index.isValid = Mock(return_value=False)
        assert isinstance(
            proxy_model.mapFromSource(proxy_index),
            QtCore.QModelIndex
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
            [
                TestTabProxyModel.DummyWorkflow,
                TestTabProxyModel.SpamWorkflow
            ]
        )
        item_index = base_model.index(1,0, parent=base_model.index(0,0))
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
            ]
        )

        proxy_model = models.WorkflowListProxyModel()
        proxy_model.setSourceModel(base_model)
        proxy_model.set_by_name("Dummy tab")
        assert proxy_model.current_tab_name == "Dummy tab"
        proxy_model.add_workflow(TestTabProxyModel.SpamWorkflow)
        assert proxy_model.rowCount() == 2

    def test_add_workflow_affects_source(self):
        base_model = models.TabsTreeModel()
        base_model.append_workflow_tab(
            "Dummy tab",
            [
                TestWorkflowListProxyModel.DummyWorkflow,
            ]
        )

        proxy_model = models.WorkflowListProxyModel()
        proxy_model.setSourceModel(base_model)
        proxy_model.set_by_name("Dummy tab")

        starting_row_count = base_model.rowCount(base_model.index(0,0)) == 1
        proxy_model.add_workflow(TestWorkflowListProxyModel.SpamWorkflow)
        after_appending_row_count = base_model.rowCount(base_model.index(0,0))

        expected = {
            "start row count": 1,
            "row count after proxy appends workflow": 2
        }

        actual = {
            "start row count": starting_row_count,
            "row count after proxy appends workflow": after_appending_row_count
        }
        assert expected == actual

    def test_remove_workflow(self):
        base_model = models.TabsTreeModel()
        base_model.append_workflow_tab(
            "Dummy tab",
            [
                TestWorkflowListProxyModel.DummyWorkflow,
            ]
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
            proxy_model.remove_workflow(TestWorkflowListProxyModel.DummyWorkflow)


class TestTabProxyModel:
    class DummyWorkflow(speedwagon.Workflow):
        name = "dummy 1"

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
            ]
        )
        tab_model = models.TabProxyModel()

        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Dummy tab")

        assert tab_model.rowCount() == 1

    def test_mapFromSource(self, base_model):
        base_model.append_workflow_tab(
            "Dummy tab",
            [TestTabProxyModel.DummyWorkflow]
        )

        base_model.append_workflow_tab(
            "Spam tab",
            [TestTabProxyModel.SpamWorkflow]
        )
        tab_model = models.TabProxyModel()

        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Spam tab")
        source_index = base_model.index(0,0, parent=base_model.index(1))
        assert tab_model.mapFromSource(source_index).row() == 0

    def test_mapFromSource_name(self, base_model):

        base_model.append_workflow_tab(
            "Dummy tab",
            [TestTabProxyModel.DummyWorkflow]
        )

        base_model.append_workflow_tab(
            "Spam tab",
            [TestTabProxyModel.SpamWorkflow]
        )

        tab_model = models.TabProxyModel()

        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Spam tab")

        source_index = base_model.index(0, 0, parent=base_model.index(1, 0))

        assert tab_model.data(tab_model.mapFromSource(source_index)) == "Spam"

    def test_mapToSource(self, base_model):

        base_model.append_workflow_tab(
            "Dummy tab",
            [TestTabProxyModel.DummyWorkflow]
        )

        base_model.append_workflow_tab(
            "Spam tab",
            [TestTabProxyModel.SpamWorkflow]
        )
        tab_model = models.TabProxyModel()

        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Spam tab")

        assert tab_model.mapToSource(
            tab_model.index(0, 0)
        ) == base_model.index(0,0, parent=base_model.index(1))

    def test_add_workflow(self, base_model):
        base_model.append_workflow_tab(
            "Dummy tab",
            [TestTabProxyModel.DummyWorkflow]
        )

        tab_model = models.TabProxyModel()
        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Dummy tab")
        assert base_model.rowCount(base_model.index(0)) == 1
        tab_model.add_workflow(TestTabProxyModel.SpamWorkflow)
        assert base_model.rowCount(base_model.index(0)) == 2
        assert base_model.data(base_model.index(1, 0, parent=base_model.index(0))) == "Spam"

    def test_add_workflow_duplicates_is_noop(self, base_model):

        base_model.append_workflow_tab(
            "Dummy tab",
            [TestTabProxyModel.DummyWorkflow]
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
        assert base_model.data(base_model.index(1, 0, parent=base_model.index(0))) == "Spam"

    def test_remove_workflow(self, base_model):

        base_model.append_workflow_tab(
            "Dummy tab",
            [TestTabProxyModel.DummyWorkflow]
        )

        tab_model = models.TabProxyModel()
        tab_model.setSourceModel(base_model)
        tab_model.set_source_tab("Dummy tab")

        assert base_model.rowCount(base_model.index(0)) == 1
        tab_model.remove_workflow(TestTabProxyModel.DummyWorkflow)
        assert base_model.rowCount(base_model.index(0)) == 0

    def test_get_source_tab_index(self, base_model):
        base_model.append_workflow_tab(
            "Dummy tab",
            [TestTabProxyModel.DummyWorkflow]
        )
        tab_model = models.TabProxyModel()
        tab_model.setSourceModel(base_model)
        assert base_model.data(
            tab_model.get_source_tab_index("Dummy tab")
        ) == "Dummy tab"

    def test_add_workflow_without_source_model_raises(self):
        tab_model = models.TabProxyModel()
        with pytest.raises(RuntimeError):
            tab_model.add_workflow(TestTabProxyModel.DummyWorkflow)


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