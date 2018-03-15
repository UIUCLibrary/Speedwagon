import abc
import typing

import forseti.worker
import forseti.tasks
from forseti.job import AbsJob


class AbsWorkflow(AbsJob):
    active = True
    description: str = None
    name: str = None

    def __init__(self) -> None:
        super().__init__()

    @abc.abstractmethod
    def discover_task_metadata(self, **user_args) -> typing.List[dict]:
        pass

    def completion_task(self, task_builder: forseti.tasks.TaskBuilder, results, **user_args) -> None:
        pass

    def initial_task(self, task_builder: forseti.tasks.TaskBuilder, **user_args) -> None:
        pass

    @classmethod
    def generate_report(cls, results: typing.List[forseti.tasks.Result], **user_args) -> typing.Optional[str]:
        pass

    # @abc.abstractmethod
    # def user_options(self):
    #     return {}
