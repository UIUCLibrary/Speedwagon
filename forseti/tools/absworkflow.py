import abc
import typing

import forseti.worker


class AbsWorkflow(metaclass=abc.ABCMeta):
    name = None
    description = None
    active = True

    def __init__(self) -> None:
        super().__init__()
        self.options = []  # type: ignore

    @abc.abstractmethod
    def create_new_job(self, **job_args) -> forseti.worker.AbsJob2:
        pass


    @abc.abstractmethod
    def discover_jobs(self, **user_args)->typing.List[dict]:
        pass