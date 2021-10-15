"""Logging related stuff."""

import logging
from logging import LogRecord
from typing import Callable

from PyQt5 import QtCore


class GuiLogHandler(logging.Handler):
    """Logger designed for gui."""

    def __init__(
            self,
            callback: Callable[[str], None],
            level: int = logging.NOTSET
    ) -> None:
        """Create a gui log handler."""
        super().__init__(level)
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        """Emit logged message to callback function."""
        self.callback(logging.Formatter().format(record))


class SignalLogHandler(logging.Handler):
    # This is problematic, the signal could be GC and cause a segfault
    def __init__(self, signal: QtCore.pyqtBoundSignal) -> None:
        super().__init__()
        self._signal = signal

    def emit(self, record: LogRecord) -> None:
        result = logging.Formatter().format(record)
        # print(result)
        self._signal.emit(result, record.levelno)


class ConsoleFormatter(logging.Formatter):
    def _debug(self, text: str) -> str:
        return f"<div><i>{text}</i></div>"

    def _warning(self, text: str) -> str:
        return f"<div><font color=\"yellow\">{text}</font></div>"

    def _error(self, text: str) -> str:
        return f"<div><font color=\"red\">{text}</font></div>"

    def format(self, record: LogRecord) -> str:
        level = record.levelno
        text = super().format(record)
        text = text.replace("\n", "<br>")

        if level == logging.DEBUG:
            return self._debug(text)

        elif level == logging.WARNING:
            return self._warning(text)

        elif level == logging.ERROR:
            return self._error(text)

        else:
            return f"<div>{text}</div>"
