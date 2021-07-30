"""Dialog boxes."""
import typing
from typing import Collection, Union

from PyQt5 import QtWidgets, QtGui, QtCore  # type: ignore
try:  # pragma: no cover
    from importlib import metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore

import speedwagon

__all__ = [
    "SystemInfoDialog",
    "WorkProgressBar",
    "about_dialog_box"
]


class ErrorDialogBox(QtWidgets.QMessageBox):
    """Dialog box for Error Messages causes while running a job."""

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        """Create a error dialog box."""
        super().__init__(parent)
        self.setIcon(QtWidgets.QMessageBox.Critical)
        self.setStandardButtons(QtWidgets.QMessageBox.Abort)
        self.setSizeGripEnabled(True)

    def event(self, event: QtCore.QEvent) -> bool:
        # Allow the dialog box to be resized so that the additional information
        # can be readable

        result = QtWidgets.QMessageBox.event(self, event)

        self.setMinimumHeight(100)
        self.setMaximumHeight(1024)
        self.setMinimumWidth(250)
        self.setMaximumWidth(1000)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        text_edit = self.findChild(QtWidgets.QTextEdit)
        if text_edit is not None:
            text_edit.setMinimumHeight(100)
            text_edit.setMaximumHeight(16777215)
            text_edit.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding)

        return result


class WorkProgressBar(QtWidgets.QProgressDialog):
    """Use this for showing progress."""

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        super().closeEvent(event)

    def __init__(self, *args) -> None:
        """Create a work progress dialog window."""
        super().__init__(*args)
        self.setModal(True)
        self.setMinimumHeight(100)
        self.setMinimumWidth(250)
        self._label = QtWidgets.QLabel()
        self._label.setWordWrap(True)
        self.setLabel(self._label)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._label.setMaximumWidth(self.width())
        self.setMinimumHeight(self._label.sizeHint().height() + 75)


def about_dialog_box(parent: typing.Optional[QtWidgets.QWidget]) -> None:
    """Launch the about speedwagon dialog box."""
    try:
        pkg_metadata = dict(metadata.metadata(speedwagon.__name__))
        summary = pkg_metadata['Summary']
        version = pkg_metadata['Version']
        message = f"{speedwagon.__name__.title()}: {version}" \
                  f"\n" \
                  f"\n" \
                  f"{summary}"

    except metadata.PackageNotFoundError:
        message = \
            f"{speedwagon.__name__.title()}"

    QtWidgets.QMessageBox.about(parent, "About", message)


class SystemInfoDialog(QtWidgets.QDialog):
    """System information dialog window."""

    # parent: QWidget = None, flags: Union[
    #     Qt.WindowFlags, Qt.WindowType] = Qt.WindowFlags()
    def __init__(
            self,
            parent: QtWidgets.QWidget,
            flags: Union[QtCore.Qt.WindowFlags,
                         QtCore.Qt.WindowType] = QtCore.Qt.WindowFlags()
    ) -> None:
        """Display System information."""
        super().__init__(parent, flags)

        self.setWindowTitle("System Information")
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        self.installed_packages_title = QtWidgets.QLabel(parent)
        self.installed_packages_title.setText("Installed Python Packages:")

        installed_python_packages = self.get_installed_packages()

        self.installed_packages_widget = QtWidgets.QListWidget(parent)
        self.installed_packages_widget.addItems(installed_python_packages)

        layout.addWidget(self.installed_packages_title)
        layout.addWidget(self.installed_packages_widget)

        self._button_box = \
            QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)

        self._button_box.accepted.connect(self.accept)
        layout.addWidget(self._button_box)

    @staticmethod
    def get_installed_packages() -> Collection[str]:
        """Get list of strings of installed packages."""
        pkgs = sorted(
            metadata.distributions(),
            key=lambda x: x.metadata['Name'].upper()
        )
        return [
            f"{x.metadata['Name']} {x.metadata['Version']}" for x in pkgs
        ]
