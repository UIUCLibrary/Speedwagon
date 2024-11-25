"""Main UI code.

Mainly for connecting GUI elements, such as buttons, to functions and methods
that do the work
"""

from __future__ import annotations

import contextlib
import logging
import logging.handlers
import typing
from typing import Optional, TYPE_CHECKING
import sys

# pylint: disable=wrong-import-position
if sys.version_info < (3, 10):  # pragma: no cover
    import importlib_metadata as metadata
else:
    from importlib import metadata
from importlib import resources
from importlib.resources import as_file

from collections import namedtuple

from PySide6 import QtWidgets, QtCore, QtGui  # type: ignore


from speedwagon.frontend.qtwidgets import ui_loader, ui
import speedwagon.runner_strategies

from speedwagon.config import StandardConfig, FullSettingsData

if TYPE_CHECKING:
    from speedwagon.job import Workflow
    from speedwagon.frontend.qtwidgets import widgets
    from speedwagon.frontend.qtwidgets.tabs import ItemTabsWidget

__all__ = ["MainWindow3"]

DEBUG_LOGGING_FORMAT = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


Setting = namedtuple("Setting", ("installed_packages_title", "widget"))


class MainWindow3UI(QtWidgets.QMainWindow):
    main_splitter: QtWidgets.QSplitter
    main_layout: QtWidgets.QVBoxLayout
    console: widgets.ToolConsole
    tab_widget: ItemTabsWidget
    menu_bar: QtWidgets.QMenuBar
    action_exit: QtGui.QAction
    action_export_logs: QtGui.QAction
    action_export_job: QtGui.QAction
    action_import_job: QtGui.QAction
    action_system_info_requested: QtGui.QAction
    action_open_application_preferences: QtGui.QAction
    action_help_requested: QtGui.QAction
    action_about: QtGui.QAction

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        with as_file(
            resources.files(ui).joinpath("main_window.ui")
        ) as ui_file:
            ui_loader.load_ui(str(ui_file), self)


class MainWindow3(MainWindow3UI):
    """Main window widget.

    Version 3
    """

    submit_job = QtCore.Signal(str, dict)
    export_job_config = QtCore.Signal(str, dict, QtWidgets.QWidget)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        """Create a new widget.

        Args:
            parent: parent widget.
        """
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.job_manager: Optional[
            speedwagon.runner_strategies.BackgroundJobManager
        ] = None

        self.config_strategy: speedwagon.config.AbsConfigSettings = (
            StandardConfig()
        )

        self.main_layout.setContentsMargins(0, 0, 0, 0)

        ###########################################################
        #  Console
        ###########################################################
        self.console.attach_logger(self.logger)
        ###########################################################
        self.action_export_logs.setIcon(
            self.style().standardIcon(
                QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton
            )
        )
        ###########################################################
        self.action_export_job.triggered.connect(self._export_job_config)
        self.tab_widget.submit_job.connect(self.submit_job)
        self.submit_job.connect(lambda *args: print("got it"))

    def update_settings(self) -> None:
        """Update settings."""
        settings = self._get_settings()
        global_settings = settings.get("GLOBAL")
        if global_settings:
            debug_mode = global_settings.get("debug", False)
        else:
            debug_mode = False

        if debug_mode is True:
            if self.console.log_handler.level != logging.DEBUG:
                self.console.log_handler.setLevel(logging.DEBUG)
                self.console.add_message(
                    "Putting Speedwagon into Debug mode. "
                )
            self.setWindowTitle("Speedwagon (DEBUG)")
        else:
            if self.console.log_handler.level != logging.INFO:
                self.console.log_handler.setLevel(logging.INFO)
                self.console.add_message(
                    "Putting Speedwagon into Normal mode. "
                )
            self.setWindowTitle("Speedwagon")

    def _export_job_config(self) -> None:
        if self.tab_widget.current_tab is not None:
            self.export_job_config.emit(
                self.tab_widget.current_tab.workspace.name,
                self.tab_widget.current_tab.workspace.configuration,
                self,
            )

    def locate_tab_index_by_name(self, name: str) -> typing.Optional[int]:
        """Get tab index by name."""
        for index in range(self.tab_widget.tabs.count()):
            if self.tab_widget.tabs.tabText(index) == name:
                return index
        return None

    def clear_tabs(self) -> None:
        """Clear all tabs."""
        self.tab_widget.clear_tabs()

    def add_tab(
        self, tab_name: str, workflows: typing.Dict[str, typing.Type[Workflow]]
    ) -> None:
        """Add tab."""
        self.tab_widget.add_workflows_tab(tab_name, list(workflows.values()))

    def set_active_workflow(self, workflow_name: str) -> None:
        """Set active workflow."""
        tab_index = self.locate_tab_index_by_name("All")
        if tab_index is None:
            raise AssertionError("Missing All tab")
        self.tab_widget.tabs.setCurrentIndex(tab_index)
        current_tab = self.tab_widget.current_tab
        if current_tab:
            current_tab.set_current_workflow(workflow_name)

    def set_current_workflow_settings(
        self, data: typing.Dict[str, typing.Any]
    ) -> None:
        """Set current workflow settings."""
        tab_index = self.locate_tab_index_by_name("All")
        if tab_index is None:
            raise AssertionError("Missing All tab")
        current_tab = self.tab_widget.current_tab
        if current_tab:
            current_tab.set_current_workflow_settings(data)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Run closing event."""
        self.console.detach_logger()
        super().closeEvent(event)

    def _get_settings(self) -> FullSettingsData:
        return self.config_strategy.settings()


def set_app_display_metadata(app: QtWidgets.QApplication) -> None:
    with as_file(
        resources.files("speedwagon").joinpath("favicon.ico")
    ) as favicon_file:
        app.setWindowIcon(QtGui.QIcon(str(favicon_file)))
    with contextlib.suppress(metadata.PackageNotFoundError):
        app.setApplicationVersion(metadata.version(__package__))
    app.setApplicationDisplayName("Speedwagon")
    QtWidgets.QApplication.processEvents()
