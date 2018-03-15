import abc
import typing

from . import options
import forseti.worker
from forseti.job import AbsJob


class AbsTool(AbsJob):

    @staticmethod
    @abc.abstractmethod
    def new_job() -> typing.Type["forseti.worker.ProcessJobWorker"]:
        pass

    @staticmethod
    def discover_jobs(**user_args) -> typing.List[dict]:
        pass

    @staticmethod
    @abc.abstractmethod
    def get_user_options() -> typing.List[options.UserOption2]:
        pass

    @staticmethod
    def post_process(user_args: dict):
        pass

    @staticmethod
    def on_completion(*args, **kwargs):
        pass

    def user_options(self):
        return self.get_user_options()

    def discover_task_metadata(self, **user_args) -> typing.List[dict]:
        return self.discover_jobs(**user_args)
