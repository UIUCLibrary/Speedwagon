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
        # "build_py": extra_commands.build_py,
    }

except ImportError:
    cmdclass = {}

cmdclass['dl_tessdata'] = extra_commands.TesseractData


setup(
    test_suite="tests",
    install_requires=[
        "PyQt5",
        "HathiZip",
        "HathiValidate>=0.3.4",
        "pyhathiprep",
        "pyyaml",
        "hathichecksumupdater",
        "uiucprescon-getmarc>=0.1.1",
        "uiucprescon.imagevalidate>=0.1.5b1",
        "uiucprescon.ocr>=0.1.1b1",
        "uiucprescon.packager[kdu]>=0.2.11b1",
        "uiucprescon.images",
        "pykdu-compress>=0.1.3b1",
        "setuptools>=30.3.0",
        'importlib_resources;python_version<"3.7"',
        'lxml',
        "py3exiv2bind>=0.1.5b3",
    ],
    packages=[
        "speedwagon",
        "speedwagon.dialog",
        "speedwagon.workflows",
        "speedwagon.workflows.tessdata",
        "speedwagon.ui",

    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', "behave", "pytest-qt"],
    python_requires=">=3.6",

    entry_points={
        "gui_scripts": [
            'speedwagon = speedwagon.__main__:main',
            'sw-tab-editor = speedwagon.startup:standalone_tab_editor'
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

# TODO: Overwrite install command class to check if the UI file have converted
#  into py files. if not, run build_ui