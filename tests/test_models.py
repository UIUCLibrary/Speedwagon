from unittest.mock import Mock

from PyQt5 import QtCore

from speedwagon import tabs, models, job


def test_settings_model_empty():
    test_model = models.SettingsModel()
    assert test_model.rowCount() == 0
    assert test_model.columnCount() == 2
    index = test_model.index(0, 0)
    assert index.data() is None
    assert isinstance(test_model.data(index), QtCore.QVariant)


def test_settings_model_added():
    test_model = models.SettingsModel()
    test_model.add_setting("mysetting", "eggs")
    assert test_model.rowCount() == 1
    assert test_model.columnCount() == 2
    assert test_model.index(0, 0).data() == "mysetting"
    assert test_model.index(0, 1).data() == "eggs"

    index = test_model.index(0, 1)
    assert isinstance(test_model.data(index), QtCore.QVariant)


def test_tabs_model_iadd_tab():
    test_model = models.TabsModel()
    new_tab = tabs.TabData("My tab", models.WorkflowListModel2())
    test_model += new_tab
    assert test_model.rowCount() == 1


def test_tabs_model_delete_tab():
    test_model = models.TabsModel()
    new_tab = tabs.TabData("My tab", models.WorkflowListModel2())
    # new_tab.tab_name =
    test_model += new_tab

    second_new_tab = tabs.TabData("second new tab", models.WorkflowListModel2())
    test_model += second_new_tab
    assert test_model.rowCount() == 2

    test_model -= second_new_tab
    assert test_model.rowCount() == 1


def test_tabs_model_delete_all_tabs():
    test_model = models.TabsModel()
    first_new_tab = tabs.TabData("My tab", models.WorkflowListModel2())
    test_model += first_new_tab

    second_new_tab = tabs.TabData("second new tab", models.WorkflowListModel2())
    test_model += second_new_tab
    assert test_model.rowCount() == 2

    test_model -= second_new_tab
    assert test_model.rowCount() == 1

    test_model -= first_new_tab
    assert test_model.rowCount() == 0


def test_workflow_list_model2_iadd():
    workflows_model = models.WorkflowListModel2()
    workflows = job.available_workflows()
    workflows_model += workflows["Hathi Prep"]
    assert workflows_model.rowCount() == 1



def test_workflow_list_model2_add():
    workflows_model = models.WorkflowListModel2()
    workflows = job.available_workflows()
    workflows_model.add_workflow(workflows["Hathi Prep"])
    assert workflows_model.rowCount() == 1


def test_workflow_list_model2_remove():
    workflows_model = models.WorkflowListModel2()
    workflows = job.available_workflows()

    workflows_model.add_workflow(workflows["Hathi Prep"])
    jp2_workflow = workflows['Make JP2']
    workflows_model.add_workflow(jp2_workflow)
    assert workflows_model.rowCount() == 2

    workflows_model.remove_workflow(jp2_workflow)
    assert workflows_model.rowCount() == 1


def test_workflow_list_model2_isub():
    workflows_model = models.WorkflowListModel2()
    workflows = job.available_workflows()

    workflows_model.add_workflow(workflows["Hathi Prep"])
    jp2_workflow = workflows['Make JP2']
    workflows_model += jp2_workflow
    assert workflows_model.rowCount() == 2

    workflows_model -= jp2_workflow
    assert workflows_model.rowCount() == 1


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
