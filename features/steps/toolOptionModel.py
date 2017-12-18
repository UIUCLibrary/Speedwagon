from behave import *
from behave import runner
from PyQt5 import QtCore
# from pytest_bdd import scenario, given, when, then
from forseti import tool


# use_step_matcher("re")


@given("we have two options called dummy and dummy2")
def step_impl(context: runner.Context):
    data = {
        "dummy": "",
        "dummy2": ""

    }
    context.data = data


@when("we provide data to generate a Qt model")
def step_impl(context: runner.Context):
    context.data_model = tool.ToolOptionsPairsModel(context.data)
    # assert context.d == "dd"


@then("we get a ToolOptionsModel object")
def step_impl(context: runner.Context):
    assert isinstance(context.data_model, tool.ToolOptionsPairsModel)
    pass


@then("the model has 2 rows")
def step_impl(context: runner.Context):
    assert context.data_model.rowCount() == 2


@step("the model has 1 column")
def step_impl(context: runner.Context):
    assert context.data_model.columnCount() == 1


@given("I have an options model with a single my_option")
def step_impl(context: runner.Context):
    data = {"my_option": ""}
    context.data_model = tool.ToolOptionsPairsModel(data)


@when("I ask for the display data of my_option")
def step_impl(context: runner.Context):
    context.index = context.data_model.index(0, 0)
    context.result = context.data_model.data(context.index, role=QtCore.Qt.DisplayRole)


@then("the data returned is an empty string")
def step_impl(context: runner.Context):
    assert context.result == ""


@step('the headerData is title case "My_Option"')
def step_impl(context):
    result = context.data_model.headerData(0, Qt_Orientation=QtCore.Qt.Vertical, role=QtCore.Qt.DisplayRole)
    assert result == "My_Option"

@when("I ask for the final data")
def step_impl(context: runner.Context):
    context.result = context.data_model.get()


@step("the results data is a dictionary")
def step_impl(context: runner.Context):
    assert isinstance(context.result, dict)


@step("my_option as the only key")
def step_impl(context: runner.Context):
    assert len(context.result.keys()) == 1
    assert "my_option" in context.result


@step("my_option has an empty string for its value")
def step_impl(context: runner.Context):
    assert context.result["my_option"] == ""


@step('I set the data to "my data"')
def step_impl(context: runner.Context):
    index = context.data_model.index(0, 0)
    context.data_model.setData(index, data="my data")


@step('my_option has an "my data" its value')
def step_impl(context: runner.Context):
    assert context.result["my_option"] == "my data"

