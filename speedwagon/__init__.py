# University of Illinois/NCSA Open Source License Copyright (c) 2018,
# University of Illinois at Urbana-Champaign. All rights reserved.
#
#  Developed by:
#  University of Illinois Library at Urbana-Champaign
#  University of Illinois at Urbana-Champaign
#
#  http://www.library.illinois.edu/
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal with the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimers.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimers in the documentation
# and/or other materials provided with the distribution.
#
# Neither the names of University of Illinois Library at Urbana-Champaign,
# University of Illinois at Urbana-Champaign, nor the names of its
# contributors may be used to endorse or promote products derived from this
# Software without specific prior written permission.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# CONTRIBUTORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS WITH THE SOFTWARE.
#




import pkg_resources
import setuptools.config
import os
import sys

from .job import Workflow, JobCancelled
from . import tasks


def get_project_metadata(config_file):
    return setuptools.config.read_configuration(config_file)["metadata"]


def get_project_distribution() -> pkg_resources.Distribution:
    return pkg_resources.get_distribution(f"{__name__}")


def get_version():
    try:
        package_distribution = get_project_distribution()
        pkg_resources.require(f"{__name__}")
        version = package_distribution.version

    except pkg_resources.DistributionNotFound as e:

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
    except FileNotFoundError as e:
        version = "Unknown"
    return version


__version__ = get_version()

__all__ = [
    "Workflow",
    "JobCancelled",
    "tasks"
]
