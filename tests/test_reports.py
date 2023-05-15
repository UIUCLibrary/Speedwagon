from speedwagon import reports


class TestExceptionReportExporter:
    def test_title(self):
        reporter = reports.ExceptionReport()
        reporter.exception = ValueError("This is wrong")
        assert reporter.title() == "ValueError"

    def test_title_empty(self):
        reporter = reports.ExceptionReport()
        assert reporter.title() == ""

    def test_report_empty(self):
        reporter = reports.ExceptionReport()
        assert reporter.report() == ""

    def test_report(self, monkeypatch):

        def format_tb(*_, **__):
            return [
                '  File "/opt/speedwagon/frontend/qtwidgets/tabs.py", '
                'line 102, in _handle_workflow_changed',
                '    self.workspace.set_workflow(workflow_klass)',
                '',
                '  File "/opt/speedwagon/frontend/qtwidgets/widgets.py", '
                'line 632, in set_workflow',
                '    models.ToolOptionsModel4(new_workflow.get_user_options())',
                '                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^',
                '',
                'File "/opt/speedwagon/workflows/workflow_completeness.py", '
                'line 45, in get_user_options'
                '    raise TypeError("I failed")'
            ]
        monkeypatch.setattr(reports.traceback, "format_tb", format_tb)
        reporter = reports.ExceptionReport()
        reporter.exception = ValueError("This is wrong")
        assert 'raise TypeError("I failed")' in reporter.report()

    def test_summary(self):
        reporter = reports.ExceptionReport()
        reporter.exception = ValueError("This is wrong")
        assert reporter.summary() == "This is wrong"

    def test_summary_empty(self):
        reporter = reports.ExceptionReport()
        assert reporter.summary() == ""
