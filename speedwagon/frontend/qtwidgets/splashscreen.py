"""Splash screen."""
import sys
import typing
# pylint: disable=wrong-import-position
if sys.version_info >= (3, 9):
    from importlib import resources
    from importlib.resources import as_file
else:
    import importlib_resources as resources
    from importlib_resources import as_file

from PySide6 import QtWidgets, QtGui, QtCore


def create_splash() -> QtWidgets.QSplashScreen:
    """Create a splash screen."""
    with as_file(
        resources.files("speedwagon").joinpath("logo.png")
    ) as logo_file:
        logo = QtGui.QPixmap()
        logo.load(str(logo_file), format=None)
        splash = QtWidgets.QSplashScreen(logo.scaled(400, 400))

    splash.setEnabled(False)
    splash.setWindowFlags(
        typing.cast(
            QtCore.Qt.WindowType,
            QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.FramelessWindowHint,
        )
    )
    return splash
