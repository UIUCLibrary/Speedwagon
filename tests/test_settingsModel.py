import speedwagon.models
from speedwagon.dialog import settings
from PyQt5 import QtCore


def test_settings_model_empty():
    test_model = speedwagon.models.SettingsModel()
    assert test_model.rowCount() == 0
    assert test_model.columnCount() == 2
    index = test_model.index(0, 0)
    assert index.data() is None
    assert isinstance(test_model.data(index), QtCore.QVariant)


def test_settings_model_added():
    test_model = speedwagon.models.SettingsModel()
    test_model.add_setting("mysetting", "eggs")
    assert test_model.rowCount() == 1
    assert test_model.columnCount() == 2
    assert test_model.index(0, 0).data() == "mysetting"
    assert test_model.index(0, 1).data() == "eggs"

    index = test_model.index(0, 1)
    assert isinstance(test_model.data(index), QtCore.QVariant)

