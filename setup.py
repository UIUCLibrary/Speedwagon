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
            self.run_command("dl_tessdata")
            super().run()

    class Clean(_clean):
        def run(self):
            super().run()
            self.clean_ui()
            self.clean_tesseract_data()

        @staticmethod
        def clean_tesseract_data():
            base = os.path.abspath(os.path.dirname(__file__))
            tessdata_path = os.path.join(
                base, "speedwagon", "workflows", "tessdata"
            )

            glob_exp = os.path.join(tessdata_path, "*.traineddata")
            for tesseract_data_file in glob.glob(glob_exp):
                print("Removing {}".format(tesseract_data_file))
                os.remove(tesseract_data_file)

            if os.path.exists(tessdata_path):
                print("Removing {}".format(tessdata_path))
                os.removedirs(tessdata_path)

        @staticmethod
        def clean_ui():
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
        "importlib_resources",
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
        ],
         "distutils.commands": [
            "dl_tessdata = speedwagon.tessdata:TesseractData",
        ],
    },
    package_data={
        'speedwagon': ["favicon.ico"],
        'speedwagon.workflows': ['speedwagon.workflows/tessdata/*.traineddata']
    },
    cmdclass=cmdclass,
)
