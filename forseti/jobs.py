import abc
from .worker import AbsJob2, AbsTask


class AbsJobBuilder(metaclass=abc.ABCMeta):

    def __init__(self):
        self._tasks = []
        self.logger = None

    @property
    @abc.abstractmethod
    def job(self) -> AbsJob2:
        pass

    def add_task(self, task: AbsTask):
        self._tasks.append(task)

    def build_job(self) -> AbsJob2:
        job = self.job
        for task in self._tasks:
            job.tasks.append(task)

        # TODO: If a logger is configured, assign the logger
        if self.logger is not None:
            pass

        return job


class JobBuilder:
    # The director
    def __init__(self, builder: AbsJobBuilder) -> None:
        self._builder = builder
        self._logger = None

    def build_job(self) -> AbsJob2:
        job = self._builder.build_job()
        return job

    def set_logger(self, logger):
        self._builder.logger = logger

    def add_task(self, task):
        self._builder.add_task(task)
