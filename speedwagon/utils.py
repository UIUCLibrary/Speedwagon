from typing import Iterator

import logging
from contextlib import contextmanager


@contextmanager
def log_config(logger: logging.Logger, callback) -> Iterator[None]:
    """Configure logs so they get forwarded to the speedwagon console.

    Args:
        logger:

    """
    try:
        from speedwagon.frontend.qtwidgets.logging_helpers import GuiLogHandler
        log_handler: logging.Handler = GuiLogHandler(callback)
    except ImportError:
        log_handler: logging.Handler = logging.StreamHandler()

    try:
        logger.addHandler(log_handler)
        yield
    finally:
        logger.removeHandler(log_handler)
