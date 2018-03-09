import forseti.models
from forseti import tool
# from PyQt5 import QtCore
import pytest


def test_load_tools():
    tools = tool.available_tools()
    assert isinstance(tools, dict)
    assert "Make Checksum Batch [Single]" in tools
    tool_list = forseti.models.ToolsListModel(tools)
    print(tool_list)