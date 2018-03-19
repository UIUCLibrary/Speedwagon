import os
from PyQt5 import QtCore
import forseti.finder
from forseti.job import AbsWorkflow


class WorkflowFinder(forseti.finder.AbsDynamicFinder):

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
    Locate all workflow class found in workflows subpackage with the workflow prefix

    Returns: Dictionary of all workflow

    """

    root = os.path.join(os.path.dirname(__file__), "workflows")
    finder = WorkflowFinder(root)
    return finder.locate()
