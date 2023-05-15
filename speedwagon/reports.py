"""Common code to help generate reports for the user."""
import abc
import functools
import typing
from typing import Optional
import traceback


def add_report_borders(
    func: typing.Callable[..., Optional[str]]
) -> typing.Callable[..., Optional[str]]:
    """Create a star character border around text report."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Optional[str]:
        report = func(*args, **kwargs)
        if report:
            line_sep = "\n" + "*" * 60

            return (
                f"{line_sep}"
                f"\n   Report"
                f"{line_sep}"
                f"\n"
                f"\n{report}"
                f"\n"
                f"{line_sep}"
            )
        return report

    return wrapper


class AbsReporter(abc.ABC):
    """Abstract base class for generating reports."""

    @abc.abstractmethod
    def title(self) -> str:
        """Get the title of the report."""

    @abc.abstractmethod
    def summary(self) -> str:
        """Get a summary of the report."""

    @abc.abstractmethod
    def report(self) -> str:
        """Get the full detailed report."""


class ExceptionReport(AbsReporter):
    """Report for Exceptions."""

    def __init__(self) -> None:
        """Generate an exception report class."""
        super().__init__()
        self.exception: Optional[BaseException] = None

    def title(self) -> str:
        """Report the exception type."""
        return self.exception.__class__.__name__ if self.exception else ""

    def summary(self) -> str:
        """Report the exception value."""
        return str(self.exception) if self.exception else ""

    def report(self) -> str:
        """Generate a report based on the exception traceback."""
        lines = []
        if self.exception:
            lines += traceback.format_tb(self.exception.__traceback__)
        return "\n".join(lines)
