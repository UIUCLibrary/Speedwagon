"""Common code to help generate reports for the user"""

import functools
import typing


def add_report_borders(
        func: typing.Callable[..., typing.Optional[str]]
) -> typing.Callable[..., typing.Optional[str]]:

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> typing.Optional[str]:
        report = func(*args, **kwargs)
        if report:
            line_sep = "\n" + "*" * 60

            return f"{line_sep}" \
                f"\n   Report" \
                f"{line_sep}" \
                f"\n" \
                f"\n{report}" \
                f"\n" \
                f"{line_sep}"
        return report
    return wrapper
