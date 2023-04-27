"""Main UI code.

Mainly for connecting GUI elements, such as buttons, to functions and methods
that do the work
"""

from __future__ import annotations

import contextlib
import logging
import logging.handlers
import typing
from typing import List, Optional, Dict

try:  # pragma: no cover
    from importlib import metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore

try:  # pragma: no cover
    from importlib.resources import as_file
    from importlib import resources
except ImportError:  # pragma: no cover
    import importlib_resources as resources  # type: ignore
    from importlib_resources import as_file

from collections import namedtuple

from PySide6 import QtWidgets, QtCore, QtGui  # type: ignore

import speedwagon
from speedwagon.frontend import qtwidgets
from speedwagon.frontend.qtwidgets import widgets, models
import speedwagon.runner_strategies
from speedwagon.job import Workflow
from speedwagon.workflow import AbsOutputOptionDataType
from speedwagon.config import StandardConfig, FullSettingsData

__all__ = [
    "MainWindow3"
]

DEBUG_LOGGING_FORMAT = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')


Setting = namedtuple("Setting", ("installed_packages_title", "widget"))


class ToolConsole(QtWidgets.QWidget):
    """Logging console."""
    _console: QtWidgets.QTextBrowser

    class ConsoleLogHandler(logging.handlers.BufferingHandler):
        class Signals(QtCore.QObject):
            message = QtCore.Signal(str)

        def __init__(self, console_widget: "ToolConsole"):
            super().__init__(capacity=10)
            self.signals = ToolConsole.ConsoleLogHandler.Signals()
            self.console_widget = console_widget
            # self.console_widget.deleteLater()
            self.signals.message.connect(self.console_widget.add_message)

        def flush(self) -> None:
            if len(self.buffer) > 0:
                message_buffer = [
                    self.format(record) for record in self.buffer
                ]
                message = "".join(message_buffer).strip()
                self.signals.message.emit(message)
            super().flush()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.log_handler = ToolConsole.ConsoleLogHandler(self)

        self.log_formatter = qtwidgets.logging_helpers.ConsoleFormatter()
        self.log_handler.setFormatter(self.log_formatter)

        with as_file(
                resources.files(qtwidgets.ui).joinpath("console.ui")
        ) as ui_file:
            qtwidgets.ui_loader.load_ui(str(ui_file), self)
        #
        # #  Use a monospaced font based on what's on system running
        monospaced_font = \
            QtGui.QFontDatabase.systemFont(
                QtGui.QFontDatabase.SystemFont.FixedFont
            )

        self._log = QtGui.QTextDocument()
        self._log.setDefaultFont(monospaced_font)
        # pylint: disable=no-member
        self._log.contentsChanged.connect(self._follow_text)
        self._console.setDocument(self._log)
        self._console.setFont(monospaced_font)

        self._attached_logger: typing.Optional[logging.Logger] = None
        self.cursor: QtGui.QTextCursor = QtGui.QTextCursor(self._log)

    def _follow_text(self) -> None:
        cursor = QtGui.QTextCursor(self._log)
        cursor.movePosition(cursor.MoveOperation.End)
        self._console.setTextCursor(cursor)

    @QtCore.Slot(str)
    def add_message(
            self,
            message: str,
    ) -> None:

        self.cursor.movePosition(self.cursor.MoveOperation.End)
        self.cursor.beginEditBlock()
        self._console.setTextCursor(self.cursor)
        self.cursor.insertHtml(message)
        self.cursor.endEditBlock()

    @property
    def text(self) -> str:
        return self._log.toPlainText()

    def attach_logger(self, logger: logging.Logger) -> None:
        logger.addHandler(self.log_handler)
        self._attached_logger = logger

    def detach_logger(self) -> None:
        if self._attached_logger is not None:
            self.log_handler.flush()
            self._attached_logger.removeHandler(self.log_handler)
            self._attached_logger = None


class ItemTabsUI(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        with as_file(
                resources.files(qtwidgets.ui).joinpath("setup_job.ui")
        ) as ui_file:
            qtwidgets.ui_loader.load_ui(str(ui_file), self)


class ItemTabsWidget(ItemTabsUI):
    tabs: QtWidgets.QTabWidget
    submit_job = QtCore.Signal(str, dict)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.layout().addWidget(self.tabs)
        self._model = models.TabsTreeModel()
        self._model.modelReset.connect(self._model_reset)

    def model(self):
        return self._model

    def _model_reset(self):
        self.tabs.clear()
        tab_count = self._model.rowCount()
        for tab_row_id in range(tab_count):
            tab_index = self._model.index(tab_row_id)
            tab_name = self._model.data(tab_index)

            workflows_tab = qtwidgets.tabs.WorkflowsTab3(parent=self.tabs)
            workflows_tab.start_workflow.connect(self.submit_job)

            workflow_klasses = {}
            for workflow_row_id in range(self._model.rowCount(tab_index)):
                workflow = self._model.data(
                    self._model.index(workflow_row_id, parent=tab_index),
                    role=models.TabsTreeModel.WorkflowClassRole
                )

                workflow_klasses[workflow.name] = workflow
            tab_model = models.TabProxyModel()
            tab_model.setSourceModel(self._model)
            tab_model.set_source_tab(tab_name)
            workflows_tab.set_model(tab_model)

            self.tabs.addTab(workflows_tab, tab_name)

    def add_tab(self, tab: QtWidgets.QWidget, name: str) -> None:
        self.tabs.addTab(tab, name)

    def add_workflows_tab(self, name, workflows):
        self._model.append_workflow_tab(name, workflows)

    def clear_tabs(self) -> None:
        self._model.clear()
        self._model_reset()

    def count(self) -> int:
        return self.tabs.count()

    @property
    def current_tab(self) -> Optional[qtwidgets.tabs.WorkflowsTab3]:
        return typing.cast(
            Optional[qtwidgets.tabs.WorkflowsTab3],
            self.tabs.currentWidget()
        )


class MainWindow3UI(QtWidgets.QMainWindow):
    main_splitter: QtWidgets.QSplitter
    main_layout: QtWidgets.QVBoxLayout
    console: ToolConsole
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
                resources.files(qtwidgets.ui).joinpath("main_window3.ui")
        ) as ui_file:
            qtwidgets.ui_loader.load_ui(str(ui_file), self)


class MainWindow3(MainWindow3UI):
    submit_job = QtCore.Signal(str, dict)
    export_job_config = QtCore.Signal(str, dict, QtWidgets.QWidget)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.job_manager: Optional[
            speedwagon.runner_strategies.BackgroundJobManager
        ] = None

        self.config_strategy: speedwagon.config.AbsConfigSettings = \
            StandardConfig()

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
                self
            )

    def locate_tab_index_by_name(self, name: str) -> typing.Optional[int]:
        for index in range(self.tab_widget.tabs.count()):
            if self.tab_widget.tabs.tabText(index) == name:
                return index
        return None

    def clear_tabs(self) -> None:
        self.tab_widget.clear_tabs()

    def add_tab(
            self,
            tab_name: str,
            workflows: typing.Dict[
                str,
                typing.Type[Workflow]
            ]
    ) -> None:
        self.tab_widget.add_workflows_tab(tab_name, workflows.values())

    def set_active_workflow(self, workflow_name: str) -> None:
        tab_index = self.locate_tab_index_by_name("All")
        if tab_index is None:
            raise AssertionError("Missing All tab")
        self.tab_widget.tabs.setCurrentIndex(tab_index)
        current_tab = self.tab_widget.current_tab
        if current_tab:
            current_tab.set_current_workflow(workflow_name)

    def set_current_workflow_settings(
            self,
            data: typing.Dict[str, typing.Any]
    ) -> None:
        tab_index = self.locate_tab_index_by_name("All")
        if tab_index is None:
            raise AssertionError("Missing All tab")
        current_tab = self.tab_widget.current_tab
        if current_tab:
            current_tab.set_current_workflow_settings(data)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
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
    app.setApplicationDisplayName(f"{speedwagon.__name__.title()}")
    QtWidgets.QApplication.processEvents()


def load_job_settings_model(
        data: Dict[str, widgets.UserDataType],
        settings_widget: widgets.DynamicForm,
        workflow_options: List[AbsOutputOptionDataType]
) -> None:
    model = models.ToolOptionsModel4(workflow_options)
    for key, value in data.items():
        for i in range(model.rowCount()):
            index = model.index(i)
            option_data = typing.cast(
                AbsOutputOptionDataType,
                model.data(index, models.ToolOptionsModel4.DataRole)
            )

            if option_data.label == key:
                model.setData(index, value, QtCore.Qt.ItemDataRole.EditRole)
    settings_widget.set_model(model)
    settings_widget.update_widget()
