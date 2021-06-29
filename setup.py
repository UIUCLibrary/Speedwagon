import glob
import os
import sys
from setuptools import setup
sys.path.insert(0, os.path.dirname(__file__))
import extra_commands

cmdclass = {
    # "build_ui": build_ui,
    "build_py": extra_commands.CustomBuildPy,
    "clean": extra_commands.Clean,
    # "build_py": extra_commands.build_py,
}
try:
    from pyqt_distutils.build_ui import build_ui
    cmdclass["build_ui"] = build_ui
except ModuleNotFoundError:
    pass

cmdclass['dl_tessdata'] = extra_commands.TesseractData

if __name__ == "__main__":
    setup(
        test_suite="tests",
        install_requires=[
            "PyQt5>=5.15.4",
            "HathiZip>=0.1.9",
            "HathiValidate>=0.3.6",
            "pyhathiprep>=0.1.5",
            "pyyaml",
            "uiucprescon.imagevalidate>=0.1.6",
            "uiucprescon.ocr>=0.1.2",
            "uiucprescon.packager[kdu]>=0.2.12",
            "uiucprescon.images",
            "pykdu-compress>=0.1.5",
            'importlib_resources;python_version<"3.9"',
            'importlib-metadata;python_version<"3.8"',
            'typing-extensions;python_version<"3.8"',
            'lxml',
            "requests",
            "py3exiv2bind>=0.1.5",
        ],
        packages=[
            "speedwagon",
            "speedwagon.dialog",
            "speedwagon.workflows",
            "speedwagon.workflows.tessdata",
            "speedwagon.ui",

        ],
        setup_requires=['pytest-runner','PyQt5', 'pyqt-distutils'],
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