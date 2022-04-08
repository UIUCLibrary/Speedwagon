import abc
import logging
import speedwagon


class AbsRunner2(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def run(self, job: speedwagon.job.AbsWorkflow,
            options: dict,
            logger: logging.Logger, completion_callback=None) -> None:
        pass
