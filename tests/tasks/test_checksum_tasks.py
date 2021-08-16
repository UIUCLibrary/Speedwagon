from unittest.mock import MagicMock, patch, mock_open

from speedwagon.tasks import validation


class TestMakeChecksumTask:
    def test_work(self, monkeypatch):
        import os
        source_path = os.path.join("some", "source", "path")
        filename = "filename"
        checksum_report = "checksum_report"
        task = validation.MakeChecksumTask(
            source_path=source_path,
            filename=filename,
            checksum_report=checksum_report
        )
        hash_value = "164e5c004f7468f23605f571d9a19cf9"

        monkeypatch.setattr(
            validation.checksum,
            "calculate_md5_hash",
            lambda x: hash_value
        )

        assert \
            task.work() is True and \
            task.results[validation.ResultsValues.SOURCE_HASH] == hash_value


class TestMakeCheckSumReportTask:
    def test_work(self):
        output_filename = "output_filename"
        checksum_calculations = [MagicMock()]
        task = validation.MakeCheckSumReportTask(
            output_filename=output_filename,
            checksum_calculations=checksum_calculations
        )

        m = mock_open()
        with patch('speedwagon.tasks.validation.open', m):
            assert task.work() is True
        assert m.called is True
