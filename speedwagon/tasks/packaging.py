"""Tasks related to file packages.

Created on 9/8/2021 by Henry Borchers

"""

import abc
from typing import Optional
import speedwagon


class AbsFindPackageTask(speedwagon.tasks.Subtask, abc.ABC):
    """Base class for creating find package tasks.

    To implement, override the find_packages method.
    """

    name = "Locating Packages"

    def __init__(self, root: str) -> None:
        """Create a new find package tasks that searches at a given location.

        Args:
            root: Path to search for packages
        """
        super().__init__()
        self._root = root

    def task_description(self) -> Optional[str]:
        """Describe where the packages are being searched for."""
        return f"Locating packages in {self._root}"

    def work(self) -> bool:
        """Perform the task."""
        self.log(f"Locating packages in {self._root}")
        self.set_results(self.find_packages(self._root))
        return True

    @abc.abstractmethod
    def find_packages(self, search_path: str):
        """Locate package type.

        Args:
            search_path:

        Returns:
            Returns packages located.
        """
