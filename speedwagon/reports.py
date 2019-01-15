def add_report_borders(func):
    def wrapper(*args, **kwargs):
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