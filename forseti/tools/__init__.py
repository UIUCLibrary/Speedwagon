from .make_checksum import MakeChecksumBatch
from .zip_packages import ZipPackages
from .verify_checksum import VerifyChecksumBatch
from .completeness import HathiPackageCompleteness
# from .spam import Spam
# from .eggs import Eggs
# __all__ = []
# from .abstool import AbsTool
# import pkgutil
# import inspect
# for loader, name, is_pkg in pkgutil.walk_packages(__path__):
#     if not is_pkg:
#         module_ = loader.find_module(name)
#         module = module_.load_module(name)
#         print(module)
#         print(loader)
#         for name_, module_class in inspect.getmembers(module, lambda m: inspect.isclass(m) and not inspect.isabstract(m)):
#
#             print(name_)
#
