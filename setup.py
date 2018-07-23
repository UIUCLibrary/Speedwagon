import glob

import os
from setuptools import setup
from distutils.command.clean import clean as _clean
from distutils.command.build_py import build_py

try:
    from pyqt_distutils.build_ui import build_ui
    from pyqt_distutils.config import Config

    class CustomBuildPy(build_py):
        def run(self):
            self.run_command("build_ui")
            super().run()

    class Clean(_clean):
        def run(self):
            super().run()
            config = Config()
            config.load()
            for glob_exp, dest in config.files:
                for src in glob.glob(glob_exp):

                    if src.endswith(".ui"):
                        gen_file = "{}_ui.py".format(os.path.splitext(src)[0])
                        if os.path.exists(gen_file):
                            print("Removing {}".format(gen_file))
                            os.remove(gen_file)

    cmdclass = {
        "build_ui": build_ui,
        "build_py": CustomBuildPy,
        "clean": Clean,
    }

except ImportError:
    cmdclass = {}

setup(
    test_suite="tests",
    install_requires=[
        "PyQt5",
        "hathizip",
        "HathiValidate>=0.3.3",
        "pyhathiprep",
        "hathichecksumupdater",
        "uiucprescon-getmarc",
        "uiucprescon-imagevalidate>=0.1.1",
        "uiucprescon-packager[kdu]>=0.2.1",
        "pykdu-compress>=0.0.4",
        "setuptools>=30.3.0",
        'lxml'
    ],
    packages=[
        "speedwagon",
        "speedwagon.tools",
        "speedwagon.workflows",
        "speedwagon.ui"
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', "behave", "pytest-qt"],
    python_requires=">=3.6",
    entry_points={
        "gui_scripts": [
            'speedwagon = speedwagon.__main__:main'
        ]
    },
    package_data={'speedwagon': ["favicon.ico"]},
    cmdclass=cmdclass,
)
