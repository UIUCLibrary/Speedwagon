from PySide6 import QtWidgets
from speedwagon.frontend.qtwidgets import splashscreen


def test_create_splash(qtbot):
    splash = splashscreen.create_splash()
    assert isinstance(splash, QtWidgets.QSplashScreen)
