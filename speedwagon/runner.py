"""Job runners."""

import abc
import logging
import speedwagon


class AbsRunner2(metaclass=abc.ABCMeta):
    """Abstract class for creating runners."""

    @abc.abstractmethod
    def run(self, job: speedwagon.job.AbsWorkflow,
            options: dict,
            logger: logging.Logger, completion_callback=None) -> None:
        """Run the workflow."""
