import concurrent.futures
from unittest.mock import Mock

import pytest
worker = pytest.importorskip("speedwagon.frontend.qtwidgets.worker")
dialog = pytest.importorskip("speedwagon.frontend.qtwidgets.dialog")


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestProcessWorker:
    class DummyProcessWorker(worker.ProcessWorker):

        def complete_task(self, fut: concurrent.futures.Future) -> None:
            pass

        def on_completion(self, *args, **kwargs) -> None:
            pass

    def test_run_all_jobs_calls_on_completion(self):
        process_worker = TestProcessWorker.DummyProcessWorker(parent=Mock())
        process_worker.on_completion = Mock()
        process_worker.run_all_jobs()
        assert process_worker.on_completion.called is True


# @pytest.mark.filterwarnings("ignore::DeprecationWarning")
# class TestJobProcessor:
#     def test_process_flushes_buffer(self):
#         parent = Mock(spec=worker.ToolJobManager)
#         parent.futures = []
#         job_processor = worker.QtJobProcessor(parent)
#         list(job_processor.process())
#         assert parent.flush_message_buffer.called is True
#
#     def test_process_timeout_calls_timeout_callback(self, monkeypatch):
#         parent = Mock(spec=worker.ToolJobManager)
#         future = Mock(
#             spec=concurrent.futures.Future,
#         )
#         parent.futures = [
#             future
#         ]
#
#         def as_completed(fs, timeout=None):
#             parent.active = False
#             raise concurrent.futures.TimeoutError()
#
#         monkeypatch.setattr(
#             worker.concurrent.futures,
#             "as_completed",
#             as_completed
#         )
#
#         job_processor = worker.QtJobProcessor(parent)
#         job_processor.timeout_callback = Mock(name="timeout_callback")
#         all(job_processor.process())
#         assert job_processor.timeout_callback.called is True
