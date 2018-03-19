import io
import logging
import queue
import time
import typing
import concurrent.futures
import pytest
import pickle
import forseti.tasks
from forseti import worker
from forseti.tasks import TaskBuilder


class SimpleSubtask(forseti.tasks.Subtask):

    def __init__(self, message):
        super().__init__()
        self.message = message

    def work(self) -> bool:
        self.log("processing")
        self.results = self.message
        return True

    @property
    def settings(self):
        return {"r": "ad"}


class SimpleMultistage(forseti.tasks.MultiStageTask):
    def process_subtask_results(self, subtask_results: typing.List[typing.Any]) -> typing.Any:
        return "\n".join(subtask_results)


class SimpleTaskBuilder(forseti.tasks.AbsTaskBuilder):

    @property
    def task(self) -> SimpleMultistage:
        return SimpleMultistage()


@pytest.fixture
def simple_task_builder():
    builder = TaskBuilder(SimpleTaskBuilder())
    builder.add_subtask(subtask=SimpleSubtask("got it"))
    return builder


def test_task_builder(simple_task_builder):
    task = simple_task_builder.build_task()

    assert isinstance(task, forseti.tasks.MultiStageTask)

    assert len(task.subtasks) == 1

    assert isinstance(task.subtasks[0], SimpleSubtask)

    assert task.progress == 0.0


def test_task_progress(simple_task_builder):
    task = simple_task_builder.build_task()
    task.exec()
    assert task.progress == 1.0


def test_task_results(simple_task_builder):
    task = simple_task_builder.build_task()
    task.exec()
    assert isinstance(task.result, str)
    assert task.result == "got it"


def test_task_logs(simple_task_builder):
    task = simple_task_builder.build_task()
    task.exec()
    assert len(task.log_q) == 1


def test_task_with_2_subtask_results(simple_task_builder):
    simple_task_builder.add_subtask(subtask=SimpleSubtask("got it"))
    task = simple_task_builder.build_task()
    task.exec()
    assert isinstance(task.result, str)
    assert task.result == "got it\ngot it"


def test_task_log_with_2_subtask(simple_task_builder):
    simple_task_builder.add_subtask(subtask=SimpleSubtask(message="got it"))
    task = simple_task_builder.build_task()
    task.exec()
    assert len(task.log_q) == 2


def test_task_can_be_picked():
    builder = TaskBuilder(SimpleTaskBuilder())
    builder.add_subtask(subtask=SimpleSubtask(message="got it"))

    task_original = builder.build_task()
    serialized = TaskBuilder.save(task_original)

    task_unserialized = TaskBuilder.load(serialized)
    assert task_original.name == task_unserialized.name

    # with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executer:
    #     future = executer.submit(print, "hello")


def execute_task(new_task):
    new_task.exec()
    return new_task.result


def test_task_as_concurrent_future(simple_task_builder):
    new_task = simple_task_builder.build_task()

    futures = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
        futures.append(executor.submit(execute_task, new_task))

        for future in concurrent.futures.as_completed(futures):
            assert "got it" == future.result()


@pytest.fixture
def simple_task_builder_with_2_subtasks():
    builder = TaskBuilder(SimpleTaskBuilder())
    builder.add_subtask(subtask=SimpleSubtask("First"))
    builder.add_subtask(subtask=SimpleSubtask("Second"))
    return builder


@pytest.mark.adapter
def test_adapter_results(simple_task_builder_with_2_subtasks):
    new_task = simple_task_builder_with_2_subtasks.build_task()

    with worker.ToolJobManager() as manager:
        for subtask in new_task.subtasks:
            adapted_tool = forseti.tasks.SubtaskJobAdapter(subtask)
            manager.add_job(adapted_tool, adapted_tool.settings)
        manager.start()
        results = list()
        for r in manager.get_results():
            results.append(r.data)


        assert len(results) == 2
        assert "First" == results[0]
        assert "Second" == results[1]


class LogCatcher(logging.Handler):

    def __init__(self, storage: list, level=logging.NOTSET):
        super().__init__(level)
        self.storage = storage

    def emit(self, record):
        self.storage.append(record)


@pytest.mark.adapter
def test_adapter_logs(simple_task_builder_with_2_subtasks):
    logs = []
    log_catcher = LogCatcher(logs)
    new_task = simple_task_builder_with_2_subtasks.build_task()

    with worker.ToolJobManager() as manager:
        manager.logger.setLevel(logging.INFO)
        manager.logger.addHandler(log_catcher)

        for subtask in new_task.subtasks:
            adapted_tool = forseti.tasks.SubtaskJobAdapter(subtask)
            manager.add_job(adapted_tool, adapted_tool.settings)
        manager.start()

        list(manager.get_results())

    assert len(logs) == 2
    assert logs[0].message == "processing"
    assert logs[1].message == "processing"
