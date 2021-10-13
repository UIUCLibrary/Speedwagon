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
            parent: QtWidgets.QWidget = None,
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
    def __init_subclass__(cls, **kwargs) -> None:
        if not hasattr(cls, "state_name") or cls.state_name is None:
            raise NotImplementedError(
                f"{cls.__name__} inherits from AbsWorkflowProgressState "
                f"which requires implementation of 'state_name' class property"
            )
        super().__init_subclass__()
    state_name: str

    def __init__(self, context: "WorkflowProgress"):
        self.context: WorkflowProgress = context

    def start(self) -> None:
        """Start."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop."""

    def close(self, event: QtGui.QCloseEvent) -> None:
        """User clicks on close window."""
        event.accept()

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

    def reset_cancel_button(self) -> None:
        cancel_button: QtWidgets.QPushButton \
            = self.context.button_box.button(self.context.button_box.Cancel)
        cancel_button.setText("Cancel")

    @staticmethod
    def set_progress_to_none(progress_bar: QtWidgets.QProgressBar) -> None:
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)

    @staticmethod
    def hide_progress_bar(progress_bar: QtWidgets.QProgressBar) -> None:
        progress_bar.setVisible(False)


class WorkflowProgressStateIdle(AbsWorkflowProgressState):
    state_name = "idle"

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self._set_button_defaults()
        self.reset_cancel_button()

    def stop(self) -> None:
        warnings.warn("Already stopped")

    def _set_button_defaults(self) -> None:
        cancel_button: QtWidgets.QPushButton \
            = self.context.button_box.button(self.context.button_box.Cancel)
        cancel_button.setEnabled(False)
        self.context.rejected.connect(self.context.button_box.rejected)

    def start(self) -> None:
        self.context.state = WorkflowProgressStateWorking(self.context)


class WorkflowProgressStateWorking(AbsWorkflowProgressState):
    state_name = "working"

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)

        cancel_button: QtWidgets.QPushButton \
            = self.context.button_box.button(self.context.button_box.Cancel)
        cancel_button.setEnabled(True)
        self.context.button_box.rejected.disconnect()

        close_button: QtWidgets.QPushButton \
            = self.context.button_box.button(self.context.button_box.Close)
        close_button.setEnabled(False)
        QtWidgets.QApplication.processEvents()

    def start(self) -> None:
        warnings.warn("Already started")

    def stop(self) -> None:
        self.context.state = WorkflowProgressStateStopping(self.context)

    def close(self, event: QtGui.QCloseEvent):
        dialog = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Information,
            "Trying to stop job.",
            "Trying to stop job?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if dialog.exec() == QtWidgets.QMessageBox.Yes:
            self.context.aborted.emit()
            # self.stop()
            self.context.state = WorkflowProgressStateStopping(self.context)
            event.accept()
        else:
            event.ignore()
        # super().close(event)


class WorkflowProgressStateStopping(AbsWorkflowProgressState):
    state_name = "stopping"

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self.context.write_to_console("Stopping")
        self.context.banner.setText("Stopping")

        cancel_button: QtWidgets.QPushButton \
            = self.context.button_box.button(self.context.button_box.Cancel)
        cancel_button.setText("Force Quit")

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
    state_name = "aborted"

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self.reset_cancel_button()
        self.set_progress_to_none(context.progress_bar)
        self.set_buttons_to_close_only(context.button_box)
        close_button: QtWidgets.QPushButton \
            = self.context.button_box.button(self.context.button_box.Close)
        self.context.write_to_console("Successfully aborted")
        self.context.banner.setText("Aborted")
        close_button.clicked.connect(self.context.accept)

    def stop(self) -> None:
        warnings.warn("Already stopped")


class WorkflowProgressStateFailed(AbsWorkflowProgressState):
    state_name = "failed"

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self.reset_cancel_button()
        self.set_progress_to_none(context.progress_bar)
        self.set_buttons_to_close_only(context.button_box)
        close_button: QtWidgets.QPushButton \
            = self.context.button_box.button(self.context.button_box.Close)
        close_button.clicked.connect(self.context.reject)
        self.hide_progress_bar(self.context.progress_bar)
        self.context.banner.setText("Failed")

    def stop(self) -> None:
        warnings.warn("Already stopped")


class WorkflowProgressStateWorkingIndeterminate(WorkflowProgressStateWorking):

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self.reset_cancel_button()
        context.progress_bar.setRange(0, 0)


class WorkflowProgressStateDone(AbsWorkflowProgressState):
    state_name = "done"

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self.reset_cancel_button()
        self.set_buttons_to_close_only(context.button_box)
        close_button: QtWidgets.QPushButton \
            = self.context.button_box.button(self.context.button_box.Close)
        close_button.setFocus()
        close_button.clicked.connect(self.context.accept)
        self.set_progress_to_full(self.context.progress_bar)
        self.hide_progress_bar(self.context.progress_bar)
        self.context.banner.setText("Finished")
        self.context.write_to_console("Done")

    @staticmethod
    def set_progress_to_full(progress_bar: QtWidgets.QProgressBar) -> None:
        progress_bar.setValue(progress_bar.maximum())

    def stop(self) -> None:
        warnings.warn("Already Finished")


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
        self.button_box: QtWidgets.QDialogButtonBox
        self.console: QtWidgets.QTextBrowser
        self.progress_bar: QtWidgets.QProgressBar
        self.banner: QtWidgets.QLabel

        # =====================================================================
        self._console_data = QtGui.QTextDocument()

        mono_font = \
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)

        self._console_data.setDefaultFont(mono_font)
        self._console_data.contentsChanged.connect(self._follow_text)
        self.console.setMinimumWidth(self.calculate_window_width(mono_font))
        # self.console.setMinimumWidth(self.calculate_window_width(mono_font))
        self.console.setDocument(self._console_data)

        # =====================================================================
        self.button_box.button(
            self.button_box.Cancel
        ).clicked.connect(self.aborted)

        self.setModal(True)
        # =====================================================================
        self.state: AbsWorkflowProgressState = WorkflowProgressStateIdle(self)

    @property
    def current_state(self) -> str:
        return self.state.state_name

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.state.close(event)

    def _follow_text(self) -> None:
        cursor = QtGui.QTextCursor(self._console_data)
        cursor.movePosition(cursor.End)
        self.console.setTextCursor(cursor)

    @staticmethod
    def calculate_window_width(
            font_used: QtGui.QFont,
            characters_width: int = 80
    ) -> int:
        return QtGui.QFontMetrics(
            font_used
        ).horizontalAdvance("*" * characters_width)

    def start(self) -> None:
        self.state.start()

    def stop(self) -> None:
        self.state.stop()

    def failed(self) -> None:
        state = WorkflowProgressStateFailed(
            context=self)
        self.state = state

    def cancel_completed(self) -> None:
        self.state = WorkflowProgressStateAborted(self)

    def success_completed(self) -> None:
        self.state = WorkflowProgressStateDone(self)

    @QtCore.pyqtSlot(int)
    def set_total_jobs(self, value: int) -> None:
        self.progress_bar.setMaximum(value)

    @QtCore.pyqtSlot(int)
    def set_current_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)
        QtWidgets.QApplication.processEvents()

    @QtCore.pyqtSlot(str, int)
    def write_to_console(self, text: str, level=logging.INFO) -> None:
        cursor = QtGui.QTextCursor(self._console_data)
        cursor.movePosition(cursor.End)
        cursor.beginEditBlock()
        text = text.replace("\n", "<br>")
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
