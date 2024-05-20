"""Tasks related to doing something with files on a file system."""

import abc
import os
from typing import Optional

import speedwagon


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

    def remove(self) -> None:
        """Remove item in path attribute."""
        os.rmdir(self.path)

    def task_description(self) -> Optional[str]:
        """Explain what os being removed."""
        return "Removing directory"
