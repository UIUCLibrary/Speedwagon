from unittest.mock import MagicMock, patch, mock_open

from speedwagon.tasks import checksum_tasks


class TestMakeChecksumTask:
    def test_work(self, monkeypatch):
        import os
        source_path = os.path.join("some", "source", "path")
        filename = "filename"
        checksum_report = "checksum_report"
        task = checksum_tasks.MakeChecksumTask(
            source_path=source_path,
            filename=filename,
            checksum_report=checksum_report
        )
        hash_value = "164e5c004f7468f23605f571d9a19cf9"

        monkeypatch.setattr(
            checksum_tasks.checksum,
            "calculate_md5_hash",
            lambda x: hash_value
        )

        assert \
            task.work() is True and \
            task.results[
                checksum_tasks.ResultsValues.SOURCE_HASH
            ] == hash_value


class TestMakeCheckSumReportTask:
    def test_work(self):
        output_filename = "output_filename"
        checksum_calculations = [MagicMock()]
        task = checksum_tasks.MakeCheckSumReportTask(
            output_filename=output_filename,
            checksum_calculations=checksum_calculations
        )

        m = mock_open()
        with patch('speedwagon.tasks.checksum_tasks.open', m):
            assert task.work() is True
        assert m.called is True
