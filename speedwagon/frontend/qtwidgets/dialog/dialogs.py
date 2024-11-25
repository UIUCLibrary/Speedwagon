"""Dialog boxes."""
from __future__ import annotations
import abc
import logging
import logging.handlers
import os
import pathlib
import sys
import typing
import warnings
import time
from typing import (
    Optional,
    TYPE_CHECKING,
    Generic,
    Union,
    Callable,
    List,
    TypeVar,
)
# pylint: disable=wrong-import-position
from importlib import resources
from importlib.resources import as_file

if sys.version_info >= (3, 10):
    from importlib import metadata
else:
    import importlib_metadata as metadata

from PySide6 import QtWidgets, QtGui, QtCore  # type: ignore

from speedwagon.reports import ExceptionReport
from speedwagon.utils import get_desktop_path
from speedwagon.frontend.qtwidgets import logging_helpers, ui_loader
from speedwagon.frontend.qtwidgets.models import ItemTableModel
import speedwagon.frontend.qtwidgets.ui
from speedwagon.info import convert_package_metadata_to_string

if TYPE_CHECKING:
    from speedwagon.info import SystemInfo


__all__ = ["SystemInfoDialog", "WorkProgressBar", "about_dialog_box"]

ALREADY_STOPPED_MESSAGE = "Already stopped"
DEFAULT_WINDOW_FLAGS = QtCore.Qt.WindowType(0)


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
        flags: QtCore.Qt.WindowType = DEFAULT_WINDOW_FLAGS,
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
        """Resize event."""
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

    installed_packages_widget: QtWidgets.QListWidget
    export_to_file_button: QtWidgets.QToolButton
    export_to_file = QtCore.Signal(str, str)

    def __init__(
        self,
        system_info: SystemInfo,
        parent: Optional[QtWidgets.QWidget] = None,
        flags: QtCore.Qt.WindowType = DEFAULT_WINDOW_FLAGS,
    ) -> None:
        """Display System information."""
        super().__init__(parent, flags)

        with as_file(
                resources.files("speedwagon.frontend.qtwidgets.ui").joinpath(
                    "system_info_dialog.ui"
                )
        ) as ui_file:
            ui_loader.load_ui(str(ui_file), self)

        self.system_info = system_info
        installed_python_packages =\
            self.system_info.get_installed_packages(
                formatter=convert_package_metadata_to_string
            )
        self.installed_packages_widget.addItems(installed_python_packages)
        self.export_to_file_button.clicked.connect(
            self.request_export_system_information
        )

    def request_export_system_information(
            self,
            *_,
            save_dialog_box=QtWidgets.QFileDialog.getSaveFileName,
            **__,
    ) -> None:
        """Request system information be saved to a file."""
        file, file_format = save_dialog_box(
            self,
            "Save File",
            os.path.join(
                get_default_export_system_info_path(),
                "speedwagon-info.txt"
            ),
            "Text (*.txt)"
        )
        if file:
            self.export_to_file.emit(file, file_format)


def get_default_export_system_info_path() -> str:
    try:
        return get_desktop_path()
    except FileNotFoundError:
        return str(pathlib.Path.home())


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

    def start(self) -> None:  # noqa: B027
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
        warnings.warn(ALREADY_STOPPED_MESSAGE, stacklevel=2)

    def _set_button_defaults(self) -> None:
        cancel_button: QtWidgets.QPushButton = self.context.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        cancel_button.setEnabled(False)
        self.context.button_box.rejected.connect(self.context.rejected)

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
        warnings.warn("Already started", stacklevel=2)

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
        warnings.warn("Already started", stacklevel=2)

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
        warnings.warn("Already stopping", stacklevel=2)


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
        warnings.warn(ALREADY_STOPPED_MESSAGE, stacklevel=2)


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
        warnings.warn(ALREADY_STOPPED_MESSAGE, stacklevel=2)


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
        warnings.warn("Already Finished", stacklevel=2)


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
        if self._log_handler.signals is None:
            raise RuntimeError("attach_logger failed to connect signals")
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
        # self.rejected.disconnect(self.button_box.rejected)

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


_T = TypeVar("_T")
_R = TypeVar("_R")


class ItemSelectOptionDelegate(QtWidgets.QStyledItemDelegate):
    """Item selection delegate widget."""

    delegate_klass = QtWidgets.QComboBox

    def __init__(self, parent=None):
        super().__init__(parent)
        self.get_choices: Callable[
            [Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]],
            List[str],
        ] = lambda index: []

    def createEditor(  # pylint: disable=C0103,W0613
        self,
        parent: QtWidgets.QWidget,
        item: QtWidgets.QStyleOptionViewItem,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
    ) -> QtWidgets.QWidget:
        """Create editor widget."""
        editor = self.delegate_klass(parent)

        def commit_data():
            self.commitData.emit(editor)
        editor.currentIndexChanged.connect(commit_data)
        return editor

    def setEditorData(  # pylint: disable=C0103,W0613
        self,
        editor: QtCore.QObject,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
    ) -> None:
        """Set editor data."""
        editor = typing.cast(QtWidgets.QComboBox, editor)
        for i, selection in enumerate(self.get_choices(index)):
            editor.addItem(selection)
            if selection == index.data():
                editor.setCurrentIndex(i)

    def setModelData(  # pylint: disable=C0103
        self,
        widget: QtWidgets.QWidget,
        model: QtCore.QAbstractItemModel,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
    ) -> None:
        """Set model data."""
        widget = typing.cast(QtWidgets.QComboBox, widget)
        model.setData(
            index, widget.currentText(), role=QtCore.Qt.ItemDataRole.EditRole
        )


class ItemView(QtWidgets.QTreeView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditTriggers(

            # QtWidgets.QTreeView.EditTrigger.AllEditTriggers
            QtWidgets.QTreeView.EditTrigger.DoubleClicked
            | QtWidgets.QTreeView.EditTrigger.EditKeyPressed
            | QtWidgets.QTreeView.EditTrigger.SelectedClicked
        )
        self._item_select_delegate = ItemSelectOptionDelegate(self)

        self.delegate_choices: Callable[
            [Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]],
            List[str],
        ] = lambda index: []

        # pylint: disable=unnecessary-lambda
        self._item_select_delegate.get_choices = (
            lambda index: self.delegate_choices(index)
        )
        # pylint: enable=unnecessary-lambda

        self.setItemDelegate(self._item_select_delegate)


class TableEditDialog(QtWidgets.QDialog, Generic[_T, _R]):
    """Browser dialog for selecting title page."""

    def __init__(
        self,
        model: ItemTableModel[_T, _R],
        parent: typing.Optional[QtWidgets.QWidget] = None,
        flags: QtCore.Qt.WindowType = DEFAULT_WINDOW_FLAGS,
    ) -> None:
        """Create a package browser dialog window."""
        super().__init__(parent, flags)
        self._parent = parent
        self._model = model

        self._layout = QtWidgets.QGridLayout(self)

        self.view = ItemView(self)
        self.view.delegate_choices = self.delegate_selections
        self.view.setModel(self._model)

        self._buttons = QtWidgets.QButtonGroup(parent=self)
        self.ok_button = QtWidgets.QPushButton("Done")

        # pylint: disable=no-member
        self.ok_button.clicked.connect(self.accept)  # type: ignore
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)  # type: ignore

        self._layout.addWidget(self.view, 0, 0, 1, 4)

        self._buttons.addButton(self.ok_button)
        self._buttons.addButton(self.cancel_button)
        self._layout.addWidget(self.ok_button, 1, 2)
        self._layout.addWidget(self.cancel_button, 1, 3)
        self._layout.setColumnStretch(2, 0)
        self._layout.setColumnStretch(3, 0)
        self._layout.setColumnStretch(1, 1)

        # Configure the window settings
        # self.setWindowTitle("Title Page Selection")
        self.setMinimumWidth(640)
        self.setMinimumHeight(240)

    def delegate_selections(self, index):
        return self._model.data(index, ItemTableModel.OptionsRole)

    def data(self) -> Optional[_R]:
        """Get the results."""
        return self._model.results()
