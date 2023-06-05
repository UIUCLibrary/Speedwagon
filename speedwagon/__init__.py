"""Speedwagon."""
import pluggy

from speedwagon import tasks, worker
from speedwagon import startup
from speedwagon.exceptions import JobCancelled
from speedwagon.runner_strategies import simple_api_run_workflow
from speedwagon.job import Workflow, available_workflows
from speedwagon import frontend, config

hookimpl = pluggy.HookimplMarker("speedwagon")

__all__ = [
    "Workflow",
    "available_workflows",
    "tasks",
    "startup",
    "simple_api_run_workflow",
    "worker",
    "JobCancelled",
    "frontend",
    'config',
    'hookimpl'
]
