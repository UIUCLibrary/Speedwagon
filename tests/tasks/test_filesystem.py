from unittest.mock import Mock

import pytest

from speedwagon.tasks import filesystem


class TestDeleteFile:
    @pytest.fixture
    def task(self):
        return filesystem.DeleteFile("some_file.txt")

    def test_removal_called(self, monkeypatch, task):
        remove = Mock()
        monkeypatch.setattr(task, "remove", remove)
        task.work()
        assert remove.called is True

    def test_task_description(self, task):
        assert isinstance(task.task_description(), str)


class TestDeleteDirectory:
    @pytest.fixture
    def task(self):
        return filesystem.DeleteDirectory("somedirectory")

    def test_removal_called(self, monkeypatch, task):
        remove = Mock()
        monkeypatch.setattr(task, "remove", remove)
        task.work()
        assert remove.called is True

    def test_task_description(self, task):
        assert isinstance(task.task_description(), str)
