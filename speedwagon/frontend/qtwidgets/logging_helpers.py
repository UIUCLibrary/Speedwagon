"""Logging related stuff."""
from __future__ import annotations

import abc
import logging
from logging.handlers import BufferingHandler
import typing

from typing import Optional
from PySide6 import QtCore

if typing.TYPE_CHECKING:
    from logging import LogRecord

__all__ = ["QtSignalLogHandler"]


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
        return f'<div><font color="yellow">{text}</font><br></div>'

    def format_error(self, text: str, record: LogRecord) -> str:
        """Format error messages in red."""
        return f'<div><font color="red">{text}</font><br></div>'

    def format_info(self, text: str, record: LogRecord) -> str:
        """No special formatting for info messages."""
        return f"{text}<br>"


class VerboseConsoleFormatStyle(AbsConsoleFormatter):
    """Verbose console formatter that includes more information.

    This adds message level (debug, warning, etc) and running thread to the
    message.
    """

    @staticmethod
    def _basic_format(record: LogRecord) -> str:
        return (
            logging.Formatter(
                "[%(levelname)s] (%(threadName)-10s) %(message)s"
            )
            .format(record)
            .replace("\n", "<br>")
        )

    def format_debug(self, text: str, record: LogRecord) -> str:
        """Italicize debug messages."""
        return f"<div><i>{self._basic_format(record)}</i></div>"

    def format_warning(self, text: str, record: LogRecord) -> str:
        """Format warning messages in yellow."""
        return f"""<div>
            <font color=\"yellow\">{self._basic_format(record)}</font>
            </div>"""

    def format_error(self, text: str, record: LogRecord) -> str:
        """Format error messages in red."""
        return f"""<div>
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
        """Format record for html based consoles."""
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


class QtSignalLogHandler(BufferingHandler):
    """Log handler for Qt signals."""

    class Signals(QtCore.QObject):  # pylint: disable=R0903
        """Qt Signals.

        This needs of be an inner class because Qt/PySide does not like mixing
        Qt parent classes with Python ones.
        """

        messageSent = QtCore.Signal(str)

    # This needs of be an inner class because Qt/PySide does not like mixing
    # Qt parent classes with Python ones.
    signals: Optional[Signals]

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        """Create a new QtSignalLogHandler object.

        Args:
            parent: Qt Object the handler is tied to keep it from being GC or
                deleted too early.
        """
        super().__init__(capacity=100)
        self._parent = parent
        self.signals = None
        self._register()
        if self._parent:
            self._parent.destroyed.connect(lambda: self._unregister)

        self.flush_timer = QtCore.QTimer(parent)
        self.flush_timer.timeout.connect(self.flush)
        self.flush_timer.start(100)

    def _register(self) -> None:
        self.signals = self.Signals(self._parent)

    def _unregister(self) -> None:
        self.signals = None

    def flush(self) -> None:
        """Flush log buffer.

        Notes:
            If the buffer is empty, no signal with be emitted.
        """
        if self.signals and len(self.buffer) > 0:
            results = [self.format(log).strip() for log in self.buffer]
            self.signals.messageSent.emit("".join(results))
        super().flush()
