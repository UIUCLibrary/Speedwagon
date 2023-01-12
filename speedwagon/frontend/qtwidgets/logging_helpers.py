"""Logging related stuff."""
from __future__ import annotations

import abc
import logging
import typing
from logging import handlers

from typing import Callable
if typing.TYPE_CHECKING:
    from logging import LogRecord
    from PySide6 import QtCore, QtWidgets


class GuiLogHandler(handlers.BufferingHandler):
    """Logger designed for gui."""

    def __init__(
            self,
            callback: Callable[[str], None],
    ) -> None:
        """Create a gui log handler."""
        super().__init__(capacity=5)
        self.callback = callback

    def emit(self, record: LogRecord) -> None:
        """Emit logged message to callback function."""
        self.callback(logging.Formatter().format(record))


class SignalLogHandler(handlers.BufferingHandler):
    """Qt Signal based log handler.

    Emits the log as a signal.

    Warnings:
         This is problematic, the signal could be GC and cause a segfault
    """

    def __init__(self, signal: QtCore.SignalInstance) -> None:
        """Create a new log handler for Qt signals."""
        super().__init__(capacity=10)
        self._signal = signal

    def emit(self, record: LogRecord) -> None:
        """Emit the record."""
        result = logging.Formatter().format(record)
        self._signal.emit(result, record.levelno)


class AbsConsoleFormatter(abc.ABC):
    """Formatter for generating HTML formatted text."""

    @abc.abstractmethod
    def format_debug(self, text: str, record: LogRecord) -> str:
        """Format a debug message."""

    @abc.abstractmethod
    def format_warning(self, text: str, record: LogRecord) -> str:
        """Format a warning message."""

    @abc.abstractmethod
    def format_error(self, text: str, record: LogRecord) -> str:
        """Format an error message."""

    @abc.abstractmethod
    def format_info(self, text: str, record: LogRecord) -> str:
        """Format a standard message."""


class DefaultConsoleFormatStyle(AbsConsoleFormatter):
    """Standard Format for a console.

    Red for Errors.
    Yellow for Warnings.
    Italics for Debug Messages.
    No formatting for info Messages.
    """

    def format_debug(self, text: str, record: LogRecord) -> str:
        """Italicize debug messages."""
        return f"<div><i>{text}</i><br></div>"

    def format_warning(self, text: str, record: LogRecord) -> str:
        """Format warning messages in yellow."""
        return f"<div><font color=\"yellow\">{text}</font><br></div>"

    def format_error(self, text: str, record: LogRecord) -> str:
        """Format error messages in red."""
        return f"<div><font color=\"red\">{text}</font><br></div>"

    def format_info(self, text: str, record: LogRecord) -> str:
        """No special formatting for info messages."""
        return f"{text}<br>"


class VerboseConsoleFormatStyle(AbsConsoleFormatter):
    """Verbose console formatter that includes more information.

    This adds message level (debug, warning, etc) and running thread to the
    message.
    """

    @staticmethod
    def _basic_format(record: LogRecord):
        return logging.Formatter(
            '[%(levelname)s] (%(threadName)-10s) %(message)s'
        ).format(record).replace("\n", "<br>")

    def format_debug(self, text: str, record: LogRecord) -> str:
        """Italicize debug messages."""
        return f"<div><i>{self._basic_format(record)}</i></div>"

    def format_warning(self, text: str, record: LogRecord) -> str:
        """Format warning messages in yellow."""
        return \
            f"""<div>
            <font color=\"yellow\">{self._basic_format(record)}</font>
            </div>"""

    def format_error(self, text: str, record: LogRecord) -> str:
        """Format error messages in red."""
        return \
            f"""<div>
            <font color=\"red\">{self._basic_format(record)}</font>
            </div>"""

    def format_info(self, text: str, record: LogRecord) -> str:
        """No special formatting for info messages."""
        return f"<div>{self._basic_format(record)}</div>"


class ConsoleFormatter(logging.Formatter):
    """Formatter for converting log records into html based logging format."""

    def __init__(self, *args, **kwargs) -> None:
        """Set a new console formatter.

        Verbose defaults to false.
        """
        super().__init__(*args, **kwargs)
        self.verbose = False

    def format(self, record: LogRecord) -> str:
        """Format record for an html based console."""
        formatters: typing.Dict[bool, typing.Type[AbsConsoleFormatter]] = {
            False: DefaultConsoleFormatStyle,
            True: VerboseConsoleFormatStyle,

        }

        formatter: AbsConsoleFormatter = formatters[self.verbose]()
        text = super().format(record).strip()
        text = text.replace("\n", "<br>")

        level = record.levelno
        if level == logging.DEBUG:
            return formatter.format_debug(text, record)

        if level == logging.WARNING:
            return formatter.format_warning(text, record)

        if level == logging.ERROR:
            return formatter.format_error(text, record)

        return formatter.format_info(text, record)


class SplashScreenLogHandler(logging.Handler):
    """Log handler for splash screen."""

    def __init__(self,
                 widget: QtWidgets.QWidget,
                 level: int = logging.NOTSET) -> None:
        """Create a new splash screen log handler."""
        super().__init__(level)
        self.widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        """Write logging message on the splash screen widget."""
        self.widget.showMessage(
            self.format(record),
            QtCore.Qt.AlignmentFlag.AlignCenter,
        )
