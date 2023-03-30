"""Main UI code.

Mainly for connecting GUI elements, such as buttons, to functions and methods
that do the work
"""
from __future__ import annotations

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
if typing.TYPE_CHECKING:
    from speedwagon.workflow import AbsOutputOptionDataType
    from speedwagon.worker import AbsToolJobManager
    from speedwagon.config import SettingsData

__all__ = [
    "MainWindow2"
]

DEBUG_LOGGING_FORMAT = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')


Setting = namedtuple("Setting", ("installed_packages_title", "widget"))


class ToolConsole(QtWidgets.QWidget):
    """Logging console."""

    class ConsoleLogHandler(logging.handlers.BufferingHandler):
        class Signals(QtCore.QObject):
            message = QtCore.Signal(str)

        def __init__(self, console_widget: "ToolConsole"):
            super().__init__(capacity=10)
            self.signals = ToolConsole.ConsoleLogHandler.Signals()
            self.console_widget = console_widget
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

        # ======================================================================
        # Type hints:
        self._console: QtWidgets.QTextBrowser
        # ======================================================================

        #  Use a monospaced font based on what's on system running
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

    def close(self) -> bool:
        self.detach_logger()
        return super().close()

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


class ItemTabsWidget(QtWidgets.QWidget):
    tabs: QtWidgets.QTabWidget

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        with as_file(
                resources.files(qtwidgets.ui).joinpath("setup_job.ui")
        ) as ui_file:
            qtwidgets.ui_loader.load_ui(str(ui_file), self)
        self.layout().addWidget(self.tabs)

    def add_tab(self, tab: QtWidgets.QWidget, name: str) -> None:
        self.tabs.addTab(tab, name)

    @property
    def current_tab(self) -> Optional[qtwidgets.tabs.WorkflowsTab3]:
        return typing.cast(
            Optional[qtwidgets.tabs.WorkflowsTab3],
            self.tabs.currentWidget()
        )


class MainProgram(QtWidgets.QMainWindow):
    def __init__(
            self,
            work_manager: AbsToolJobManager,
            debug: bool = False
    ) -> None:
        super().__init__()

        self._debug = debug
        self.user_settings = None

        self.work_manager = work_manager

        self.log_manager: logging.Logger = self.work_manager.logger
        self.log_manager.setLevel(logging.DEBUG)

    def debug_mode(self, debug: bool) -> None:
        self._debug = debug


class MainWindowMenuBuilder:
    def __init__(self, parent: MainWindow2) -> None:
        self._parent = parent
        self._menu_bar: QtWidgets.QMenuBar = self._parent.menuBar()

        self.add_help: bool = True
        self.add_about: bool = True

        self.show_configuration_signal: \
            typing.Optional[typing.Callable[[], None]] = None

        self.show_system_info_signal: \
            typing.Optional[typing.Callable[[], None]] = None

        self.exit_function: typing.Optional[typing.Callable[[], bool]] = None

        self.save_log_function: \
            typing.Optional[typing.Callable[[], None]] = None

        self.export_signal: typing.Optional[typing.Callable[[], None]] = None
        self.import_signal: typing.Optional[typing.Callable[[], None]] = None

    def build(self) -> None:
        self._build_file_menu(self._menu_bar)

        self._build_job_menu(self._menu_bar)
        self._build_system_menu(self._menu_bar)

        self._build_help(self._menu_bar)

    def _build_system_menu(self, menu_bar: QtWidgets.QMenuBar) -> None:
        system_menu = menu_bar.addMenu("System")
        system_menu.setObjectName("systemMenu")

        self._build_config_action(system_menu)
        self._build_system_info_action(system_menu)

    def _build_system_info_action(self, system_menu: QtWidgets.QMenu) -> None:
        # System --> System Info
        # Create a system info menu item
        if self.show_system_info_signal is not None:

            system_info_menu_item = QtGui.QAction(
                "System Info",
                self._parent
            )

            system_info_menu_item.setObjectName("systemInfoAction")
            # pylint: disable=no-member
            system_info_menu_item.triggered.connect(  # type: ignore
                self.show_system_info_signal
            )
            system_menu.addAction(system_info_menu_item)

    def _build_config_action(self, system_menu: QtWidgets.QMenu) -> None:
        # System --> Configuration
        # Create a system info menu item
        if self.show_configuration_signal is not None:
            system_settings_menu_item = \
                QtGui.QAction("Settings", self._parent)

            system_settings_menu_item.setObjectName('settingsAction')
            # pylint: disable=no-member
            system_settings_menu_item.triggered.connect(  # type: ignore
                self.show_configuration_signal
            )

            system_settings_menu_item.setShortcut("Ctrl+Shift+S")
            system_menu.addAction(system_settings_menu_item)

    def _build_file_menu(self, menu_bar: QtWidgets.QMenuBar) -> None:

        # File Menu
        file_menu = menu_bar.addMenu("File")
        self._build_export_log_action(file_menu)
        self._build_exit_action(file_menu)

    def _build_exit_action(self, file_menu: QtWidgets.QMenu) -> None:
        # File --> Exit
        # Create Exit button
        if self.exit_function is not None:
            exit_button = QtGui.QAction(" &Exit", self._parent)
            exit_button.setObjectName("exitAction")

            # pylint: disable=no-member
            exit_button.triggered.connect(  # type: ignore
                self.exit_function
            )
            file_menu.addAction(exit_button)

    def _build_export_log_action(self, file_menu: QtWidgets.QMenu) -> None:
        # File --> Export Log
        if self.save_log_function is not None:

            export_logs_button = QtGui.QAction(
                " &Export Log",
                self._parent
            )

            export_logs_button.setIcon(
                self._parent.style().standardIcon(
                    QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton)
            )
            # pylint: disable=no-member
            export_logs_button.triggered.connect(  # type: ignore
                self.save_log_function
            )
            file_menu.addAction(export_logs_button)
            file_menu.setObjectName("fileMenu")
            file_menu.addAction(export_logs_button)
            file_menu.setObjectName("fileMenu")
            file_menu.addSeparator()

    def _build_help(self, menu_bar: QtWidgets.QMenuBar) -> None:
        # Help Menu
        help_menu = menu_bar.addMenu("Help")

        if self.add_help is True:
            # Help --> Help
            # Create a Help menu item
            help_button = QtGui.QAction(" &Help ", self._parent)
            # pylint: disable=no-member
            help_button.triggered.connect(  # type: ignore
                self._parent.help_requested
            )
            help_menu.addAction(help_button)

        if self.add_about is True:
            # Help --> About
            # Create an About button
            about_button = QtGui.QAction(" &About ", self._parent)
            # pylint: disable=no-member
            about_button.triggered.connect(  # type: ignore
                self._parent.show_about_window
            )
            help_menu.addAction(about_button)

    def _build_job_menu(self, menu_bar: QtWidgets.QMenuBar) -> None:
        job_menu = menu_bar.addMenu("Job")
        job_menu.setObjectName("jobMenu")

        if self.export_signal is not None:
            export_button = QtGui.QAction(
                "Export",
                self._parent
            )

            # pylint: disable=no-member
            export_button.triggered.connect(self.export_signal)  # type: ignore
            job_menu.addAction(export_button)

        if self.import_signal is not None:
            import_button = QtGui.QAction(
                "Import",
                self._parent
            )

            # pylint: disable=no-member
            import_button.triggered.connect(self.import_signal)  # type: ignore

            job_menu.addAction(import_button)


class MainWindow2UI(QtWidgets.QMainWindow):
    main_splitter: QtWidgets.QSplitter
    main_layout: QtWidgets.QVBoxLayout
    console: ToolConsole
    tab_widget: ItemTabsWidget

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)
        with as_file(
                resources.files(qtwidgets.ui).joinpath("main_window2.ui")
        ) as ui_file:
            qtwidgets.ui_loader.load_ui(str(ui_file), self)

        # ======================================================================
        # Type hints
        # ======================================================================
        self.main_splitter: QtWidgets.QSplitter
        # ======================================================================


class MainWindow2(MainWindow2UI):
    submit_job = QtCore.Signal(str, dict)
    configuration_requested = QtCore.Signal(QtWidgets.QWidget)
    system_info_requested = QtCore.Signal(QtWidgets.QWidget)
    help_requested = QtCore.Signal()
    save_logs_requested = QtCore.Signal(QtWidgets.QWidget)
    export_job_config = QtCore.Signal(str, dict, QtWidgets.QWidget)
    import_job_config = QtCore.Signal(QtWidgets.QWidget)

    def __init__(
            self,
            job_manager: "speedwagon.runner_strategies.BackgroundJobManager",
            settings: typing.Optional[
                SettingsData
            ] = None
            ) -> None:
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.job_manager = job_manager
        self.user_settings = settings or {}

        self.main_layout.setContentsMargins(0, 0, 0, 0)

        ###########################################################
        #  Console
        ###########################################################
        self.console.attach_logger(self.logger)
        self.console.log_formatter.verbose = \
            typing.cast(
                bool,
                self.user_settings.get('debug', False)
            )
        ###########################################################
        self.setup_menu()
        ###########################################################

    def set_current_tab(self, tab_name: str) -> None:
        tab_index = self.locate_tab_index_by_name(tab_name)
        if tab_index is None:
            raise IndexError(f"No tab named {tab_name}")
        self.tab_widget.tabs.setCurrentIndex(tab_index)

    def locate_tab_index_by_name(self, name) -> typing.Optional[int]:
        for index in range(self.tab_widget.tabs.count()):
            if self.tab_widget.tabs.tabText(index) == name:
                return index
        return None

    def set_active_workflow(self, workflow_name: str) -> None:
        tab_index = self.locate_tab_index_by_name("All")
        if tab_index is None:
            raise AssertionError("Missing All tab")
        current_tab = self.tab_widget.current_tab
        if current_tab:
            current_tab.set_current_workflow(workflow_name)

    def set_current_workflow_settings(
            self,
            data: typing.Dict[str, typing.Any]
    ):
        tab_index = self.locate_tab_index_by_name("All")
        if tab_index is None:
            raise AssertionError("Missing All tab")
        current_tab = self.tab_widget.current_tab
        if current_tab:
            current_tab.set_current_workflow_settings(data)

    def close(self) -> bool:
        self.console.close()
        return super().close()

    def closeEvent(  # pylint: disable=C0103
            self,
            event: QtGui.QCloseEvent
    ) -> None:
        self.console.close()
        super().closeEvent(event)

    def setup_menu(self) -> None:
        builder = MainWindowMenuBuilder(parent=self)
        builder.exit_function = lambda: self.close()

        builder.show_system_info_signal = \
            lambda: self.system_info_requested.emit(self)

        builder.show_configuration_signal = \
            lambda: self.configuration_requested.emit(self)

        builder.save_log_function = self.save_log

        builder.export_signal = lambda: self.export_job_config.emit(
            self.get_current_workflow_name(),
            self.get_current_job_settings(),
            self
        )

        builder.import_signal = lambda: self.import_job_config.emit(self)

        builder.add_help = True
        builder.build()

    def get_current_workflow_name(self) -> typing.Optional[str]:
        current_tab = self.tab_widget.current_tab
        if not current_tab:
            return None
        klass = current_tab.workflow_selector.get_current_workflow_type()
        return klass.name if klass else None

    def get_current_job_settings(
            self
    ) -> typing.Dict[str, widgets.UserDataType]:

        current_tab = self.tab_widget.current_tab
        if current_tab is None:
            raise IndexError("Unable to locate the current tab")
        return typing.cast(
            typing.Dict[str, widgets.UserDataType],
            current_tab.workspace.configuration
        )

    def add_tab(
            self,
            tab_name: str,
            workflows: typing.Dict[
                str,
                typing.Type[Workflow]
            ]
    ) -> None:
        workflows_tab = qtwidgets.tabs.WorkflowsTab3(parent=self)
        workflows_tab.workflows = workflows
        workflows_tab.start_workflow.connect(self._start_workflow)
        self.tab_widget.add_tab(workflows_tab, tab_name)

    def _start_workflow(self,
                        workflow: str,
                        options: typing.Dict[str, typing.Any]) -> None:
        self.submit_job.emit(workflow, options)

    def show_about_window(self) -> None:
        qtwidgets.dialog.about_dialog_box(parent=self)

    def save_log(self) -> None:
        self.save_logs_requested.emit(self)


def set_app_display_metadata(app: QtWidgets.QApplication) -> None:
    with as_file(
            resources.files("speedwagon").joinpath("favicon.ico")
    ) as favicon_file:
        app.setWindowIcon(QtGui.QIcon(str(favicon_file)))
    try:
        app.setApplicationVersion(metadata.version(__package__))
    except metadata.PackageNotFoundError:
        pass
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
            option_data: AbsOutputOptionDataType = \
                model.data(index, models.ToolOptionsModel4.DataRole)

            if option_data.label == key:
                model.setData(index, value, QtCore.Qt.ItemDataRole.EditRole)
    settings_widget.set_model(model)
    settings_widget.update_widget()
