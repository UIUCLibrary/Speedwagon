import forseti.job
import forseti.models
from forseti import tool
# from PyQt5 import QtCore
import pytest


def test_load_tools():
    tools = forseti.job.available_tools()
    assert isinstance(tools, dict)
    assert "Make Checksum Batch [Single]" in tools
    tool_list = forseti.models.ToolsListModel(tools)
    print(tool_list)