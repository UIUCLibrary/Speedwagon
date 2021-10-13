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
        self._signal.emit(result, record.levelno)
