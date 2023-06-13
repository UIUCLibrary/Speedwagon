"""General module for things that don't fit anywhere else."""

from typing import Iterator, Callable

import logging
from logging.handlers import BufferingHandler
from contextlib import contextmanager


@contextmanager
def log_config(
    logger: logging.Logger, callback: Callable[[str], None]
) -> Iterator[None]:
    """Configure logs so they get forwarded to the speedwagon console.

    Args:
        logger: logger to use.
        callback: callback function handle messages.

    """
    try:
        log_handler: logging.Handler
        log_handler = CallbackLogHandler(callback)
    except ImportError:
        log_handler = logging.StreamHandler()

    try:
        logger.addHandler(log_handler)
        yield
    finally:
        logger.removeHandler(log_handler)


class CallbackLogHandler(BufferingHandler):
    """Logger that runs a callback."""

    def __init__(
        self,
        callback: Callable[[str], None],
    ) -> None:
        """Create a log handler for callbacks."""
        super().__init__(capacity=5)
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        """Emit logged message to callback function."""
        self.callback(logging.Formatter().format(record))
