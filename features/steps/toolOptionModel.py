from behave import *
from behave import runner
from PySide6 import QtCore
import speedwagon
from speedwagon.frontend.qtwidgets import models
from speedwagon.workflows.shared_custom_widgets import  UserOptionCustomDataType

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
    context.data_model = models.ToolOptionsModel3(context.data)


@then("we get a ToolOptionsModel object")
def step_impl(context: runner.Context):
    assert isinstance(context.data_model, models.ToolOptionsModel3)


@then("the model has 2 rows")
def step_impl(context: runner.Context):
    assert context.data_model.rowCount() == 2


@step("the model has 1 column")
def step_impl(context: runner.Context):
    assert context.data_model.columnCount() == 1


@given("I have an options model with a single my_option")
def step_impl(context: runner.Context):
    data = {"my_option": ""}
    context.data_model = models.ToolOptionsPairsModel(data)


@when("I ask for the display data of my_option")
def step_impl(context: runner.Context):
    context.index = context.data_model.index(0, 0)
    context.result = context.data_model.data(context.index,
                                             role=QtCore.Qt.DisplayRole)


@then("the data returned is an empty string")
def step_impl(context: runner.Context):
    assert context.result == ""


@step('the headerData is "my_option"')
def step_impl(context):
    result = context.data_model.headerData(0, QtCore.Qt.Vertical,
                                           role=QtCore.Qt.DisplayRole)
    assert result == "my_option"


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


@given("we have two ToolOptions called dummy and dummy2")
def step_impl(context):
    data = [
        UserOptionCustomDataType("dummy", str),
        UserOptionCustomDataType("dummy2", str)
    ]

    context.data = data
