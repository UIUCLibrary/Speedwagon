"""Logging related stuff."""

import logging
from logging import LogRecord
import logging.handlers

from typing import Callable
from PyQt5 import QtCore


class GuiLogHandler(logging.handlers.BufferingHandler):
    """Logger designed for gui."""

    def __init__(
            self,
            callback: Callable[[str], None],
    ) -> None:
        """Create a gui log handler."""
        super().__init__(capacity=5)
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        """Emit logged message to callback function."""
        self.callback(logging.Formatter().format(record))


class SignalLogHandler(logging.handlers.BufferingHandler):
    """Qt Signal based log handler.

    Emits the log as a signal.

    Warnings:
         This is problematic, the signal could be GC and cause a segfault
    """

    def __init__(self, signal: QtCore.pyqtBoundSignal) -> None:
        """Create a new log handler for Qt signals."""
        super().__init__(capacity=10)
        self._signal = signal

    def shouldFlush(self, record: LogRecord) -> bool:
        return super().shouldFlush(record)

    def emit(self, record: LogRecord) -> None:
        """Emit the record."""
        result = logging.Formatter().format(record)
        self._signal.emit(result, record.levelno)


class ConsoleFormatter(logging.Formatter):
    """Formatter for converting log records into html based logging format."""

    @staticmethod
    def _debug(text: str) -> str:
        return f"<div><i>{text}</i></div>"

    @staticmethod
    def _warning(text: str) -> str:
        return f"<div><font color=\"yellow\">{text}</font></div>"

    @staticmethod
    def _error(text: str) -> str:
        return f"<div><font color=\"red\">{text}</font></div>"

    def format(self, record: LogRecord) -> str:
        """Format record for an html based console."""
        level = record.levelno
        text = super().format(record)
        text = text.replace("\n", "<br>")

        if level == logging.DEBUG:
            return self._debug(text)

        if level == logging.WARNING:
            return self._warning(text)

        if level == logging.ERROR:
            return self._error(text)

        return f"<div>{text}</div>"
