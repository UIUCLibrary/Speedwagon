"""Tasks related to doing something with files on a file system."""

import abc
import logging
import os
import warnings
from typing import Optional

import speedwagon.tasks.tasks
logger = logging.getLogger(__name__)
__all__ = ["delete_file", "delete_directory"]


class DeleteFileSystemItem(speedwagon.tasks.Subtask[str]):
    """Base class for removing an item from a file system."""

    def __init__(self, path: str) -> None:
        """Create a new task for removing an item from the file system.

        Args:
            path: path to file or directory.
        """
        super().__init__()
        self.path = path

    @abc.abstractmethod
    def remove(self) -> None:
        """Remove the item."""

    def work(self) -> bool:
        """Run the task."""
        self.log(f"Removing {self.path}")
        self.remove()
        self.set_results(self.path)
        return True


class DeleteFile(DeleteFileSystemItem):
    """Remove a file from the file system."""

    def __init__(self, path: str) -> None:
        warnings.warn(
            "use delete_file instead",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(path)

    def task_description(self) -> Optional[str]:
        """Explain what os being removed."""
        return "Deleting file"

    def remove(self) -> None:
        """Remove the file in the path attribute."""
        os.remove(self.path)

    def work(self) -> bool:
        """Run the task."""
        self.log(f"Deleting {self.path}")
        self.remove()
        self.set_results(self.path)
        return True


class DeleteDirectory(DeleteFileSystemItem):
    """Remove a directory from the file system."""

    def __init__(self, path: str) -> None:
        warnings.warn(
            "use delete_directory instead",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(path)

    def remove(self) -> None:
        """Remove item in path attribute."""
        os.rmdir(self.path)

    def task_description(self) -> Optional[str]:
        """Explain what os being removed."""
        return "Removing directory"


@speedwagon.tasks.workflow_task(description='Removing directory')
def delete_directory(path: str, verbosity: int = logging.WARN) -> str:
    """Create a task to remove a directory.

    Args:
        path: path to directory to remove.
        verbosity: Log verbosity level.
    """
    func_logger = logger.getChild('delete_directory')
    func_logger.setLevel(verbosity)
    func_logger.debug(f"Deleting {path}")
    os.rmdir(path)
    func_logger.info(f"Deleted {path}")
    return path


@speedwagon.tasks.workflow_task(description='Removing file')
def delete_file(path: str, verbosity: int = logging.WARN) -> str:
    """Create a task to remove a file .

    Args:
        path: path to file to remove.
        verbosity: Log verbosity level.
    """
    func_logger = logger.getChild('delete_file')
    func_logger.setLevel(verbosity)
    func_logger.debug(f"Deleting {path}")
    os.remove(path)
    func_logger.info(f"Deleted {path}")
    return path
