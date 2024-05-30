"""Pluggy style hook for defining plugins."""

from __future__ import annotations
from typing import Dict, Type, TYPE_CHECKING, List
import pluggy
if TYPE_CHECKING:
    from speedwagon import Workflow
    from speedwagon.tasks.system import AbsSystemTask

hookspec = pluggy.HookspecMarker("speedwagon")

# mypy: disable-error-code="empty-body"


@hookspec
def registered_workflows() -> Dict[str, Type[Workflow]]:
    """Get workflows registered to this plugin."""


@hookspec
def registered_initialization_tasks() -> List[AbsSystemTask]:
    """Get initializing tasks registered to this plugin."""
