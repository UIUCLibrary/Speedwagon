"""Define how various jobs are described."""

import abc
import importlib
import inspect
import logging
import os
import sys
from typing import Type, Optional, Iterable, Dict, List, Any, Tuple, Set

from PyQt5 import QtWidgets  # type: ignore
from . import tasks
__all__ = [
    "JobCancelled",
    "AbsWorkflow",
    "Workflow",
    "NullWorkflow",
    "available_workflows",
    "all_required_workflow_keys"
]


class JobCancelled(Exception):
    """Job cancelled exception."""

    def __init__(self, *args: object, expected=False) -> None:
        super().__init__(*args)
        self.expected = expected


class AbsWorkflow(metaclass=abc.ABCMeta):
    """Base class for workflows."""

    active = True
    description: Optional[str] = None
    name: Optional[str] = None
    global_settings: Dict[str, str] = dict()
    required_settings_keys: Set[str] = set()

    def __init__(self, *args, **kwargs) -> None:
        """Populate the base structure of a workflow class."""
        super().__init__()
        self.options = []  # type: ignore

    @abc.abstractmethod
    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data: Dict[str, Any],
                               **user_args) -> List[dict]:
        """Generate data or parameters needed for upcoming tasks.

        Generate data or parameters needed for task to complete based on
        the user's original configuration

        Return a list of dictionaries of types that can be serialized,
            preferably strings.

        """

    def completion_task(self, task_builder: tasks.TaskBuilder, results,
                        **user_args) -> None:
        """Last task after Job is completed."""

    def initial_task(self, task_builder: tasks.TaskBuilder,
                     **user_args) -> None:
        """Create a task to run before the main tasks start.

        The initial task is run prior to the get_additional_info method.
        Results generated here will then be passed to get_additional_info.

        This is useful for locating additional information that will be
        needed by other tasks and the user needs to additional decisions
        before running the main tasks.

        In general, prefer :py:meth:`discover_task_metadata` if you don't
        need a user's interaction.
        """

    def create_new_task(
            self,
            task_builder: tasks.TaskBuilder,
            **job_args
    ) -> None:
        """Add a new task to be accomplished when the workflow is started.

        Use the task_builder parameter's add_subtask method to include a
        :py:class:`speedwagon.Subtask()`

            Example:
                .. code-block::

                    title_page = job_args['title_page']
                    source = job_args['source_path']
                    package_id = job_args['package_id']

                    task_builder.add_subtask(
                        subtask=MakeYamlTask(package_id, source, title_page))

        """

    @classmethod
    def generate_report(cls, results: List[tasks.Result], **user_args) \
            -> Optional[str]:
        r"""Generate a text report for the results of the workflow.

        Example:
            .. code-block::

                report_lines = []

                for checksum_report, items_written in \\
                        cls.sort_results([i.data for \n
                        i in results]).items():

                    report_lines.append(
                        f"Checksum values for {len(items_written)} "
                        f"files written to {checksum_report}")

                return '\\n'.join(report_lines)

        """

    @staticmethod
    def validate_user_options(**user_args) -> bool:
        """Make sure that the options the user provided is valid.

        Notes:
            This raises a ValueError on Failure.
            This should be rewritten to be better.

        Args:
            **user_args:

        Returns:
            Returns True on valid else returns False.

        """
        return True


class Workflow(AbsWorkflow):  # pylint: disable=abstract-method
    """Base class for defining a new workflow item.

    Subclass this class to generate a new workflow.

    Notes:
        You need to implement the discover_task_metadata() method.
    """

    def get_additional_info(self, parent: QtWidgets.QWidget,
                            options: dict, pretask_results: list) -> dict:
        """Request additional information from the user.

        If a user needs to be prompted for more information, run this

        Args:
            parent: QtWidget to build off of
            options:  Dictionary of existing user settings
            pretask_results: results of the pretask, if any

        Returns:
            Any additional configurations that needs to be added to a job

        """
        return dict()


class NullWorkflow(Workflow):
    """Null Workflow.

    Does nothing.
    """

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        """Discover task metadata."""
        return []

    def user_options(self):
        """User options."""
        return []


class AbsDynamicFinder(metaclass=abc.ABCMeta):
    """Dyanmic finder base class."""

    def __init__(self, path) -> None:
        """Populate the base structure of a dynamic finder."""
        self.path = path
        self.logger = logging.getLogger(__name__)

    @staticmethod
    @abc.abstractmethod
    def py_module_filter(item: os.DirEntry) -> bool:
        pass

    def locate(self) -> Dict["str", AbsWorkflow]:
        """Locate workflows."""
        located_class = {}
        tree = os.scandir(self.path)

        for module_file in filter(self.py_module_filter, tree):
            for name, module in self.load(module_file.name):
                located_class[name] = module
        return located_class

    @property
    @abc.abstractmethod
    def base_class(self) -> Type[AbsWorkflow]:
        pass

    def load(self, module_file: str) -> \
            Iterable[Tuple[str, Any]]:
        """Load module file."""
        def class_member_filter(item) -> bool:
            return inspect.isclass(item) and not inspect.isabstract(item)

        try:
            module = importlib.import_module(
                "{}.{}".format(self.package_name,
                               os.path.splitext(module_file)[0])
            )
            members = inspect.getmembers(module, class_member_filter)

            for _, module_class in members:

                if issubclass(module_class, self.base_class) \
                        and module_class.active:
                    yield module_class.name, module_class

        except ImportError as error:
            msg = "Unable to load {}. Reason: {}".format(module_file, error)
            print(msg, file=sys.stderr)
            self.logger.warning(msg)

    @property
    @abc.abstractmethod
    def package_name(self) -> str:
        """Get he name of the python package."""


class WorkflowFinder(AbsDynamicFinder):

    @staticmethod
    def py_module_filter(item: os.DirEntry) -> bool:
        return bool(str(item.name).startswith("workflow_"))

    @property
    def package_name(self) -> str:
        return "{}.workflows".format(__package__)

    @property
    def base_class(self):
        """Get base class."""
        return AbsWorkflow


def available_workflows() -> dict:
    """Locate all workflow class in workflows subpackage.

    This looks for a workflow prefix in the naming.

    Returns:
        Dictionary of all workflow

    """
    root = os.path.join(os.path.dirname(__file__), "workflows")
    finder = WorkflowFinder(root)
    return finder.locate()


def all_required_workflow_keys(workflows=None) -> Set[str]:
    """Get all the keys required by the workflows.

    Args:
        workflows: Optional value. If not explicitly set, it will pull for all
            workflows

    Returns:
        Set of Keys that workflows are expecting

    """
    workflows = workflows or available_workflows()
    keys: Set[str] = set()
    for workflow in workflows.values():
        keys = keys.union(set(workflow.required_settings_keys))
    return keys
