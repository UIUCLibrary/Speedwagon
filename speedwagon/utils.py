"""General module for things that don't fit anywhere else."""

from __future__ import annotations

import os
import pathlib
from typing import Iterator, Callable, Dict, List, TYPE_CHECKING

import logging
from logging.handlers import BufferingHandler
from contextlib import contextmanager

if TYPE_CHECKING:
    from speedwagon.workflow import AbsOutputOptionDataType, UserDataType


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


def get_desktop_path() -> str:
    """Locate user's desktop.

    Throws FileNotFoundError if unsuccessful
    """
    home = pathlib.Path.home()
    desktop_path = home / "Desktop"
    if os.path.exists(desktop_path):
        return str(desktop_path)
    raise FileNotFoundError("No Desktop folder located")


def validate_user_input(
    options: Dict[str, AbsOutputOptionDataType]
) -> Dict[str, List[str]]:
    """Validate all user inputs and generate a dictionary of findings."""
    all_findings = {}
    for key, v in options.items():
        findings = []
        if v.required is True and any(
            [
                v.value is None,
                (isinstance(v.value, str) and v.value.strip() == ""),
            ]
        ):
            findings.append("Required value missing")
        else:
            findings += v.get_findings(
                job_args={key: option.value for key, option in options.items()}
            )

        if findings:
            all_findings[key] = findings
    return all_findings


def assign_values_to_job_options(
    job_params: List[AbsOutputOptionDataType], **option_values: UserDataType
) -> List[AbsOutputOptionDataType]:
    """Assign values to a list of job args."""
    for option in job_params:
        if option.setting_name in option_values:
            option.value = option_values[option.setting_name]
        elif option.label in option_values:
            option.value = option_values[option.label]
    return job_params
