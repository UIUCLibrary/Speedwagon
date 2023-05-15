from unittest.mock import Mock
import pytest
from speedwagon import startup, job, Workflow, frontend

QtCore = pytest.importorskip("PySide6.QtCore")


# class TestSingleWorkflowLauncher:
#     @pytest.mark.parametrize("times_run_in_a_row", [1, 2, 5])
#     def test_commands_called(self, qtbot, monkeypatch, times_run_in_a_row):
#         from speedwagon.frontend.qtwidgets import dialog
#         import speedwagon.frontend.qtwidgets.gui_startup
#         monkeypatch.setattr(
#             speedwagon.frontend.qtwidgets.gui,
#             "MainWindow1",
#             Mock(
#                 spec=speedwagon.frontend.qtwidgets.gui.MainWindow1
#             )
#         )
#         monkeypatch.setattr(
#             dialog,
#             "WorkProgressBar",
#             Mock(spec=dialog.dialogs.WorkProgressBar)
#         )
#         for _ in range(times_run_in_a_row):
#             single_item_launcher = \
#                 frontend.qtwidgets.gui_startup.SingleWorkflowLauncher(app=None)
#
#
#
#
#             workflow = Mock(spec=Workflow)
#             workflow.discover_task_metadata = Mock(return_value=[])
#             workflow.name = "job"
#             workflow.__class__ = job.Workflow
#             workflow.validate_user_options = Mock(return_value=True)
#
#             monkeypatch.setattr(workflow, "create_new_task", Mock())
#             single_item_launcher.set_workflow(workflow)
#             single_item_launcher.options = {
#                 "Input": "somefakeinput",
#                 "Profile": "HathiTrust Tiff"
#             }
#             app_ = startup.ApplicationLauncher(strategy=single_item_launcher)
#             app_.initialize()
#             app_.run()
#             assert workflow.initial_task.called is True and \
#                    workflow.discover_task_metadata.called is True and \
#                    workflow.generate_report.called is True
#
#     def test_workflow_not_set_throw_exception_when_run(self):
#         pytest.importorskip("speedwagon.frontend.qtwidgets")
#         single_item_launcher = \
#             frontend.qtwidgets.gui_startup.SingleWorkflowLauncher(app=None)
#
#         with pytest.raises(AttributeError):
#             single_item_launcher.run()


class TestApplicationLauncher:
    def test_application_launcher_startup(self):
        strategy = Mock()
        app = startup.ApplicationLauncher(strategy=strategy)
        app.run()
        assert strategy.run.called is True
