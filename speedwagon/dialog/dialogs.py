"""Dialog boxes."""
import abc
import logging
import sys
import typing
import warnings
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

    @abc.abstractmethod
    def start(self) -> None:
        """Start."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop."""

    def set_buttons_to_close_only(
            self,
            button_box: QtWidgets.QDialogButtonBox
    ) -> None:
        cancel_button: QtWidgets.QPushButton = \
            button_box.button(button_box.Cancel)

        cancel_button.setEnabled(False)

        close_button: QtWidgets.QPushButton \
            = button_box.button(button_box.Close)
        close_button.setEnabled(True)

    def set_progress_to_none(
            self,
            progress_bar: QtWidgets.QProgressBar
    ) -> None:
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)

    @staticmethod
    def hide_progress_bar(progress_bar: QtWidgets.QProgressBar):
        progress_bar.setVisible(False)


class WorkflowProgressStateIdle(AbsWorkflowProgressState):

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self._set_button_defaults()

    def stop(self) -> None:
        warnings.warn("Already stopped")

    def _set_button_defaults(self):
        cancel_button: QtWidgets.QPushButton \
            = self.context.buttonBox.button(self.context.buttonBox.Cancel)
        cancel_button.setEnabled(False)
        self.context.rejected.connect(self.context.buttonBox.rejected)

    def start(self):
        self.context.state = WorkflowProgressStateWorking(self.context)


class WorkflowProgressStateWorking(AbsWorkflowProgressState):

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)

        cancel_button: QtWidgets.QPushButton \
            = self.context.buttonBox.button(self.context.buttonBox.Cancel)
        cancel_button.setEnabled(True)
        self.context.buttonBox.rejected.disconnect()

        close_button: QtWidgets.QPushButton \
            = self.context.buttonBox.button(self.context.buttonBox.Close)
        close_button.setEnabled(False)
        QtWidgets.QApplication.processEvents()

    def start(self) -> None:
        warnings.warn("Already started")

    def stop(self) -> None:
        self.context.state = WorkflowProgressStateStopping(self.context)


class WorkflowProgressStateStopping(AbsWorkflowProgressState):
    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self.context.write_to_console("Stopping")

    def start(self) -> None:
        warnings.warn("Already started")

    def stop(self) -> None:
        dialog = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Information,
            "Trying to stop job.",
            "Do you want to force quit?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if dialog.exec() == QtWidgets.QMessageBox.Yes:
            sys.exit(1)
        warnings.warn("Already stopping")


class WorkflowProgressStateAborted(AbsWorkflowProgressState):
    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self.set_progress_to_none(context.progressBar)
        self.set_buttons_to_close_only(context.buttonBox)
        close_button: QtWidgets.QPushButton \
            = self.context.buttonBox.button(self.context.buttonBox.Close)
        self.context.write_to_console("Successfully stopped")
        close_button.clicked.connect(self.context.accept)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class WorkflowProgressStateFailed(AbsWorkflowProgressState):
    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self.set_progress_to_none(context.progressBar)
        self.set_buttons_to_close_only(context.buttonBox)
        close_button: QtWidgets.QPushButton \
            = self.context.buttonBox.button(self.context.buttonBox.Close)
        close_button.clicked.connect(self.context.reject)
        self.hide_progress_bar(self.context.progressBar)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class WorkflowProgressStateWorkingIndeterminate(WorkflowProgressStateWorking):

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        context.progressBar.setRange(0, 0)


class WorkflowProgressStateDone(AbsWorkflowProgressState):

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self.set_buttons_to_close_only(context.buttonBox)
        close_button: QtWidgets.QPushButton \
            = self.context.buttonBox.button(self.context.buttonBox.Close)
        close_button.clicked.connect(self.context.accept)
        self.set_progress_to_full(self.context.progressBar)
        self.hide_progress_bar(self.context.progressBar)

    @staticmethod
    def set_progress_to_full(progress_bar: QtWidgets.QProgressBar) -> None:
        progress_bar.setValue(progress_bar.maximum())

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class WorkflowProgress(QtWidgets.QDialog):
    aborted = QtCore.pyqtSignal()

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
        self.progressBar: QtWidgets.QProgressBar
        # =====================================================================

        self._console_data = QtGui.QTextDocument()

        self._console_data.setDefaultFont(
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        )

        self.console.setDocument(self._console_data)

        # =====================================================================
        c = self.buttonBox.button(self.buttonBox.Cancel)
        c.clicked.connect(self.aborted)
        # self.aborted.connect()
        # =====================================================================
        self.state = WorkflowProgressStateIdle(self)

    def start(self):
        self.state.start()

    def stop(self):
        self.state.stop()

    def failed(self):
        state = WorkflowProgressStateFailed(
            context=self)
        self.state = state

    def cancel_completed(self):
        self.state = WorkflowProgressStateAborted(self)

    def success_completed(self):
        self.state = WorkflowProgressStateDone(self)

    @QtCore.pyqtSlot(int)
    def set_total_jobs(self, value):
        self.progressBar.setMaximum(value)

    @QtCore.pyqtSlot(int)
    def set_current_progress(self, value):
        self.progressBar.setValue(value)
        QtWidgets.QApplication.processEvents()

    @QtCore.pyqtSlot(str, int)
    def write_to_console(self, text: str, level=logging.INFO):
        cursor = QtGui.QTextCursor(self._console_data)
        cursor.movePosition(cursor.End)
        cursor.beginEditBlock()
        if level == logging.DEBUG:
            cursor.insertHtml(f"<div><i>{text}</i></div>")
        elif level == logging.WARNING:
            cursor.insertHtml(
                f"<div><font color=\"yellow\">{text}</font></div>"
            )
        elif level == logging.ERROR:
            cursor.insertHtml(f"<div><font color=\"red\">{text}</font></div>")
        else:
            cursor.insertHtml(f"<div>{text}</div>")

        cursor.insertText("\n")
        cursor.endEditBlock()

    def get_console_content(self) -> str:
        return self._console_data.toPlainText()
