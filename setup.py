import glob
import os

from setuptools import setup

import extra_commands

try:
    from pyqt_distutils.build_ui import build_ui
    cmdclass = {
        "build_ui": build_ui,
        "build_py": extra_commands.CustomBuildPy,
        "clean": extra_commands.Clean,
    }

except ImportError:
    cmdclass = {}

cmdclass['dl_tessdata'] = extra_commands.TesseractData


setup(
    test_suite="tests",
    install_requires=[
        "PyQt5",
        "HathiZip",
        "HathiValidate>=0.3.3",
        "pyhathiprep",
        "pyyaml",
        "hathichecksumupdater",
        "uiucprescon-getmarc",
        "uiucprescon-imagevalidate>=0.1.4",
        "uiucprescon-ocr>=0.0.1",
        "uiucprescon-packager[kdu]>=0.1.1",
        "pykdu-compress>=0.0.4",
        "setuptools>=30.3.0",
        "importlib_resources",
        'lxml',
        "py3exiv2bind>=0.1.3",
    ],
    packages=[
        "speedwagon",
        "speedwagon.dialog",
        "speedwagon.tools",
        "speedwagon.workflows",
        "speedwagon.workflows.tessdata",
        "speedwagon.ui",

    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', "behave", "pytest-qt"],
    python_requires=">=3.6",

    entry_points={
        "gui_scripts": [
            'speedwagon = speedwagon.__main__:main'
        ],
    },
    include_package_data=True,
    package_data={
        'speedwagon.workflows.tessdata': [
            'speedwagon/workflows/tessdata/*.*',
            "speedwagon/workflows/tessdata/eng.traineddata",
            "speedwagon/workflows/tessdata/osd.traineddata",
        ],
        'speedwagon': ["favicon.ico", "logo.png"],
    },
    cmdclass=cmdclass
)

