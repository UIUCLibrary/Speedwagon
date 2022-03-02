"""Dialog boxes."""
import abc
import logging
import logging.handlers
import sys
import typing
import warnings
from typing import Collection, Union

from PySide6 import QtWidgets, QtGui, QtCore  # type: ignore
from speedwagon import ui_loader


try:  # pragma: no cover
    from importlib import metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore

try:  # pragma: no cover
    from importlib import resources
except ImportError:  # pragma: no cover
    import importlib_resources as resources  # type: ignore

import speedwagon
import speedwagon.logging_helpers

__all__ = [
    "SystemInfoDialog",
    "WorkProgressBar",
    "about_dialog_box"
]

ALREADY_STOPPED_MESSAGE = "Already stopped"


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
    def __init_subclass__(cls) -> None:
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

    def close_dialog(  # pylint: disable=R0201
            self,
            event: QtGui.QCloseEvent
    ) -> None:
        """User clicks on close window."""
        event.accept()

    @staticmethod
    def set_buttons_to_close_only(
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
        warnings.warn(ALREADY_STOPPED_MESSAGE)

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

    def start(self) -> None:
        warnings.warn("Already started")

    def stop(self) -> None:
        self.context.state = WorkflowProgressStateStopping(self.context)

    def close_dialog(self, event: QtGui.QCloseEvent) -> None:
        dialog = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Information,
            "Trying to stop job.",
            "Trying to stop job?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if dialog.exec() == QtWidgets.QMessageBox.Yes:
            self.context.aborted.emit()
            self.context.state = WorkflowProgressStateStopping(self.context)
            event.accept()
        else:
            event.ignore()


class WorkflowProgressStateStopping(AbsWorkflowProgressState):
    state_name = "stopping"

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self.context.write_to_console("Stopping")
        self.context.banner.setText("Stopping")

        cancel_button: QtWidgets.QPushButton \
            = self.context.button_box.button(self.context.button_box.Cancel)

        cancel_button.setText("Force Quit")

        self.context.progress_bar.setMaximum(0)
        self.context.progress_bar.setMinimum(0)

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
        warnings.warn(ALREADY_STOPPED_MESSAGE)


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
        warnings.warn(ALREADY_STOPPED_MESSAGE)


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
        # self.context.write_to_console("Done")

    @staticmethod
    def set_progress_to_full(progress_bar: QtWidgets.QProgressBar) -> None:
        progress_bar.setValue(progress_bar.maximum())

    def stop(self) -> None:
        warnings.warn("Already Finished")


class WorkflowProgressGui(QtWidgets.QDialog):
    class DialogLogHandler(logging.handlers.BufferingHandler):
        class LogSignals(QtCore.QObject):
            message = QtCore.Signal(str)

        def __init__(self, dialog: "WorkflowProgressGui") -> None:
            super().__init__(capacity=200)
            self.signals = WorkflowProgress.DialogLogHandler.LogSignals()
            self._dialog = dialog
            self.signals.message.connect(
                self._dialog.write_html_block_to_console
            )

        def flush(self) -> None:
            results = [self.format(log).strip() for log in self.buffer]
            if results:
                report = "".join(results)
                self.signals.message.emit(f"{report}")
            super().flush()

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)

        # All ui info is located in the .ui file. Any graphical changes should
        # be make in there.
        with resources.path(
                "speedwagon.ui",
                "workflow_progress.ui"
        ) as ui_file:
            ui_loader.load_ui(ui_file, self)

        # =====================================================================
        #  Type hints loaded to help with development after loading in the
        #  Qt .ui files
        # =====================================================================
        self.button_box: QtWidgets.QDialogButtonBox
        self.console: QtWidgets.QTextBrowser
        self.progress_bar: QtWidgets.QProgressBar
        self.banner: QtWidgets.QLabel
        # =====================================================================
        self._log_handler: typing.Optional[logging.Handler] = None
        self._parent_logger: typing.Optional[logging.Logger] = None

        self._console_data = QtGui.QTextDocument(parent=self)

    def write_html_block_to_console(self, html: str) -> None:
        cursor = QtGui.QTextCursor(self._console_data)
        cursor.movePosition(cursor.End)
        cursor.beginEditBlock()
        cursor.insertHtml(html.strip())
        cursor.endEditBlock()

    def flush(self) -> None:
        if self._log_handler is not None:
            self._log_handler.flush()

    def attach_logger(self, logger: logging.Logger) -> None:
        self._parent_logger = logger
        self._log_handler = WorkflowProgressGui.DialogLogHandler(self)
        formatter = speedwagon.logging_helpers.ConsoleFormatter()
        self._log_handler.setFormatter(formatter)
        self._parent_logger.addHandler(self._log_handler)

    def remove_log_handles(self) -> None:
        if self._parent_logger is not None:
            if self._log_handler is not None:
                self._log_handler.flush()
                self._parent_logger.removeHandler(self._log_handler)
                self._log_handler = None
            self._parent_logger = None

    def get_console_content(self) -> str:
        return self._console_data.toPlainText()


class WorkflowProgress(WorkflowProgressGui):

    aborted = QtCore.Signal()

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)

        # =====================================================================

        mono_font = \
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)

        self._console_data.setDefaultFont(mono_font)

        typing.cast(
            QtCore.SignalInstance,
            self._console_data.contentsChanged
        ).connect(self._follow_text)

        self.console.setMinimumWidth(self.calculate_window_width(mono_font))

        self.console.setDocument(self._console_data)
        # =====================================================================
        self.button_box.button(
            self.button_box.Cancel
        ).clicked.connect(self.aborted)

        self.setModal(True)
        # =====================================================================
        self.state: AbsWorkflowProgressState = WorkflowProgressStateIdle(self)
        # =====================================================================

        # Seems to be causing the segfault
        # self.finished.connect(self.clean_local_console)

        self.finished.connect(self.remove_log_handles)

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self.flush)
        self.finished.connect(self.stop_timer)
        self._refresh_timer.start(100)

    def stop_timer(self) -> None:
        self._refresh_timer.stop()

    def clean_local_console(self) -> None:
        # CRITICAL: Running self.console.clear() seems to cause A SEGFAULT when
        # shutting down!!!
        self._console_data.clear()

    @property
    def current_state(self) -> str:
        return self.state.state_name

    def closeEvent(  # pylint: disable=C0103
            self,
            event: QtGui.QCloseEvent
    ) -> None:
        self.state.close_dialog(event)

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

    @QtCore.Slot(int)
    def set_total_jobs(self, value: int) -> None:
        self.progress_bar.setMaximum(value)

    @QtCore.Slot(int)
    def set_current_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)

    def write_to_console(self, text: str, level: int = logging.INFO) -> None:
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
