import logging
import os
import shutil
import time
import typing
import concurrent.futures
from unittest.mock import Mock

import pytest

from speedwagon import config
import speedwagon
from speedwagon.tasks import system

class SimpleSubtask(speedwagon.tasks.Subtask):

    def __init__(self, message):
        super().__init__()
        self.message = message

    def work(self) -> bool:
        self.log("processing")
        print("processing {}".format(self.message))
        time.sleep(.01)
        self.set_results(self.message)
        print("finished with {}".format(self.message))
        return True

    @property
    def settings(self):
        return {"message": self.message}


class SimplePreTask(speedwagon.tasks.Subtask):

    def __init__(self, message):
        super().__init__()
        self.message = message

    def work(self) -> bool:
        self.log("Setting up")
        self.set_results(self.message)
        return True

    @property
    def settings(self):
        return {"r": "ad"}


class SimpleMultistage(speedwagon.tasks.tasks.MultiStageTask):
    def process_subtask_results(self,
                                subtask_results: typing.List[typing.Any])\
            -> typing.Any:

        return "\n".join(subtask_results)


class SimpleTaskBuilder(speedwagon.tasks.tasks.BaseTaskBuilder):

    @property
    def task(self) -> SimpleMultistage:
        return SimpleMultistage()


@pytest.fixture
def simple_task_builder(tmpdir_factory):
    temp_path = os.path.join(tmpdir_factory.getbasetemp(), "test")
    os.makedirs(temp_path)
    builder = speedwagon.tasks.TaskBuilder(SimpleTaskBuilder(), str(temp_path))
    builder.add_subtask(subtask=SimpleSubtask("got it"))
    yield builder
    shutil.rmtree(temp_path)


def test_task_builder(simple_task_builder):
    task = simple_task_builder.build_task()

    assert isinstance(task, speedwagon.tasks.tasks.MultiStageTask)

    assert len(task.main_subtasks) == 1

    assert isinstance(task.main_subtasks[0], SimpleSubtask)

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


def test_task_can_be_picked(tmpdir):
    temp_path = tmpdir.mkdir("test")
    builder = speedwagon.tasks.TaskBuilder(SimpleTaskBuilder(), temp_path)
    builder.add_subtask(subtask=SimpleSubtask(message="got it"))

    task_original = builder.build_task()
    serialized = speedwagon.tasks.TaskBuilder.save(task_original)

    task_unserialized = speedwagon.tasks.TaskBuilder.load(serialized)
    assert task_original.name == task_unserialized.name

    shutil.rmtree(tmpdir)
    shortcut = os.path.join(tmpdir.dirname, "test_task_can_be_pickedcurrent")
    if os.path.exists(shortcut):
        os.unlink(shortcut)


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
def simple_task_builder_with_2_subtasks(tmpdir_factory):
    temp_path = tmpdir_factory.mktemp("task_builder")
    builder = speedwagon.tasks.TaskBuilder(SimpleTaskBuilder(), temp_path)
    builder.add_subtask(subtask=SimpleSubtask("First"))
    builder.add_subtask(subtask=SimpleSubtask("Second"))
    yield builder
    shutil.rmtree(temp_path)

    shortcut = \
        os.path.join(tmpdir_factory.getbasetemp(), "task_buildercurrent")

    if os.path.exists(shortcut):
        os.unlink(shortcut)


# @pytest.mark.adapter
# @pytest.mark.filterwarnings(
#     "ignore::DeprecationWarning")
# def test_adapter_results(simple_task_builder_with_2_subtasks):
#     new_task = simple_task_builder_with_2_subtasks.build_task()
#     with speedwagon.worker.ToolJobManager() as manager:
#         for subtask in new_task.main_subtasks:
#             adapted_tool = speedwagon.worker.SubtaskJobAdapter(subtask)
#             manager.add_job(adapted_tool, adapted_tool.settings)
#         manager.start()
#         results = list()
#         for r in manager.get_results():
#             results.append(r.data)
#
#         assert len(results) == 2
#         assert "First" == results[0]
#         assert "Second" == results[1]
#

class LogCatcher(logging.Handler):

    def __init__(self, storage: list, level=logging.NOTSET):
        super().__init__(level)
        self.storage = storage

    def emit(self, record):
        self.storage.append(record)


# @pytest.mark.adapter
# @pytest.mark.filterwarnings(
#     "ignore::DeprecationWarning")
# def test_adapter_logs(simple_task_builder_with_2_subtasks):
#     # worker = pytest.importorskip("speedwagon.frontend.qtwidgets.worker")
#     logs = []
#     log_catcher = LogCatcher(logs)
#     new_task = simple_task_builder_with_2_subtasks.build_task()
#
#     with speedwagon.worker.ToolJobManager() as manager:
#         manager.logger.setLevel(logging.INFO)
#         manager.logger.addHandler(log_catcher)
#
#         for subtask in new_task.main_subtasks:
#             adapted_tool = speedwagon.worker.SubtaskJobAdapter(subtask)
#             manager.add_job(adapted_tool, adapted_tool.settings)
#         manager.start()
#
#         list(manager.get_results())
#
#     assert len(logs) == 2
#     assert logs[0].message == "processing"
#     assert logs[1].message == "processing"


def test_pretask_builder(tmpdir):

    temp_path = tmpdir.mkdir("test")

    pretask = SimplePreTask("Starting")

    builder = speedwagon.tasks.TaskBuilder(SimpleTaskBuilder(), temp_path)
    builder.set_pretask(subtask=pretask)
    builder.add_subtask(subtask=SimpleSubtask("First"))
    builder.add_subtask(subtask=SimpleSubtask("Second"))
    task = builder.build_task()
    assert task.pretask == pretask
    shutil.rmtree(tmpdir)
    shortcut = os.path.join(tmpdir.dirname, "test_pretask_buildercurrent")
    if os.path.exists(shortcut):
        os.unlink(shortcut)


def test_posttask_builder(tmpdir):

    temp_path = tmpdir.mkdir("test")

    posttask = SimpleSubtask("ending")

    builder = speedwagon.tasks.TaskBuilder(SimpleTaskBuilder(), temp_path)
    builder.add_subtask(subtask=SimpleSubtask("First"))
    builder.add_subtask(subtask=SimpleSubtask("Second"))
    builder.set_posttask(posttask)
    task = builder.build_task()
    assert task.posttask == posttask
    shutil.rmtree(tmpdir)
    shortcut = os.path.join(tmpdir.dirname, "test_posttask_buildercurrent")
    if os.path.exists(shortcut):
        os.unlink(shortcut)

class TestAbsSystemTask:

    @pytest.fixture
    def spam_task(self):
        class SpamTask(system.AbsSystemTask):
            def description(self):
                return "Spam"
            def run(self) -> None:
                pass

        return SpamTask()
    def test_system_task_has_config(self, spam_task):

        spam_task.set_config_backend(
            Mock(
                name="mockConfig",
                spec_set=config.AbsConfigSettings,
                application_settings=Mock(return_value={"bacon": "eggs"})
            )
        )
        assert spam_task.config["bacon"] == "eggs"

    def test_config_none(self, spam_task):
        # Note: set_config_backend has not been set
        assert spam_task.config is None

    def test_call(self, spam_task):
        config = Mock()
        config_file_locator = Mock()
        spam_task.run = Mock()
        spam_task(config, config_file_locator)
        spam_task.run.assert_called_once()


class TestSubtask:
    def test_status_default_to_idle(self):
        task = speedwagon.tasks.Subtask()
        assert task.status == speedwagon.tasks.tasks.TaskStatus.IDLE

    def test_task_results_default_to_none(self):
        task = speedwagon.tasks.Subtask()
        assert task.task_result is None
#
    def test_results_default_to_none(self):
        task = speedwagon.tasks.Subtask()
        assert task.results is None

    def test_work_raises(self):
        # you are supposed to implement this so trying to call it will raise an
        #  exception. Let's test for that!
        task = speedwagon.tasks.Subtask()
        with pytest.raises(NotImplementedError):
            task.work()
#
    @pytest.mark.parametrize(
        "return_value, expected_status",
        [
            (False, speedwagon.tasks.tasks.TaskStatus.FAILED),
            (True, speedwagon.tasks.tasks.TaskStatus.SUCCESS),
        ]
    )
    def test_exec_status(self, return_value, expected_status):
        class MyTask(speedwagon.tasks.Subtask):
            def work(self) -> bool:
                return return_value
        task = MyTask()
        task.exec()
        assert task.status == expected_status

    def test_exec_throws_speedwagon_exceptions_failed(self):
        class MyTask(speedwagon.tasks.Subtask):
            def work(self) -> bool:
                raise speedwagon.exceptions.SpeedwagonException("let's go")
        task = MyTask()
        with pytest.raises(speedwagon.exceptions.SpeedwagonException):
            task.exec()
        assert task.status == speedwagon.tasks.tasks.TaskStatus.FAILED
#
# @pytest.mark.adapter
# # @pytest.mark.filterwarnings("ignore::DeprecationWarning")
# def test_adapter_results_with_pretask(tmpdir):
#     temp_path = tmpdir.mkdir("test")
#     pretask = SimplePreTask("Starting")
#
#     builder = speedwagon.tasks.TaskBuilder(SimpleTaskBuilder(), temp_path)
#     builder.set_pretask(subtask=pretask)
#     builder.add_subtask(subtask=SimpleSubtask("First"))
#     builder.add_subtask(subtask=SimpleSubtask("Second"))
#     new_task = builder.build_task()
#
#     with speedwagon.worker.ToolJobManager() as manager:
#         for subtask in new_task.subtasks:
#             adapted_tool = speedwagon.worker.SubtaskJobAdapter(subtask)
#             manager.add_job(adapted_tool, adapted_tool.settings)
#         manager.start()
#         results = list()
#         for r in manager.get_results():
#             results.append(r.data)
#
#         assert len(results) == 3
#         assert "Starting" == results[0]
#         assert "First" == results[1]
#         assert "Second" == results[2]
#     shutil.rmtree(tmpdir)
#
#     shortcut = \
#         os.path.join(tmpdir.dirname, "test_adapter_results_with_pretcurrent")
#
#     if os.path.exists(shortcut):
#         os.unlink(shortcut)
#

# @pytest.mark.slow
# @pytest.mark.adapter
# # @pytest.mark.filterwarnings(
# #     "ignore::DeprecationWarning")
# def test_adapter_results_with_posttask(tmpdir):
#     from speedwagon.worker import ToolJobManager
#     temp_path = tmpdir.mkdir("test")
#     post_task = SimpleSubtask("Ending")
#
#     builder = speedwagon.tasks.TaskBuilder(SimpleTaskBuilder(), temp_path)
#     builder.set_posttask(subtask=post_task)
#     builder.add_subtask(subtask=SimpleSubtask("First"))
#     builder.add_subtask(subtask=SimpleSubtask("Second"))
#     new_task = builder.build_task()
#
#     queued_order = []
#
#     with ToolJobManager() as manager:
#         for subtask in new_task.subtasks:
#             adapted_tool = speedwagon.worker.SubtaskJobAdapter(subtask)
#             manager.add_job(adapted_tool, adapted_tool.settings)
#
#         for message in manager._job_runtime._pending_jobs.queue:
#             print(message)
#             queued_order.append(message.args['message'])
#
#         manager.start()
#
#         # Fuzz this
#         time.sleep(1)
#
#         results = list()
#
#         for r in manager.get_results():
#             results.append(r.data)
#
#         assert len(results) == 3
#
#         assert "First" == results[0], "results = {}, queued_order={}".format(
#             results, queued_order)
#
#         assert "Second" == results[1]
#         assert "Ending" == results[2]
#
#     shutil.rmtree(tmpdir)
#
#     shortcut = \
#         os.path.join(tmpdir.dirname, "test_adapter_results_with_postcurrent")
#
#     if os.path.exists(shortcut):
#         os.unlink(shortcut)
