import logging
from unittest.mock import Mock

import pytest

from speedwagon.tasks import filesystem
from speedwagon.tasks.tasks import TaskStatus


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

def test_delete_directory_task_description():
    assert filesystem.delete_directory.task_description() == "Removing directory"

def test_delete_directory_not_deleting_when_called(monkeypatch):
    rmdir = Mock(name='rmdir')
    monkeypatch.setattr(filesystem.os, "rmdir", rmdir)
    filesystem.delete_directory("some_directory")
    rmdir.assert_not_called()

def test_delete_directory_with_exec(monkeypatch):
    rmdir = Mock(name='rmdir')
    monkeypatch.setattr(filesystem.os, "rmdir", rmdir)
    task = filesystem.delete_directory("some_directory")
    rmdir.assert_not_called()
    task.exec()
    rmdir.assert_called_once_with("some_directory")

def test_delete_directory_with_exec_has_results(monkeypatch):
    rmdir = Mock(name='rmdir')
    monkeypatch.setattr(filesystem.os, "rmdir", rmdir)
    task = filesystem.delete_directory("some_directory")
    rmdir.assert_not_called()
    task.exec()
    result = task.task_result
    assert result.data == "some_directory"
    assert result.source == filesystem.delete_directory.func

def test_delete_directory_with_changes_status(monkeypatch):
    rmdir = Mock(name='rmdir')
    monkeypatch.setattr(filesystem.os, "rmdir", rmdir)
    task = filesystem.delete_directory("some_directory")
    assert task.status == TaskStatus.IDLE
    task.exec()
    assert task.status == TaskStatus.SUCCESS

def test_delete_directory_with_changes_to_fail_on_exception(monkeypatch):
    rmdir = Mock(name='rmdir', side_effect=FileNotFoundError("no directory"))
    monkeypatch.setattr(filesystem.os, "rmdir", rmdir)
    task = filesystem.delete_directory("some_directory")
    assert task.status == TaskStatus.IDLE
    try:
        task.exec()
    except FileNotFoundError:
        pass
    assert task.status == TaskStatus.FAILED

@pytest.mark.parametrize("level,expected_error_messages", [
    (logging.DEBUG, ["Deleting some_directory", "Deleted some_directory"]),
    (logging.INFO, ["Deleted some_directory"]),
    (logging.WARN, []),
])
def test_delete_directory_logging(monkeypatch, caplog, level, expected_error_messages):
    rmdir = Mock(name='rmdir')
    monkeypatch.setattr(filesystem.os, "rmdir", rmdir)
    task = filesystem.delete_directory("some_directory", verbosity=logging.DEBUG)
    with caplog.at_level(level):
        task.exec()
    assert all(
        expect_message == log_record.message
        for expect_message, log_record
        in zip(expected_error_messages, caplog.records)
    ), (f"expected {expected_error_messages}, "
        f"got {[record.message for record in caplog.records]}")


def test_delete_file_with_exec(monkeypatch):
    remove = Mock(name='rmdir')
    monkeypatch.setattr(filesystem.os, "remove", remove)
    task = filesystem.delete_file("some_file.txt")
    remove.assert_not_called()
    task.exec()
    remove.assert_called_once_with("some_file.txt")
