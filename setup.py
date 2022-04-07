from setuptools import setup

if __name__ == "__main__":
    setup(
        test_suite="tests",
        install_requires=[
            "PySide6",
            "HathiZip>=0.1.10",
            "HathiValidate>=0.3.8",
            "pyhathiprep>=0.1.7",
            "pyyaml",
            "uiucprescon.imagevalidate>=0.1.9b2",
            "uiucprescon.ocr>=0.1.4b1",
            "uiucprescon.packager[kdu]>=0.2.15b2",
            "uiucprescon.images",
            "pykdu-compress>=0.1.7b2",
            'importlib_resources;python_version<"3.9"',
            'importlib-metadata;python_version<"3.8"',
            'typing-extensions;python_version<"3.8"',
            'lxml',
            "requests",
            "py3exiv2bind>=0.1.9b1",
        ],
        packages=[
            "speedwagon",
            "speedwagon.frontend",
            "speedwagon.frontend.cli",
            "speedwagon.frontend.qtwidgets",
            "speedwagon.frontend.qtwidgets.dialog",
            "speedwagon.frontend.qtwidgets.ui",
            "speedwagon.tasks",
            "speedwagon.workflows",
            "speedwagon.workflows.tessdata",

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
            'speedwagon': ["favicon.ico", "logo.png"],
            'speedwagon.frontend.qtwidgets.ui': [
                "tab_editor.ui",
                "main_window_shell.ui",
                "main_window2.ui",
                "console.ui",
                'setup_job.ui'
            ],
        },
    )
