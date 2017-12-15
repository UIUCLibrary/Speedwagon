from forseti import tool
from PyQt5 import QtCore

def test_get():
    data = {
        "dummy": ""

    }
    options_module = tool.ToolOptionsModule(data)


    result = options_module.get()
    assert data == result


def test_row_count():
    data = {
        "dummy": "",
        "dummy2": ""

    }
    options_module = tool.ToolOptionsModule(data)
    assert options_module.rowCount() == 2
    assert options_module.columnCount() == 1

    # data = options_module.data(index)


def test_index():
    data = {
        "dummy": "dummydata"

    }
    options_module = tool.ToolOptionsModule(data)
    index = options_module.createIndex(0,0)
    result = options_module.data(index, QtCore.Qt.DisplayRole)
    assert result == "dummydata"