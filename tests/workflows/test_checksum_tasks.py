from speedwagon.workflows import checksum_tasks


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

        monkeypatch.setattr(
            checksum_tasks.checksum,
            "calculate_md5_hash",
            lambda x: "164e5c004f7468f23605f571d9a19cf9"
        )
        assert task.work() is True and \
            task.results[checksum_tasks.ResultsValues.SOURCE_HASH] == \
            "164e5c004f7468f23605f571d9a19cf9"
