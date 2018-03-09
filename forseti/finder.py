import abc
import importlib
import inspect
import os
import sys
import typing

from forseti.tools import AbsTool


class AbsDynamicFinder(metaclass=abc.ABCMeta):

    def __init__(self, path) -> None:
        self.path = path

    @staticmethod
    @abc.abstractmethod
    def py_module_filter(item: os.DirEntry) -> bool:
        pass

    def locate(self) -> dict:
        located_class = dict()
        tree = os.scandir(self.path)

        for m in filter(self.py_module_filter, tree):
            for name, module in self.load(m.name):
                located_class[name] = module
        return located_class

    @property
    @abc.abstractmethod
    def base_class(self):
        pass

    def load(self, module_file) -> typing.Iterable[typing.Tuple[str, typing.Any]]:

        try:
            module = importlib.import_module("{}.{}".format(self.package_name, os.path.splitext(module_file)[0]))
            members = inspect.getmembers(module, lambda m: inspect.isclass(m) and not inspect.isabstract(m))

            for name_, module_class in members:
                if issubclass(module_class, self.base_class) and module_class.active:
                    yield module_class.name, module_class

        except ImportError as e:
            print("Unable to load {}. Reason: {}".format(module_file, e), file=sys.stderr)

    @property
    @abc.abstractmethod
    def package_name(self) -> str:
        pass