import abc
from typing import Optional
import speedwagon


class AbsFindPackageTask(speedwagon.tasks.Subtask, abc.ABC):
    name = "Locating Packages"

    def __init__(self, root: str) -> None:
        super().__init__()
        self._root = root

    def task_description(self) -> Optional[str]:
        return f"Locating packages in {self._root}"

    def work(self) -> bool:
        self.log("Locating packages in {}".format(self._root))
        self.set_results(self.find_packages(self._root))
        return True

    @abc.abstractmethod
    def find_packages(self, search_path: str):
        """Locate package type.

        Args:
            search_path:

        Returns:
        """
