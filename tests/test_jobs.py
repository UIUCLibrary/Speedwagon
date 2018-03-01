import io
import queue
import time
import typing
import concurrent.futures
import pytest
import pickle
import forseti.tasks
from forseti import TaskBuilder


class SimpleSubtask(forseti.tasks.Subtask):

    def work(self) -> bool:
        self.log("processing")
        time.sleep(1)
        self.result = "got it"
        return True


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

# def test_dummy():
# with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executer:
#     future = executer.submit(print, "hello")

#
# def test_task_as_concurrent_future(simple_task_builder):
#     task = simple_task_builder.build_task()
#     # tasks.append(task)
#     futures = []
#
#     with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executer:
#         futures.append(executer.submit(task.exec))
#         for future in concurrent.futures.as_completed(futures):
#             print(future.result())
#         # concurrent.futures.wait([results])
#         # print(results)
#         # for result in results:
#         #     print(result)
