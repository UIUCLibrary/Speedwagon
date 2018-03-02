import io
import queue
import time
import typing
import concurrent.futures
import pytest
import pickle
import forseti.tasks
from forseti import TaskBuilder, worker


class SimpleSubtask(forseti.tasks.Subtask):

    def work(self) -> bool:
        self.log("processing")
        self.result = "got it"
        return True


class SimpleMultistage(forseti.tasks.MultiStageTask):
    def process_subtask_results(self, subtask_results: typing.List[typing.Any]) -> typing.Any:
        return "\n".join(subtask_results)
    #
    # def exec(self, *args, **kwargs):
    #     return super().exec(*args, **kwargs)
    #


class SimpleTaskBuilder(forseti.tasks.AbsTaskBuilder):

    @property
    def task(self) -> SimpleMultistage:
        return SimpleMultistage()


@pytest.fixture
def simple_task_builder():
    builder = TaskBuilder(SimpleTaskBuilder())
    builder.add_subtask(subtask=SimpleSubtask())
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
    simple_task_builder.add_subtask(subtask=SimpleSubtask())
    task = simple_task_builder.build_task()
    task.exec()
    assert isinstance(task.result, str)
    assert task.result == "got it\ngot it"


def test_task_log_with_2_subtask(simple_task_builder):
    simple_task_builder.add_subtask(subtask=SimpleSubtask())
    task = simple_task_builder.build_task()
    task.exec()
    assert len(task.log_q) == 2


def test_task_can_be_picked():
    builder = TaskBuilder(SimpleTaskBuilder())
    builder.add_subtask(subtask=SimpleSubtask())

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
            assert future.result() == "got it"


def test_adapter(simple_task_builder):
    simple_task_builder.add_subtask(SimpleSubtask())
    new_task = simple_task_builder.build_task()

    with worker.ToolJobManager() as manager:
        for subtask in new_task.subtasks:
            settings = {}
            # adapter =
            # new_job = adapter.job
            # settings = adapter.settings
            adapted_tool = forseti.tasks.TaskJobAdapter(subtask)
            manager.add_job(adapted_tool, settings)
        manager.start()
        results = list(manager.get_results())

        assert len(results) == 2
        for result in results:
            assert result == "got it"

