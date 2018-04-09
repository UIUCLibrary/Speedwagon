import speedwagon.job
import speedwagon.models
import pytest


def test_load_tools():
    tools = speedwagon.job.available_tools()
    assert isinstance(tools, dict)
    assert "Make Checksum Batch [Single]" in tools
    tool_list = speedwagon.models.ToolsListModel(tools)
    print(tool_list)