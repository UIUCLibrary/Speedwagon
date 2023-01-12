import pytest
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from speedwagon.frontend.qtwidgets import splashscreen


def test_create_splash(qtbot):
    splash = splashscreen.create_splash()
    assert isinstance(splash, QtWidgets.QSplashScreen)
