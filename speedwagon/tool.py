import abc
import os
from typing import Type, List

from speedwagon import worker
from speedwagon import job
from speedwagon.job import AbsDynamicFinder
from speedwagon.workflows.shared_custom_widgets import UserOption2


class AbsTool(job.AbsJob):

    @staticmethod
    @abc.abstractmethod
    def new_job() -> Type[worker.ProcessJobWorker]:
        pass

    @staticmethod
    def discover_jobs(**user_args) -> List[dict]:
        pass

    @staticmethod
    @abc.abstractmethod
    def get_user_options() -> List[UserOption2]:
        pass

    @staticmethod
    def post_process(user_args: dict):
        pass

    @staticmethod
    def on_completion(*args, **kwargs):
        pass

    def user_options(self):
        return self.get_user_options()

    def discover_task_metadata(self, **user_args) -> List[dict]:
        return self.discover_jobs(**user_args)

    @staticmethod
    def generate_report(results, user_args):
        return None


class ToolFinder(AbsDynamicFinder):

    @staticmethod
    def py_module_filter(item: os.DirEntry):
        if not str(item.name).startswith("tool_"):
            return False
        return True

    @property
    def package_name(self) -> str:
        return "{}.tools".format(__package__)

    @property
    def base_class(self):
        return AbsTool
