from forseti import tool
from PyQt5 import QtCore
import pytest


def test_load_tools():
    tools = tool.available_tools()
    assert isinstance(tools, dict)
    assert "Make Checksum Batch" in tools
    tool_list = tool.ToolsListModel(tools)
    print(tool_list)