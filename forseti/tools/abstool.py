import abc
import typing

from . import options
import forseti.worker


class AbsTool(metaclass=abc.ABCMeta):
    name = None  # type: str
    description = None  # type: str
    active = True  # type: bool

    def __init__(self) -> None:
        super().__init__()
        self.options = []  # type: ignore

    @staticmethod
    @abc.abstractmethod
    def new_job() ->typing.Type["forseti.worker.ProcessJob"]:
        pass


    @staticmethod
    @abc.abstractmethod
    def discover_jobs(**user_args)->typing.List[dict]:
        pass


    @staticmethod
    @abc.abstractmethod
    def get_user_options() -> typing.List[options.UserOption2]:
        pass

    @staticmethod
    def validate_args(**user_args):
        return True

    @staticmethod
    def post_process(user_args:dict):
        pass

    @staticmethod
    def on_completion(*args, **kwargs):
        pass

    # @staticmethod
    @classmethod
    def generate_report(cls, *args, **kwargs):
        return None


