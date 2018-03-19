import abc
import typing
import forseti.tasks

class AbsJob(metaclass=abc.ABCMeta):
    active = True
    description: str = None
    name: str = None

    def __init__(self):
        self.options = []  # type: ignore

    @abc.abstractmethod
    def user_options(self):
        pass

    @staticmethod
    def validate_user_options(**user_args):
        return True

    @abc.abstractmethod
    def discover_task_metadata(self, **user_args)->typing.List[dict]:
        pass

    def create_new_task(self, task_builder: "forseti.tasks.TaskBuilder", **job_args):
        pass

    # def setup_task(self, task_builder: "forseti.tasks.TaskBuilder"):
    #     pass
    #
    # def finalization_task(self, task_builder: "forseti.tasks.TaskBuilder"):
    #     pass

    # @classmethod
    # def generate_report(cls, *args, **kwargs):
    #     return None


class AbsTool(AbsJob):

    @staticmethod
    @abc.abstractmethod
    def new_job() -> typing.Type["forseti.worker.ProcessJobWorker"]:
        pass

    @staticmethod
    def discover_jobs(**user_args) -> typing.List[dict]:
        pass

    @staticmethod
    @abc.abstractmethod
    def get_user_options() -> typing.List["options.UserOption2"]:
        pass

    @staticmethod
    def post_process(user_args: dict):
        pass

    @staticmethod
    def on_completion(*args, **kwargs):
        pass

    def user_options(self):
        return self.get_user_options()

    def discover_task_metadata(self, **user_args) -> typing.List[dict]:
        return self.discover_jobs(**user_args)
