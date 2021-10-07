"""Logging related stuff."""

import logging
from typing import Callable


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
