import abc
import importlib
import inspect
import logging
import os
import sys
import typing
from typing import Dict
from . import tasks
from . import worker
from .tools.options import UserOption2
from PyQt5 import QtWidgets


class JobCancelled(Exception):
    pass


class AbsJob(metaclass=abc.ABCMeta):
    active = True
    description: typing.Optional[str] = None
    name: typing.Optional[str] = None

    def __init__(self):
        self.options = []  # type: ignore

    @abc.abstractmethod
    def user_options(self):
        pass

    @staticmethod
    def validate_user_options(**user_args):
        return True

    def create_new_task(self,
                        task_builder: tasks.TaskBuilder,
                        **job_args):
        pass


class AbsTool(AbsJob):

    @staticmethod
    @abc.abstractmethod
    def new_job() -> typing.Type[worker.ProcessJobWorker]:
        pass

    @staticmethod
    def discover_jobs(**user_args) -> typing.List[dict]:
        pass

    @staticmethod
    @abc.abstractmethod
    def get_user_options() -> typing.List[UserOption2]:
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

    @staticmethod
    def generate_report(results, user_args):
        return None


class AbsWorkflow(AbsJob):
    active = True
    description: typing.Optional[str] = None
    name: typing.Optional[str] = None

    def __init__(self) -> None:
        super().__init__()
        self.global_settings: Dict[str, str] = dict()

    @abc.abstractmethod
    def discover_task_metadata(self, initial_results: typing.List[typing.Any],
                               additional_data, **user_args) \
            -> typing.List[dict]:
        pass

    def completion_task(
            self,
            task_builder: tasks.TaskBuilder,
            results,
            **user_args
    ) -> None:
        pass

    def initial_task(self, task_builder: tasks.TaskBuilder,
                     **user_args) -> None:
        pass

    @classmethod
    def generate_report(cls, results: typing.List[tasks.Result],
                        **user_args) -> typing.Optional[str]:
        pass

    # @abc.abstractmethod
    # def user_options(self):
    #     return {}


class Workflow(AbsWorkflow):

    def get_additional_info(self, parent: QtWidgets.QWidget,
                            options: dict, pretask_results: list) -> dict:
        """If a user needs to be prompted for more information, run this

        Args:
            parent: QtWidget to build off of
            options:  Dictionary of existing user settings
            pretask_results: results of the pretask, if any

        Returns: Any additional configurations that needs to be added to a job

        """
        return dict()


class AbsDynamicFinder(metaclass=abc.ABCMeta):

    def __init__(self, path) -> None:
        self.path = path
        self.logger = logging.getLogger(__name__)

    @staticmethod
    @abc.abstractmethod
    def py_module_filter(item: os.DirEntry) -> bool:
        pass

    def locate(self) -> typing.Dict["str", AbsJob]:
        located_class = dict()
        tree = os.scandir(self.path)

        for m in filter(self.py_module_filter, tree):
            for name, module in self.load(m.name):
                located_class[name] = module
        return located_class

    @property
    @abc.abstractmethod
    def base_class(self) -> typing.Type[AbsJob]:
        pass

    def load(self, module_file) -> \
            typing.Iterable[typing.Tuple[str, typing.Any]]:

        def class_member_filter(item):
            return inspect.isclass(item) and not inspect.isabstract(item)

        try:
            module = importlib.import_module(
                "{}.{}".format(self.package_name,
                               os.path.splitext(module_file)[0])
            )
            members = inspect.getmembers(module, class_member_filter)

            for name_, module_class in members:

                if issubclass(module_class, self.base_class) \
                        and module_class.active:
                    yield module_class.name, module_class

        except ImportError as e:
            msg = "Unable to load {}. Reason: {}".format(module_file, e)
            print(msg, file=sys.stderr)
            self.logger.warning(msg)

    @property
    @abc.abstractmethod
    def package_name(self) -> str:
        pass


class AbsToolData(metaclass=abc.ABCMeta):

    def __init__(self, parent=None):
        self._parent = parent
        self.label = ""
        self.widget = self.get_widget()

    @abc.abstractmethod
    def get_widget(self):
        pass

    @property
    def data(self):
        return self.widget.value


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


def available_tools() -> dict:
    """
    Locate all tools that can be loaded

    Returns: Dictionary of all tools

    """
    root = os.path.join(os.path.dirname(__file__), "tools")
    finder = ToolFinder(root)
    return finder.locate()


class WorkflowFinder(AbsDynamicFinder):

    @staticmethod
    def py_module_filter(item: os.DirEntry) -> bool:
        if not str(item.name).startswith("workflow_"):
            return False
        return True

    @property
    def package_name(self) -> str:
        return "{}.workflows".format(__package__)

    @property
    def base_class(self):
        return AbsWorkflow


def available_workflows() -> dict:
    """
    Locate all workflow class found in workflows subpackage with the workflow
    prefix

    Returns: Dictionary of all workflow

    """

    root = os.path.join(os.path.dirname(__file__), "workflows")
    finder = WorkflowFinder(root)
    return finder.locate()
