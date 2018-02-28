from behave import *
from behave import runner

import forseti.tools.options
from forseti import tool

use_step_matcher("re")
@given("we have two ToolOptions called dummy and dummy2")
def step_impl(context):
    data = [
        forseti.tools.options.ToolOptionDataType(name="dummy"),
        forseti.tools.options.ToolOptionDataType(name="dummy2")
    ]

    context.data = data

@then("we get a ToolOptionsModel2 object")
def step_impl(context: runner.Context):
    assert isinstance(context.data_model, tool.ToolOptionsModel2)


@when("we provide data to generate a Qt model options model 2")
def step_impl(context: runner.Context):
    context.data_model = tool.ToolOptionsModel2(context.data)

@given("I have an options model with ToolOptions 2 with a single my_option")
def step_impl(context: runner.Context):
    data = [forseti.tools.options.ToolOptionDataType(name="my_option")]
    context.data_model = tool.ToolOptionsModel2(data)


