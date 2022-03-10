import json
from unittest.mock import Mock

import pytest
from PySide6 import QtCore, QtWidgets

from speedwagon import tabs, models, job, widgets, workflow


class TestSettingsModel:
    def test_settings_model_empty(self):
        test_model = models.SettingsModel()
        assert test_model.rowCount() == 0
        assert test_model.columnCount() == 2
        index = test_model.index(0, 0)
        assert index.data() is None
        assert isinstance(test_model.data(index), QtCore.QVariant)

    def test_settings_model_added(self):
        test_model = models.SettingsModel()
        test_model.add_setting("mysetting", "eggs")
        assert test_model.rowCount() == 1
        assert test_model.columnCount() == 2
        assert test_model.index(0, 0).data() == "mysetting"
        assert test_model.index(0, 1).data() == "eggs"

        index = test_model.index(0, 1)
        assert isinstance(test_model.data(index), QtCore.QVariant)


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


class TestItemListModel:
    def test_create(self):
        data = {
            "spam": Mock()
        }
        new_model = models.ItemListModel(data)
        assert new_model.jobs == list(data.values())

    def test_columns_are_always_two(self):
        data = {
            "spam": Mock()
        }
        new_model = models.ItemListModel(data)
        assert new_model.columnCount() == 2

    def test_columns_row_count_is_the_size_of_data(self):
        data = {
            "spam": Mock()
        }
        new_model = models.ItemListModel(data)
        assert new_model.rowCount() == len(data)


class TestWorkflowListModel2:

    def test_workflow_list_model2_iadd(self):
        workflows_model = models.WorkflowListModel2()
        workflows = job.available_workflows()
        workflows_model += workflows["Hathi Prep"]
        assert workflows_model.rowCount() == 1

    def test_workflow_list_model2_add(self):
        workflows_model = models.WorkflowListModel2()
        workflows = job.available_workflows()
        workflows_model.add_workflow(workflows["Hathi Prep"])
        assert workflows_model.rowCount() == 1

    def test_workflow_list_model2_remove(self):
        workflows_model = models.WorkflowListModel2()
        workflows = job.available_workflows()

        workflows_model.add_workflow(workflows["Hathi Prep"])
        jp2_workflow = workflows['Make JP2']
        workflows_model.add_workflow(jp2_workflow)
        assert workflows_model.rowCount() == 2

        workflows_model.remove_workflow(jp2_workflow)
        assert workflows_model.rowCount() == 1

    def test_workflow_list_model2_isub(self):
        workflows_model = models.WorkflowListModel2()
        workflows = job.available_workflows()

        workflows_model.add_workflow(workflows["Hathi Prep"])
        jp2_workflow = workflows['Make JP2']
        workflows_model += jp2_workflow
        assert workflows_model.rowCount() == 2

        workflows_model -= jp2_workflow
        assert workflows_model.rowCount() == 1

    def test_data(self):
        workflows_model = models.WorkflowListModel2()
        mock_workflow = Mock()
        mock_workflow.name = "Spam"
        workflows_model.add_workflow(mock_workflow)

        assert workflows_model.data(
            workflows_model.index(0, 0),
            role=QtCore.Qt.DisplayRole
        ) == "Spam"

    def test_sort_defaults_alpha_by_name(self):
        workflows_model = models.WorkflowListModel2()
        mock_spam_workflow = Mock()
        mock_spam_workflow.name = "Spam"
        workflows_model.add_workflow(mock_spam_workflow)

        mock_bacon_workflow = Mock()
        mock_bacon_workflow.name = "Bacon"
        workflows_model.add_workflow(mock_bacon_workflow)
        workflows_model.sort()
        assert workflows_model.data(
            workflows_model.index(0,0),
            role=QtCore.Qt.DisplayRole
        ) == "Bacon" and workflows_model.data(
            workflows_model.index(1,0),
            role=QtCore.Qt.DisplayRole
        ) == "Spam"


class TestToolOptionsModel3:
    def test_model_data_user_role(self):
        data = [Mock(data="Spam")]
        new_model = models.ToolOptionsModel3(data)

        assert new_model.data(new_model.index(0, 0),
                              QtCore.Qt.UserRole) == data[0]

    def test_model_data_edit_role(self):
        data = [Mock(data="Spam")]
        new_model = models.ToolOptionsModel3(data)
        assert new_model.data(
            new_model.index(0, 0), QtCore.Qt.EditRole
        ) == "Spam"

    def test_model_data_display_role(self):
        data = [Mock(data="Spam")]
        new_model = models.ToolOptionsModel3(data)
        assert new_model.data(
            new_model.index(0, 0), QtCore.Qt.DisplayRole
        ) == "Spam"

    def test_model_size_hint(self):
        data = [Mock()]
        new_model = models.ToolOptionsModel3(data)
        assert isinstance(
            new_model.data(new_model.index(0, 0), QtCore.Qt.SizeHintRole),
            QtCore.QSize
        )

    def test_get(self):
        data = [Mock(data="Spam")]
        new_model = models.ToolOptionsModel3(data)
        assert "Spam" in new_model.get().values()

    def test_header_data(self):
        data = [Mock(data="Spam", label_text="Spam label")]
        new_model = models.ToolOptionsModel3(data)
        label = new_model.headerData(
            0, QtCore.Qt.Vertical, role=QtCore.Qt.DisplayRole
        )
        assert label == "Spam label"

    def test_set_data(self):
        data = [Mock(data="Spam", label_text="Spam label")]
        new_model = models.ToolOptionsModel3(data)
        new_model.setData(new_model.index(0,0), "Bacon")
        s = new_model.data(new_model.index(0,0))
        assert s == "Bacon"

    def test_set(self):
        data = [Mock(data="Spam", label_text="Spam label")]
        new_model = models.ToolOptionsModel3(data)
        new_model["Spam label"] = "Dummy"
        assert new_model.get()["Spam label"] == "Dummy"

    def test_get_item(self):
        data = [
            Mock(data="Spam", label_text="Spam label"),
            Mock(data="Bacon", label_text="Bacon label"),
        ]
        new_model = models.ToolOptionsModel3(data)
        new_model["Spam label"] = "Dummy"
        assert new_model["Spam label"] == "Dummy"

    def test_get_item_invalid(self):
        data = []
        new_model = models.ToolOptionsModel3(data)
        with pytest.raises(IndexError):
            new_model["Eggs"]


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

        options = workflow.DropDownSelection('Order')
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
        model.setData(model.index(0,0), data="dumb")
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


class TestTabsModel:
    def test_model_contains(self):
        from speedwagon.tabs import TabData
        model = models.TabsModel()
        model.add_tab(TabData("dummy", Mock()))
        assert ("dummy" in model) is True

    def test_model_contains_false(self):
        model = models.TabsModel()
        assert ("dummy" in model) is False

    def test_model_iadd_operator(self):
        from speedwagon.tabs import TabData
        model = models.TabsModel()
        model += TabData("dummy", Mock())
        assert ("dummy" in model) is True

    def test_model_isub_operator(self):
        from speedwagon.tabs import TabData
        tab = TabData("dummy", Mock())
        model = models.TabsModel()
        model += tab
        assert ("dummy" in model) is True
        model -= tab
        assert ("dummy" in model) is False

    def test_model_data(self):
        from speedwagon.tabs import TabData
        tab = TabData("dummy", Mock())
        model = models.TabsModel()
        model.add_tab(tab)
        assert model.data(model.index(0, 0), role=QtCore.Qt.UserRole) == tab
