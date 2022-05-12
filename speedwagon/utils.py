from typing import Iterator, Callable

import logging
from contextlib import contextmanager


@contextmanager
def log_config(
        logger: logging.Logger,
        callback: Callable[[str], None]
) -> Iterator[None]:
    """Configure logs so they get forwarded to the speedwagon console.

    Args:
        logger:
        callback:

    """
    try:
        log_handler: logging.Handler
        from speedwagon.frontend.qtwidgets.logging_helpers import GuiLogHandler
        log_handler = GuiLogHandler(callback)
    except ImportError:
        log_handler = logging.StreamHandler()

    try:
        logger.addHandler(log_handler)
        yield
    finally:
        logger.removeHandler(log_handler)
