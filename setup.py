from setuptools import setup

if __name__ == "__main__":
    setup(
        test_suite="tests",
        install_requires=[
            "HathiZip>=0.1.10",
            "HathiValidate>=0.3.8",
            "pyhathiprep>=0.1.7",
            "pyyaml",
            "uiucprescon.imagevalidate>=0.1.9",
            "uiucprescon.ocr>=0.1.4",
            "uiucprescon.packager[kdu]>=0.2.15",
            "uiucprescon.images",
            "pykdu-compress>=0.1.8",
            'importlib_resources;python_version<"3.9"',
            'importlib-metadata;python_version<"3.10"',
            'typing-extensions;python_version<"3.11"',
            'lxml',
            "requests",
            "py3exiv2bind>=0.1.10",
        ],
        packages=[
            "speedwagon",
            "speedwagon.config",
            "speedwagon.frontend",
            "speedwagon.frontend.cli",
            "speedwagon.frontend.qtwidgets",
            "speedwagon.frontend.qtwidgets.dialog",
            "speedwagon.frontend.qtwidgets.models",
            "speedwagon.frontend.qtwidgets.ui",
            "speedwagon.tasks",
            "speedwagon.workflows",
        ],
        # setup_requires=['pytest-runner'],
        tests_require=[
            'pytest',
            'pytest-mock'
        ],
        python_requires=">=3.7",
        extras_require={
          "QT": ["PySide6==6.4.*"]
        },
        entry_points={
            "gui_scripts": [
                'speedwagon = speedwagon.__main__:main',
                'sw-tab-editor = speedwagon.startup:standalone_tab_editor'
            ],
        },
        include_package_data=True,
        package_data={
            'speedwagon': ["favicon.ico", "logo.png", 'py.typed'],
            'speedwagon.frontend.qtwidgets.ui': [
                "console.ui",
                "main_window3.ui",
                "main_window_shell.ui",
                "plugin_settings.ui",
                "select_workflow_widget.ui",
                'setup_job.ui',
                "tab_editor.ui",
                "workflow_progress.ui",
                "workspace.ui",
            ],
        },
    )
