import abc
import os
from typing import Optional

import speedwagon


class DeleteFileSystemItem(speedwagon.tasks.Subtask, abc.ABC):

    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path

    @abc.abstractmethod
    def remove(self) -> None:
        """Remove the item."""

    def work(self) -> bool:
        self.log(f"Removing {self.path}")
        self.remove()
        self.set_results(self.path)
        return True


class DeleteFile(DeleteFileSystemItem):

    def task_description(self) -> Optional[str]:
        return "Deleting file"

    def remove(self) -> None:
        os.remove(self.path)

    def work(self) -> bool:
        self.log(f"Deleting {self.path}")
        self.remove()
        self.set_results(self.path)
        return True


class DeleteDirectory(DeleteFileSystemItem):

    def remove(self) -> None:
        os.rmdir(self.path)

    def task_description(self) -> Optional[str]:
        return "Removing directory"
