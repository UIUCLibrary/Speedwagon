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
        "pyqt5", "hathizip", "HathiValidate"
    ],
    packages=[
        "forseti",
        "forseti.tools",
        "forseti.ui"
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', "behave"],
    entry_points={
        "console_scripts": [
            'forseti = forseti.__main__:main'
        ]
    },
    cmdclass=cmdclass,
)
