import pkg_resources
import setuptools.config

from .job import Workflow, JobCancelled, available_workflows
from .tasks import Subtask
from . import tasks


def get_project_metadata(config_file):
    return setuptools.config.read_configuration(config_file)["metadata"]


def get_project_distribution() -> pkg_resources.Distribution:
    """

    Returns:

    """
    return pkg_resources.get_distribution(f"{__name__}")


__all__ = [
    "Workflow",
    "Subtask",
    "available_workflows",
    "JobCancelled",
    "tasks"
]
