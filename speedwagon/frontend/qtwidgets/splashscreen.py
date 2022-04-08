try:  # pragma: no cover
    from importlib import resources  # type: ignore
except ImportError:  # pragma: no cover
    import importlib_resources as resources  # type: ignore
import typing

from PySide6 import QtWidgets, QtGui, QtCore

import speedwagon


def create_splash():
    with resources.open_binary(speedwagon.__name__, "logo.png") as logo:
        splash = QtWidgets.QSplashScreen(
            QtGui.QPixmap(logo.name).scaled(400, 400))

    splash.setEnabled(False)
    splash.setWindowFlags(
        typing.cast(
            QtCore.Qt.WindowFlags,
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint
        )
    )
    return splash
