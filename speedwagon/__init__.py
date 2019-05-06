import pkg_resources
import setuptools.config
import os
import sys

from .job import Workflow, JobCancelled
from . import tasks


def get_project_metadata(config_file):
    return setuptools.config.read_configuration(config_file)["metadata"]


def get_project_distribution() -> pkg_resources.Distribution:
    """

    Returns:

    """
    return pkg_resources.get_distribution(f"{__name__}")


def get_version():
    try:
        package_distribution = get_project_distribution()
        pkg_resources.require(f"{__name__}")
        version = package_distribution.version

    except pkg_resources.DistributionNotFound:

        # =====================================================================
        # In the case of CX_FREEZE. As of version 5.1.1, it doesn't build
        # package metadata files. For this reason setup.cfg must be manually
        # included as part of the setup script, which it includes it to the
        # same path as the main exe.
        # =====================================================================
        setup_cfg = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "../", "setup.cfg"))
        if os.path.exists(setup_cfg):
            metadata = get_project_metadata(setup_cfg)
            if metadata["name"] == f"{__name__}":
                return metadata["version"]
        # =====================================================================

        print("No package metadata for this project located", file=sys.stderr)
        version = "Unknown"
    except FileNotFoundError:
        version = "Unknown"
    return version


__version__ = get_version()

__all__ = [
    "Workflow",
    "JobCancelled",
    "tasks"
]
