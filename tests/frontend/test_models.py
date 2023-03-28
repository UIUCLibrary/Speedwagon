import configparser
import json
import os
from unittest.mock import Mock
import sys
if sys.version_info < (3, 10):
    import importlib_metadata as metadata
else:
    from importlib import metadata

from speedwagon import job, workflow

import pytest
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QtCore = pytest.importorskip("PySide6.QtCore")

import speedwagon.config
from speedwagon.frontend.qtwidgets import tabs, models

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


class TestTabsModel:
    def test_tabs_model_iadd_tab(self):
        test_model = models.TabsModel()
        new_tab = tabs.TabData("My tab", models.WorkflowListModel2())
        test_model += new_tab
        assert test_model.rowCount() == 1

    def test_tabs_model_delete_tab(self):
        test_model = models.TabsModel()
        new_tab = tabs.TabData("My tab", models.WorkflowListModel2())
        # new_tab.tab_name =
        test_model += new_tab

        second_new_tab = tabs.TabData("second new tab",
                                      models.WorkflowListModel2())

        test_model += second_new_tab
        assert test_model.rowCount() == 2

        test_model -= second_new_tab
        assert test_model.rowCount() == 1

    def test_tabs_model_delete_all_tabs(self):
        test_model = models.TabsModel()
        first_new_tab = tabs.TabData("My tab", models.WorkflowListModel2())
        test_model += first_new_tab

        second_new_tab = tabs.TabData("second new tab",
                                      models.WorkflowListModel2())

        test_model += second_new_tab
        assert test_model.rowCount() == 2

        test_model -= second_new_tab
        assert test_model.rowCount() == 1

        test_model -= first_new_tab
        assert test_model.rowCount() == 0

    def test_model_contains(self):
        from speedwagon.frontend.qtwidgets.tabs import TabData
        model = models.TabsModel()
        model.add_tab(TabData("dummy", Mock()))
        assert ("dummy" in model) is True

    def test_model_contains_false(self):
        model = models.TabsModel()
        assert ("dummy" in model) is False

    def test_model_iadd_operator(self):
        from speedwagon.frontend.qtwidgets.tabs import TabData
        model = models.TabsModel()
        model += TabData("dummy", Mock())
        assert ("dummy" in model) is True

    def test_model_isub_operator(self):
        from speedwagon.frontend.qtwidgets.tabs import TabData
        tab = TabData("dummy", Mock())
        model = models.TabsModel()
        model += tab
        assert ("dummy" in model) is True
        model -= tab
        assert ("dummy" in model) is False

    def test_model_data(self):
        from speedwagon.frontend.qtwidgets.tabs import TabData
        tab = TabData("dummy", Mock())
        model = models.TabsModel()
        model.add_tab(tab)
        assert model.data(model.index(0, 0), role=QtCore.Qt.UserRole) == tab

    def test_adding_tab_is_data_modified(self, qtbot):
        test_model = models.TabsModel()
        assert test_model.data_modified is False
        with qtbot.wait_signal(test_model.dataChanged) as signal:
            new_tab = tabs.TabData(
                "new_tab_name",
                models.WorkflowListModel2()
            )
            test_model.add_tab(new_tab)
        assert test_model.data_modified is True
    def test_adding_tab_and_removing_it_is_not_data_modified(self, qtbot):
        test_model = models.TabsModel()
        assert test_model.data_modified is False
        new_tab = tabs.TabData(
            "new_tab_name",
            models.WorkflowListModel2()
        )
        with qtbot.wait_signal(test_model.dataChanged):
            test_model.add_tab(new_tab)

        with qtbot.wait_signal(test_model.dataChanged):
            test_model.remove_tab(new_tab)

        assert test_model.data_modified is False

    def test_add_and_reset_modified(self, qtbot):
        test_model = models.TabsModel()
        assert test_model.data_modified is False
        new_tab = tabs.TabData(
            "new_tab_name",
            models.WorkflowListModel2()
        )
        with qtbot.wait_signal(test_model.dataChanged):
            test_model.add_tab(new_tab)
        assert test_model.data_modified is True
        with qtbot.wait_signal(test_model.dataChanged):
            test_model.reset_modified()
        assert test_model.data_modified is False

    def test_modify_reset_modified(self, qtbot):
        test_model = models.TabsModel()
        assert test_model.data_modified is False
        new_tab = tabs.TabData(
            "new_tab_name",
            models.WorkflowListModel2()
        )
        with qtbot.wait_signal(test_model.dataChanged):
            test_model.add_tab(new_tab)
        assert test_model.data_modified is True
        with qtbot.wait_signal(test_model.dataChanged):
            test_model.reset_modified()
        assert test_model.data_modified is False


class TestWorkflowListModel2:

    @pytest.fixture()
    def workflows_model(self, monkeypatch):
        monkeypatch.setattr(
            speedwagon.config,
            "get_whitelisted_plugins",
            lambda: []
        )
        return models.WorkflowListModel2()

    def test_workflow_list_model2_iadd(self, workflows_model):
        workflows = job.available_workflows()
        workflows_model += workflows["Hathi Prep"]
        assert workflows_model.rowCount() == 1

    def test_workflow_list_model2_add(self, workflows_model):
        workflows = job.available_workflows()
        workflows_model.add_workflow(workflows["Hathi Prep"])
        assert workflows_model.rowCount() == 1

    def test_workflow_list_model2_remove(self, workflows_model):
        workflows = job.available_workflows()

        workflows_model.add_workflow(workflows["Hathi Prep"])
        jp2_workflow = workflows['Make JP2']
        workflows_model.add_workflow(jp2_workflow)
        assert workflows_model.rowCount() == 2

        workflows_model.remove_workflow(jp2_workflow)
        assert workflows_model.rowCount() == 1

    def test_workflow_list_model2_isub(self, workflows_model):
        workflows = job.available_workflows()

        workflows_model.add_workflow(workflows["Hathi Prep"])
        jp2_workflow = workflows['Make JP2']
        workflows_model += jp2_workflow
        assert workflows_model.rowCount() == 2

        workflows_model -= jp2_workflow
        assert workflows_model.rowCount() == 1

    def test_data(self, workflows_model):
        mock_workflow = Mock()
        mock_workflow.name = "Spam"
        workflows_model.add_workflow(mock_workflow)

        assert workflows_model.data(
            workflows_model.index(0, 0),
            role=QtCore.Qt.DisplayRole
        ) == "Spam"

    def test_sort_defaults_alpha_by_name(self, workflows_model):
        mock_spam_workflow = Mock()
        mock_spam_workflow.name = "Spam"
        workflows_model.add_workflow(mock_spam_workflow)

        mock_bacon_workflow = Mock()
        mock_bacon_workflow.name = "Bacon"
        workflows_model.add_workflow(mock_bacon_workflow)
        workflows_model.sort()
        assert workflows_model.data(
            workflows_model.index(0, 0),
            role=QtCore.Qt.DisplayRole
        ) == "Bacon" and workflows_model.data(
            workflows_model.index(1, 0),
            role=QtCore.Qt.DisplayRole
        ) == "Spam"

    def test_data_modified(self, workflows_model):
        assert workflows_model.data_modified is False
        class Dummy(speedwagon.Workflow):
            pass
        workflows_model.add_workflow(Dummy)
        assert workflows_model.data_modified is True

    def test_swaps_workflow_data_modified(self, qtbot, workflows_model):
        assert workflows_model.data_modified is False

        class Dummy1(speedwagon.Workflow):
            name = "Dummy1"

        class Dummy2(speedwagon.Workflow):
            name = "Dummy2"

        class Dummy3(speedwagon.Workflow):
            name = "Dummy3"

        workflows_model.add_workflow(Dummy1)
        workflows_model.add_workflow(Dummy2)
        workflows_model.reset_modified()

        # replace one workflow for another
        workflows_model.remove_workflow(Dummy2)
        workflows_model.add_workflow(Dummy3)
        assert workflows_model.data_modified is True



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


def test_get_settings_errors():
    file_selection_option = workflow.FileSelectData(
        'Checksum File',
        required=True
    )
    # Note that no value has been selected for a required field
    file_selection_option.value = None

    data = [
        file_selection_option
    ]
    model = models.ToolOptionsModel4(data)
    error = models.get_settings_errors(
        model,
        [
            models.check_required_settings_have_values
        ]
    )
    assert len(error) > 0


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
