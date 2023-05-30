"""Dialog boxes."""
import abc
import logging
import logging.handlers
import sys
import typing
import warnings
import time
from typing import Optional, Sequence

from PySide6 import QtWidgets, QtGui, QtCore  # type: ignore

try:  # pragma: no cover
    from importlib import metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore

try:  # pragma: no cover
    from importlib.resources import as_file
    from importlib import resources
except ImportError:  # pragma: no cover
    import importlib_resources as resources  # type: ignore
    from importlib_resources import as_file  # type: ignore

import speedwagon
from speedwagon.reports import ExceptionReport
from speedwagon.frontend.qtwidgets import logging_helpers, ui_loader
import speedwagon.frontend.qtwidgets.ui

__all__ = ["SystemInfoDialog", "WorkProgressBar", "about_dialog_box"]

ALREADY_STOPPED_MESSAGE = "Already stopped"


class ErrorDialogBox(QtWidgets.QMessageBox):
    """Dialog box for Error Messages causes while running a job."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        """Create a error dialog box."""
        super().__init__(parent)
        self.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        self.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Abort)
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
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        text_edit = typing.cast(
            Optional[QtWidgets.QTextEdit], self.findChild(QtWidgets.QTextEdit)
        )

        if text_edit is not None:
            text_edit.setMinimumHeight(100)
            text_edit.setMaximumHeight(16777215)
            text_edit.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Expanding,
            )

        return result


class WorkProgressBar(QtWidgets.QProgressDialog):
    """Use this for showing progress."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0),
    ) -> None:
        """Create a work progress dialog window."""
        super().__init__(parent, flags)
        self.setModal(True)
        self.setMinimumHeight(100)
        self.setMinimumWidth(250)
        self._label = QtWidgets.QLabel(parent=self)
        self._label.setWordWrap(True)
        self.setLabel(self._label)

    def resizeEvent(
        self, event: QtGui.QResizeEvent  # pylint: disable=C0103
    ) -> None:
        super().resizeEvent(event)
        self._label.setMaximumWidth(self.width())
        self.setMinimumHeight(self._label.sizeHint().height() + 75)


def about_dialog_box(parent: QtWidgets.QWidget) -> None:
    """Launch the about speedwagon dialog box."""
    try:
        pkg_metadata: metadata.PackageMetadata = metadata.metadata(
            "speedwagon"
        )

        summary = pkg_metadata["Summary"]
        version = pkg_metadata["Version"]
        message = (
            f"{speedwagon.__name__.title()}: {version}"
            f"\n"
            f"\n"
            f"{summary}"
        )

    except metadata.PackageNotFoundError:
        message = f"{speedwagon.__name__.title()}"

    QtWidgets.QMessageBox.about(parent, "About", message)


class SystemInfoDialog(QtWidgets.QDialog):
    """System information dialog window."""

    # parent: QWidget = None, flags: Union[
    #     Qt.WindowFlags, Qt.WindowType] = Qt.WindowFlags()
    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0),
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

        self._button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        # pylint: disable=no-member
        self._button_box.accepted.connect(self.accept)  # type: ignore
        layout.addWidget(self._button_box)

    @staticmethod
    def get_installed_packages() -> Sequence[str]:
        """Get list of strings of installed packages."""
        pkgs = sorted(
            metadata.distributions(), key=lambda x: x.metadata["Name"].upper()
        )
        return [f"{x.metadata['Name']} {x.metadata['Version']}" for x in pkgs]


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

    def close_dialog(self, event: QtGui.QCloseEvent) -> None:
        """User clicks on close window."""
        event.accept()

    @staticmethod
    def set_buttons_to_close_only(
        button_box: QtWidgets.QDialogButtonBox,
    ) -> None:
        cancel_button: QtWidgets.QPushButton = button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )

        cancel_button.setEnabled(False)

        close_button: QtWidgets.QPushButton = button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        close_button.setEnabled(True)

    def reset_cancel_button(self) -> None:
        cancel_button: QtWidgets.QPushButton = self.context.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
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
        cancel_button: QtWidgets.QPushButton = self.context.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        cancel_button.setEnabled(False)
        self.context.rejected.connect(  # type: ignore
            self.context.button_box.rejected  # type: ignore
        )

    def start(self) -> None:
        self.context.state = WorkflowProgressStateWorking(self.context)


class WorkflowProgressStateWorking(AbsWorkflowProgressState):
    state_name = "working"

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)

        cancel_button: QtWidgets.QPushButton = self.context.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        cancel_button.setEnabled(True)
        self.context.button_box.rejected.disconnect()  # type: ignore
        close_button: QtWidgets.QPushButton = self.context.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        close_button.setEnabled(False)

    def start(self) -> None:
        warnings.warn("Already started")

    def stop(self) -> None:
        self.context.state = WorkflowProgressStateStopping(self.context)

    def close_dialog(self, event: QtGui.QCloseEvent) -> None:
        dialog = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Icon.Information,
            "Trying to stop job.",
            "Trying to stop job?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        if dialog.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
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

        cancel_button: QtWidgets.QPushButton = self.context.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )

        cancel_button.setText("Force Quit")

        self.context.progress_bar.setMaximum(0)
        self.context.progress_bar.setMinimum(0)

    def start(self) -> None:
        warnings.warn("Already started")

    def stop(self) -> None:
        dialog = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Icon.Information,
            "Trying to stop job.",
            "Do you want to force quit?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        if dialog.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            sys.exit(1)
        warnings.warn("Already stopping")


class WorkflowProgressStateAborted(AbsWorkflowProgressState):
    state_name = "aborted"

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self.reset_cancel_button()
        self.set_progress_to_none(context.progress_bar)
        self.set_buttons_to_close_only(context.button_box)
        close_button: QtWidgets.QPushButton = self.context.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        self.context.write_to_console("Successfully aborted")
        self.context.banner.setText("Aborted")
        close_button.clicked.connect(self.context.accept)  # type: ignore

    def stop(self) -> None:
        warnings.warn(ALREADY_STOPPED_MESSAGE)


class WorkflowProgressStateFailed(AbsWorkflowProgressState):
    state_name = "failed"

    def __init__(self, context: "WorkflowProgress"):
        super().__init__(context)
        self.reset_cancel_button()
        self.set_progress_to_none(context.progress_bar)
        self.set_buttons_to_close_only(context.button_box)
        close_button: QtWidgets.QPushButton = self.context.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        close_button.clicked.connect(self.context.reject)  # type: ignore
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
        close_button: QtWidgets.QPushButton = self.context.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        close_button.setFocus()
        close_button.clicked.connect(self.context.accept)  # type: ignore
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
    button_box: QtWidgets.QDialogButtonBox
    banner: QtWidgets.QLabel
    progress_bar: QtWidgets.QProgressBar
    console: QtWidgets.QTextBrowser

    def __init__(
        self, parent: typing.Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)

        # All ui info is located in the .ui file. Any graphical changes should
        # be make in there.
        with as_file(
            resources.files("speedwagon.frontend.qtwidgets.ui").joinpath(
                "workflow_progress.ui"
            )
        ) as ui_file:
            ui_loader.load_ui(str(ui_file), self)

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

        # The extra typehint is to fix typehints due to the way
        # QtGui.QTextCursor is reporting it as Callable[[QWidget], QCursor]
        self.cursor: QtGui.QTextCursor = QtGui.QTextCursor(self._console_data)

        self.cursor.movePosition(self.cursor.MoveOperation.End)

    def write_html_block_to_console(self, html: str) -> None:
        self.cursor.beginEditBlock()
        self.cursor.insertHtml(html.strip())
        self.cursor.endEditBlock()

    def flush(self) -> None:
        if self._log_handler is not None:
            self._log_handler.flush()

    def attach_logger(self, logger: logging.Logger) -> None:
        self._parent_logger = logger
        self._log_handler = logging_helpers.QtSignalLogHandler(self)
        self._log_handler.signals.messageSent.connect(
            self.write_html_block_to_console
        )
        formatter = logging_helpers.ConsoleFormatter()
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
        self, parent: typing.Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)

        # =====================================================================

        mono_font = QtGui.QFontDatabase.systemFont(
            QtGui.QFontDatabase.SystemFont.FixedFont
        )

        self._console_data.setDefaultFont(mono_font)

        # pylint: disable=no-member
        typing.cast(
            QtCore.SignalInstance,
            self._console_data.contentsChanged,  # type: ignore
        ).connect(self._follow_text)

        self.console.setMinimumWidth(self.calculate_window_width(mono_font))

        self.console.setDocument(self._console_data)
        # =====================================================================
        self.button_box.button(  # type: ignore
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        ).clicked.connect(self.aborted)

        self.setModal(True)
        # =====================================================================
        self.state: AbsWorkflowProgressState = WorkflowProgressStateIdle(self)
        # =====================================================================

        self.finished.connect(self.remove_log_handles)  # type: ignore

    def clean_local_console(self) -> None:
        # CRITICAL: Running self.console.clear() seems to cause A SEGFAULT when
        # shutting down!!!
        self._console_data.clear()

    @property
    def current_state(self) -> str:
        return self.state.state_name

    def closeEvent(  # pylint: disable=C0103
        self, event: QtGui.QCloseEvent
    ) -> None:
        self.state.close_dialog(event)

    def _follow_text(self) -> None:
        cursor = QtGui.QTextCursor(self._console_data)
        cursor.movePosition(cursor.MoveOperation.End)
        self.console.setTextCursor(cursor)

    @staticmethod
    def calculate_window_width(
        font_used: QtGui.QFont, characters_width: int = 80
    ) -> int:
        return QtGui.QFontMetrics(font_used).horizontalAdvance(
            "*" * characters_width
        )

    def start(self) -> None:
        self.state.start()

    def stop(self) -> None:
        self.state.stop()

    def failed(self) -> None:
        state = WorkflowProgressStateFailed(context=self)
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
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.beginEditBlock()
        if level == logging.DEBUG:
            cursor.insertHtml(f"<div><i>{text}</i></div>")
        elif level == logging.WARNING:
            cursor.insertHtml(f'<div><font color="yellow">{text}</font></div>')
        elif level == logging.ERROR:
            cursor.insertHtml(f'<div><font color="red">{text}</font></div>')
        else:
            cursor.insertHtml(f"<div>{text}</div>")

        cursor.insertText("\n")
        cursor.endEditBlock()


class AbsSaveReport(abc.ABC):  # pylint: disable=R0903
    qt_parent: QtWidgets.QWidget
    default_name: str

    @abc.abstractmethod
    def save(self, data: str) -> None:
        """Save data to a file."""


class SaveReportDialogBox(AbsSaveReport):
    def __init__(self) -> None:
        self.default_name = "report.txt"
        self.qt_parent: QtWidgets.QWidget = QtWidgets.QWidget()

    def save(self, data: str) -> None:
        while True:
            log_file_name: Optional[str]
            log_file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.qt_parent,
                "Export crash data",
                self.default_name,
                "Text Files (*.txt)",
            )
            if not log_file_name:
                return
            if self.write_data(log_file_name, data) is False:
                continue
            print(f"Save crash info to {log_file_name}")
            break

    def write_data(self, file_name: str, data: str) -> bool:
        """Write data to a file.

        Returns True on success and False on failure.
        """
        try:
            with open(file_name, "w", encoding="utf-8") as file_handle:
                file_handle.write(data)
            return True
        except OSError as error:
            message_box = QtWidgets.QMessageBox(self.qt_parent)
            message_box.setText("Saving data failed")
            message_box.setDetailedText(str(error))
            message_box.exec()
            return False


class SpeedwagonExceptionDialog(QtWidgets.QMessageBox):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setIcon(self.Icon.Critical)
        self.report_strategy = ExceptionReport()
        self.save_report_strategy: AbsSaveReport = SaveReportDialogBox()

        self.setText("Speedwagon has hit an exception")
        self.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Close)

        self.export_button = self.addButton(
            "Export Details", QtWidgets.QMessageBox.ButtonRole.ActionRole
        )
        self.export_button.clicked.disconnect()
        self.export_button.clicked.connect(self.export_information)

    def export_information(self) -> None:
        epoch_in_minutes = int(time.time() / 60)
        file_name = f"speedwagon_crash_{epoch_in_minutes}.txt"
        self.save_report_strategy.default_name = file_name
        self.save_report_strategy.qt_parent = self
        self.save_report_strategy.save(self.report_strategy.report())

    @property
    def exception(self) -> Optional[BaseException]:
        return self.report_strategy.exception

    @exception.setter
    def exception(self, value: BaseException) -> None:
        self.report_strategy.exception = value
        self.setWindowTitle(self.report_strategy.title())
        summary = self.report_strategy.summary()
        if summary:
            self.setInformativeText(summary)
