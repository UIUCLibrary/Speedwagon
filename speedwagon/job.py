"""Define how various jobs are described."""
from __future__ import annotations

import abc
import importlib.util
import inspect
import json
import logging
import os
import sys
import typing
from typing import (
    Any, Dict, Iterable, List, Optional, Set, Tuple, Type, Mapping, Sequence,
    TypeVar, Generic
)

import speedwagon.plugins
import speedwagon.workflows

if typing.TYPE_CHECKING:
    from speedwagon.workflow import AbsOutputOptionDataType
    from speedwagon.frontend.interaction import UserRequestFactory
    from speedwagon.tasks import TaskBuilder, Result
    from speedwagon.config import SettingsData, SettingsDataType
    from pluggy import PluginManager


__all__ = [
    "AbsWorkflow",
    "Workflow",
    "NullWorkflow",
    "available_workflows",
    "all_required_workflow_keys",
    "AbsJobConfigSerializationStrategy",
]

_T = TypeVar("_T", bound=Mapping[str, object])


class AbsWorkflow(Generic[_T], metaclass=abc.ABCMeta):
    """Base class for workflows."""

    active = True
    description: Optional[str] = None
    name: Optional[str] = None
    global_settings: SettingsData = {}
    required_settings_keys: Set[str] = set()

    # pylint: disable=unused-argument
    def __init__(self, *args, **kwargs) -> None:
        """Populate the base structure of a workflow class."""
        super().__init__()
        self.options = []  # type: ignore

    @abc.abstractmethod
    def discover_task_metadata(
        self,
        initial_results: List[Result],
        additional_data: Mapping[str, Any],
        user_args: _T,
    ) -> Sequence[Mapping[str, object]]:
        """Generate data or parameters needed for upcoming tasks.

        Generate data or parameters needed for task to complete based on
        the user's original configuration

        Return a list of dictionaries of types that can be serialized,
            preferably strings.

        """

    def completion_task(  # noqa: B027
        self,
        task_builder: TaskBuilder,
        results: List[Result],
        user_args: _T
    ) -> None:
        """Last task after Job is completed.

        By default, this method is a no-op unless overridden.
        """

    def initial_task(  # noqa: B027
        self,
        task_builder: TaskBuilder,
        user_args: _T
    ) -> None:
        """Create a task to run before the main tasks start.

        The initial task is run prior to the get_additional_info method.
        Results generated here will then be passed to get_additional_info.

        This is useful for locating additional information that will be
        needed by other tasks and the user needs to additional decisions
        before running the main tasks.

        In general, prefer :py:meth:`discover_task_metadata` if you don't
        need a user's interaction.

        By default, this method is a no-op unless overridden.
        """

    def create_new_task(  # noqa: B027
        self,
        task_builder: TaskBuilder,
        job_args
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

        By default, this method is a no-op unless overridden.
        """

    @classmethod  # noqa: B027
    def generate_report(
        cls, results: List[Result], user_args: _T
    ) -> Optional[str]:
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

        By default, this method is a no-op and returns None unless overridden.
        """

    # pylint: disable=unused-argument
    @staticmethod
    def validate_user_options(**user_args) -> bool:
        """Make sure that the options the user provided is valid.

        Notes:
            This raises a ValueError on Failure.
            This should be rewritten to be better.

        Args:
            **user_args: user arguments

        Returns:
            Returns True on valid else returns False.

        """
        return True


class Workflow(AbsWorkflow[_T]):  # pylint: disable=abstract-method
    """Base class for defining a new workflow item.

    Subclass this class to generate a new workflow.

    Notes:
        You need to implement the discover_task_metadata() method.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Create a new workflow object."""
        super().__init__(*args, **kwargs)
        self._options_backends = None

    def set_options_backend(self, value) -> None:
        """Set the option backend."""
        self._options_backends = value

    # pylint: disable=unused-argument
    def get_additional_info(
        self,
        user_request_factory: UserRequestFactory,
        options: _T,
        pretask_results: List[Result],
    ) -> Mapping[str, Any]:
        """Request additional information from the user.

        If a user needs to be prompted for more information, run this

        Args:
            user_request_factory: factory needed
            options:  Dictionary of existing user settings
            pretask_results: results of the pretask, if any

        Returns:
            Any additional configurations that needs to be added to a job

        """
        return {}

    # pylint: enable=unused-argument
    def job_options(self) -> List[AbsOutputOptionDataType]:
        """Get user options.

        Defaults to no args.
        """
        return []

    def workflow_options(self) -> List[AbsOutputOptionDataType]:
        """Get options configured at the application level.

        Defaults to no args.
        """
        return []

    def get_workflow_configuration_value(
        self, key: str
    ) -> Optional[SettingsDataType]:
        """Get a value from the workflow configuration."""
        if self._options_backends is None:
            return None
        return self._options_backends.get(key)


class NullWorkflow(Workflow):
    """Null Workflow.

    Does nothing.
    """

    name = ""
    description = ""

    def discover_task_metadata(
        self, initial_results: List[Any], additional_data, user_args: _T
    ) -> List[dict]:
        """Discover task metadata."""
        return []


class AbsDynamicFinder(metaclass=abc.ABCMeta):
    """Dyanmic finder base class."""

    def __init__(self, path: str) -> None:
        """Populate the base structure of a dynamic finder."""
        self.path = path
        self.logger = logging.getLogger(__name__)

    @staticmethod
    @abc.abstractmethod
    def py_module_filter(item: "os.DirEntry[str]") -> bool:
        pass

    def locate(self) -> Dict["str", Type[Workflow]]:
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

    def load(self, module_file: str) -> Iterable[Tuple[str, Any]]:
        """Load module file."""

        def class_member_filter(item: type) -> bool:
            return inspect.isclass(item) and not inspect.isabstract(item)

        try:
            module = importlib.import_module(
                f"{self.package_name}.{os.path.splitext(module_file)[0]}"
            )
            members = inspect.getmembers(module, class_member_filter)

            for _, module_class in members:
                if (
                    issubclass(module_class, self.base_class)
                    and module_class.active
                ):
                    yield module_class.name, module_class

        except ImportError as error:
            msg = f"Unable to load {module_file}. Reason: {error}"
            print(msg, file=sys.stderr)
            self.logger.warning(msg)

    @property
    @abc.abstractmethod
    def package_name(self) -> str:
        """Get he name of the python package."""


class WorkflowFinder(AbsDynamicFinder):
    @staticmethod
    def py_module_filter(item: "os.DirEntry[str]") -> bool:
        return bool(str(item.name).startswith("workflow_"))

    @property
    def package_name(self) -> str:
        return f"{__package__}.workflows"

    @property
    def base_class(self) -> Type[AbsWorkflow]:
        """Get base class."""
        return AbsWorkflow


class AbsWorkflowFinder(abc.ABC):  # pylint: disable=too-few-public-methods
    @abc.abstractmethod
    def locate(self) -> Dict[str, Type[Workflow]]:
        """Locate workflows from everywhere."""


class FindAllWorkflowsPluggyStrategy(AbsWorkflowFinder):

    def __init__(self, plugin_manager: Optional[PluginManager] = None) -> None:
        super().__init__()
        self.plugin_manager: PluginManager = \
            plugin_manager or self.get_plugin_manager()

    @staticmethod
    def get_plugin_manager():
        return speedwagon.plugins.get_plugin_manager(
            speedwagon.plugins.register_whitelisted_plugins
        )

    def locate(self) -> Dict[str, Type[Workflow]]:
        all_workflows: Dict[str, Type[Workflow]] = {}
        for plugin_workflows in \
                self.plugin_manager.hook.registered_workflows():
            all_workflows = {**all_workflows, **plugin_workflows}
        return all_workflows


def available_workflows(strategy: Optional[AbsWorkflowFinder] = None) -> dict:
    """Locate all workflow class in workflows subpackage.

    This looks for a workflow prefix in the naming.

    Returns:
        Dictionary of all workflow

    """
    strategy = strategy or FindAllWorkflowsPluggyStrategy()
    return strategy.locate()


def all_required_workflow_keys(
    workflows: Optional[Dict[str, Type[Workflow]]] = None
) -> Set[str]:
    """Get all the keys required by the workflows.

    Args:
        workflows: Optional value. If not explicitly set, it will pull for all
            workflows

    Returns:
        Set of Keys that workflows are expecting

    """
    workflows = workflows or find_builtin_workflows()
    keys: Set[str] = set()
    for speedwagon_workflow in workflows.values():
        keys = keys.union(set(speedwagon_workflow.required_settings_keys))
    return keys


class AbsJobConfigSerializationStrategy(abc.ABC):
    """Base class for serializing job configurations."""

    def __init__(self) -> None:
        """Create a new job serialization strategy."""
        self.file_name: typing.Optional[str] = None

    @abc.abstractmethod
    def save(self, workflow_name: str, data: Dict[str, Any]) -> None:
        """Save data to file."""

    @abc.abstractmethod
    def load(self) -> typing.Tuple[str, Dict[str, Any]]:
        """Load data from file and return."""


class JobConfigSerialization:
    def __init__(self, strategy: AbsJobConfigSerializationStrategy) -> None:
        super().__init__()
        self._strategy = strategy

    def save(self, workflow_name: str, data: Dict[str, Any]) -> None:
        self._strategy.save(workflow_name, data)

    def load(self) -> typing.Tuple[str, Dict[str, Any]]:
        return self._strategy.load()


class ConfigJSONSerialize(AbsJobConfigSerializationStrategy):
    def save(self, workflow_name: str, data: Dict[str, Any]) -> None:
        if self.file_name is None:
            raise AssertionError(
                "Required class attribute missing: file_name "
            )

        with open(self.file_name, "w", encoding="utf-8") as file_writer:
            file_writer.write(self.serialize_data(workflow_name, data))

    @staticmethod
    def serialize_data(name: str, data: Dict[str, Any]) -> str:
        return json.dumps({"Workflow": name, "Configuration": data}, indent=4)

    @staticmethod
    def deserialize_data(
        data: typing.Mapping[str, Any]
    ) -> typing.Tuple[str, Dict[str, Any]]:
        return data["Workflow"], data["Configuration"]

    def load(self) -> typing.Tuple[str, Dict[str, Any]]:
        if self.file_name is None:
            raise AssertionError(
                "Required class attribute missing: file_name "
            )

        with open(self.file_name, "r", encoding="utf-8") as file_reader:
            return self.deserialize_data(json.load(file_reader))


def find_builtin_workflows() -> Dict[str, Type[Workflow]]:
    """Locate all workflow class in workflows subpackage.

    This looks for a workflow prefix in the naming.

    Returns:
        Dictionary of all workflow

    """
    root = os.path.join(os.path.dirname(__file__), "workflows")
    finder = WorkflowFinder(root)
    return finder.locate()
