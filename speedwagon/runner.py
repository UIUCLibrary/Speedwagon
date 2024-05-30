"""Job runners."""
from __future__ import annotations
import abc
import typing

if typing.TYPE_CHECKING:
    import logging
    from speedwagon.job import AbsWorkflow


class AbsRunner2(metaclass=abc.ABCMeta):
    """Abstract class for creating runners."""

    @abc.abstractmethod
    def run(
        self,
        job: AbsWorkflow,
        options: typing.Mapping[str, object],
        logger: logging.Logger,
        completion_callback=None,
    ) -> None:
        """Run the workflow."""
