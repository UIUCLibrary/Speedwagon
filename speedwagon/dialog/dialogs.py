"""Dialog boxes."""
import abc
import logging
import typing
from typing import Collection, Union

from PyQt5 import QtWidgets, QtGui, QtCore  # type: ignore
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget

try:  # pragma: no cover
    from importlib import metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore

try:  # pragma: no cover
    from importlib import resources
except ImportError:  # pragma: no cover
    import importlib_resources as resources  # type: ignore

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

    def __init__(self, *args, **kwargs) -> None:
        """Create a work progress dialog window."""
        super().__init__(*args, **kwargs)
        self.setModal(True)
        self.setMinimumHeight(100)
        self.setMinimumWidth(250)
        self._label = QtWidgets.QLabel(parent=self)
        self._label.setWordWrap(True)
        self.setLabel(self._label)

    def resizeEvent(self,  # pylint: disable=C0103
                    event: QtGui.QResizeEvent) -> None:
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


class AbsWorkflowProgressState(abc.ABC):
    def __init__(self, context: "WorkflowProgress"):
        self.context = context


class WorkflowProgressStateIdle(AbsWorkflowProgressState):

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self._set_button_defaults()

    def _set_button_defaults(self):
        cancel_button: QtWidgets.QPushButton \
            = self.context.buttonBox.button(self.context.buttonBox.Cancel)
        cancel_button.setEnabled(False)


class WorkflowProgressStateWorking(AbsWorkflowProgressState):

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)

        cancel_button: QtWidgets.QPushButton \
            = self.context.buttonBox.button(self.context.buttonBox.Cancel)
        cancel_button.setEnabled(True)

        close_button: QtWidgets.QPushButton \
            = self.context.buttonBox.button(self.context.buttonBox.Close)
        close_button.setEnabled(False)


class WorkflowProgressStateWorkingIndeterminate(WorkflowProgressStateWorking):

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        context.progressBar.setRange(0,0)


class WorkflowProgress(QtWidgets.QDialog):
    add_message = QtCore.pyqtSignal([str], [str, int])
    set_current_progress = QtCore.pyqtSignal(int)
    set_max_value = QtCore.pyqtSignal(int)

    def __init__(self, parent: typing.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # All ui info is located in the .ui file. Any graphical changes should
        # be make in there.
        with resources.path(
                "speedwagon.ui",
                "workflow_progress.ui"
        ) as ui_file:
            uic.loadUi(ui_file, self)

        # =====================================================================
        #  Type hints loaded to help with development after loading in the
        #  Qt .ui files
        # =====================================================================
        self.buttonBox: QtWidgets.QDialogButtonBox
        self.console: QtWidgets.QTextBrowser
        # =====================================================================

        self._console_data = QtGui.QTextDocument()
        monospaced_font = \
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        self._console_data.setDefaultFont(monospaced_font)

        # self._set_button_defaults()

        self.console.setDocument(self._console_data)
        self.add_message[str].connect(self.write_to_console)
        self.add_message[str, int].connect(self.write_to_console)

        # =====================================================================
        self.state = WorkflowProgressStateIdle(self)

    def write_to_console(self, text, level=logging.INFO):
        cursor = QtGui.QTextCursor(self._console_data)
        cursor.movePosition(cursor.End)
        cursor.beginEditBlock()
        if level == logging.DEBUG:
            cursor.insertHtml(f"<div><i>{text}</i></div>")
        elif level == logging.WARNING:
            cursor.insertHtml(f"<div><font color=\"yellow\">{text}</font></div>")
        elif level == logging.ERROR:
            cursor.insertHtml(f"<div><font color=\"red\">{text}</font></div>")
        else:
            cursor.insertHtml(f"<div>{text}</div>")

        cursor.insertText("\n")
        cursor.endEditBlock()

    def get_console_content(self) -> str:
        return self._console_data.toPlainText()
