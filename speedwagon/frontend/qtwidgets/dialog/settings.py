"""Configuration settings."""

import os
import platform
import typing
from typing import Optional, Dict, cast, Type
from PySide6 import QtWidgets, QtCore  # type: ignore
try:  # pragma: no cover
    from importlib.resources import as_file
    from importlib import resources
except ImportError:  # pragma: no cover
    from importlib_resources import as_file
    import importlib_resources as resources  # type: ignore

from speedwagon.config import \
    AbsOpenSettings, \
    DarwinOpenSettings, \
    WindowsOpenSettings, \
    OpenSettingsDirectory

from speedwagon import job
from speedwagon.frontend import qtwidgets
from speedwagon.frontend.qtwidgets import models

__all__ = ['GlobalSettingsTab', 'TabsConfigurationTab', 'TabEditor']


class UnsupportedOpenSettings(AbsOpenSettings):

    def __init__(self,
                 settings_directory: str,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(settings_directory)
        self.parent = parent

    def system_open_directory(self, settings_directory: str) -> None:
        msg = QtWidgets.QMessageBox(parent=self.parent)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msg.setText(
            f"Don't know how to do that on {platform.system()}"
        )

        msg.show()


class SettingsDialog(QtWidgets.QDialog):

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0)
    ) -> None:
        super().__init__(parent, flags)
        self.settings_location: Optional[str] = None

        self.setWindowTitle("Settings")
        layout = QtWidgets.QVBoxLayout(self)
        self.tabs_widget = QtWidgets.QTabWidget(self)
        layout.addWidget(self.tabs_widget)

        self.open_settings_path_button = QtWidgets.QPushButton(self)
        self.open_settings_path_button.setText("Open Config File Directory")

        # pylint: disable=no-member
        # pylint: disable=unnecessary-lambda
        # This needs a lambda to delay execution. Otherwise Qt might segfault
        # when it tries to open the dialog box
        self.open_settings_path_button.clicked.connect(  # type: ignore
            lambda: self.open_settings_dir()
        )
        # pylint: enable=unnecessary-lambda

        layout.addWidget(self.open_settings_path_button)

        self._button_box = \
            QtWidgets.QDialogButtonBox(
                cast(
                    QtWidgets.QDialogButtonBox.StandardButton,
                    QtWidgets.QDialogButtonBox.StandardButton.Cancel |
                    QtWidgets.QDialogButtonBox.StandardButton.Ok
                )
            )

        self._button_box.accepted.connect(  # type: ignore
            self.accept
        )
        self._button_box.rejected.connect(  # type: ignore
            self.reject
        )
        layout.addWidget(self._button_box)

        self.setLayout(layout)
        self.setFixedHeight(480)
        self.setFixedWidth(600)

    def add_tab(self, tab: QtWidgets.QWidget, tab_name: str) -> None:
        self.tabs_widget.addTab(tab, tab_name)

    def open_settings_dir(
            self,
            strategy: Optional[AbsOpenSettings] = None
    ) -> None:
        if self.settings_location is None:
            return

        strategies: Dict[str, AbsOpenSettings] = {
            "Darwin": DarwinOpenSettings(self.settings_location),
            "Windows": WindowsOpenSettings(self.settings_location)
        }

        folder_opener = OpenSettingsDirectory(
            strategy if strategy is not None else strategies.get(
                platform.system(),
                UnsupportedOpenSettings(
                    settings_directory=self.settings_location, parent=self)
            )
        )

        folder_opener.open()


class GlobalSettingsTab(QtWidgets.QWidget):
    """Widget for editing global settings."""

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0)
    ) -> None:
        """Create a global settings tab widget."""
        super().__init__(parent, flags)
        self.config_file: Optional[str] = None
        self._modified = False

        layout = QtWidgets.QVBoxLayout(self)

        self.settings_table = QtWidgets.QTableView(self)

        self.settings_table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self.settings_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.settings_table)
        self.setLayout(layout)

    def read_config_data(self) -> None:
        """Read configuration file."""
        if self.config_file is None:
            raise FileNotFoundError("No Configuration file set")
        if not os.path.exists(self.config_file):
            raise FileNotFoundError("Invalid Configuration file set")

        self.settings_table.setModel(
            models.build_setting_qt_model(self.config_file)
        )

        self.settings_table.model().dataChanged.connect(  # type: ignore
            self.on_modified
        )

    def on_modified(self) -> None:
        """Set modified to true."""
        self._modified = True

    def on_okay(self) -> None:
        """Execute when a user selects okay."""
        if not self._modified:
            return
        if self.config_file is None:
            msg = QtWidgets.QMessageBox(parent=self)
            msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            msg.setText("Unable to save settings. No configuration file set")
            msg.exec()
            return

        print("Saving changes")

        data = models.serialize_settings_model(
            self.settings_table.model()
        )

        with open(self.config_file, "w", encoding="utf-8") as file_writer:
            file_writer.write(data)

        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("Saved changes")
        msg_box.setText("Please restart changes to take effect")
        msg_box.exec()


class TabsConfigurationTab(QtWidgets.QWidget):
    """Tabs configuration widget."""

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0)
    ) -> None:
        """Create a tab configuration widget."""
        super().__init__(parent, flags)
        self.settings_location: Optional[str] = None
        self._modified = False
        layout = QtWidgets.QVBoxLayout(self)
        self.editor = TabEditor()
        self.editor.layout().setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        self.setLayout(layout)

    def on_okay(self) -> None:
        """Execute when a user selects okay."""
        if self.editor.modified is False:
            return
        if self.settings_location is None:
            msg = QtWidgets.QMessageBox(parent=self)
            msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            msg.setText("Unable to save settings. No settings location set")
            msg.exec()
            return
        print(f"Saving changes to {self.settings_location}")
        qtwidgets.tabs.write_tabs_yaml(
            self.settings_location,
            qtwidgets.tabs.extract_tab_information(
                cast(
                    models.TabsModel,
                    self.editor.selected_tab_combo_box.model()
                )
            )
        )

        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("Saved changes to tabs files")
        msg_box.setText("Please restart changes to take effect")
        msg_box.exec()

    def load(self) -> None:
        """Load configuration settings."""
        print(f"loading {self.settings_location}")
        self.editor.tabs_file = self.settings_location
        workflows = job.available_workflows()
        self.editor.set_all_workflows(workflows)


class SettingsBuilder:
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        """Create a new settings dialog builder.

        Args:
            parent: Parent widget of the settings window.
        """
        self._parent = parent
        self._settings_path: typing.Optional[str] = None
        self._global_config_file_path: typing.Optional[str] = None
        self._tab_config_file_path: typing.Optional[str] = None
        self._global_settings_tab: typing.Optional[GlobalSettingsTab] = None

    def _build_tab_editor_tab(self, config_dialog: SettingsDialog) -> None:
        tabs_tab = TabsConfigurationTab()
        if self._settings_path is not None:
            tabs_tab.settings_location = self._tab_config_file_path
            tabs_tab.load()

        config_dialog.add_tab(tabs_tab, "Tabs")
        config_dialog.accepted.connect(  # type: ignore
            tabs_tab.on_okay
        )

    def _build_global_settings(self, config_dialog: SettingsDialog) -> None:
        global_settings_tab = GlobalSettingsTab()
        if self._global_config_file_path is not None:
            global_settings_tab.config_file = self._global_config_file_path
            global_settings_tab.read_config_data()

        config_dialog.accepted.connect(  # type: ignore
            global_settings_tab.on_okay
        )
        self._global_settings_tab = global_settings_tab

        if self._global_settings_tab is not None:
            config_dialog.add_tab(self._global_settings_tab, "Global Settings")

    def build(self) -> SettingsDialog:
        """Generate a new SettingsDialog object."""
        config_dialog = SettingsDialog(parent=self._parent)
        if self._settings_path is not None:
            config_dialog.settings_location = self._settings_path
        else:
            config_dialog.open_settings_path_button.setVisible(False)

        if self._global_config_file_path is not None:
            self._build_global_settings(config_dialog)

        if self._tab_config_file_path is not None:
            self._build_tab_editor_tab(config_dialog)

        return config_dialog

    def add_global_settings(self, path: str) -> None:
        self._global_config_file_path = path

    def add_tabs_setting(self, path: str) -> None:
        self._tab_config_file_path = path

    def add_open_settings(self, path: str) -> None:
        self._settings_path = path


class TabEditorWidget(QtWidgets.QWidget):
    tab_workflows_list_view: QtWidgets.QListView
    selected_tab_combo_box: QtWidgets.QComboBox
    new_tab_button: QtWidgets.QPushButton
    delete_current_tab_button: QtWidgets.QPushButton
    add_items_button: QtWidgets.QPushButton
    remove_items_button: QtWidgets.QPushButton
    splitter: QtWidgets.QSplitter

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0)
    ) -> None:
        """Create a tab editor widget."""
        super().__init__(parent, flags)
        self.load_ui_file()

    def load_ui_file(self) -> None:

        with as_file(
                resources.files(
                    "speedwagon.frontend.qtwidgets.ui"
                ).joinpath("tab_editor.ui")
        ) as ui_file:
            qtwidgets.ui_loader.load_ui(str(ui_file), self)


class TabEditor(TabEditorWidget):
    """Widget for editing tabs."""

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0)
    ) -> None:
        """Create a tab editor widget."""
        super().__init__(parent, flags)
        self.tabs_model = models.TabsModel()
        self.selected_tab_combo_box.setModel(self.tabs_model)

        self._tabs_file: Optional[str] = None

        self._all_workflows_model: models.WorkflowListModel2 = \
            models.WorkflowListModel2()

        self._active_tab_workflows_model: \
            models.WorkflowListModel2 = \
            models.WorkflowListModel2()

        self.tab_workflows_list_view.setModel(
            self._active_tab_workflows_model
        )
        selected_tab_combo_box = self.selected_tab_combo_box
        selected_tab_combo_box.currentIndexChanged.connect(  # type: ignore
            self._changed_tab
        )

        self.new_tab_button.clicked.connect(  # type: ignore
            self._create_new_tab
        )

        self.delete_current_tab_button.clicked.connect(  # type: ignore
            self._delete_tab
        )

        self.add_items_button.clicked.connect(  # type: ignore
            self._add_items_to_tab
        )
        self.remove_items_button.clicked.connect(  # type: ignore
            self._remove_items
        )

        # pylint: disable=no-member
        self.tabs_model.dataChanged.connect(self.on_modified)  # type: ignore
        self.modified: bool = False
        self.splitter.setChildrenCollapsible(False)

    def on_modified(self) -> None:
        """Set modified to true."""
        self.modified = True

    @property
    def tabs_file(self) -> Optional[str]:
        """Get tabs file used."""
        return self._tabs_file

    @tabs_file.setter
    def tabs_file(self, value: str) -> None:

        for tab in qtwidgets.tabs.read_tabs_yaml(value):

            tab.workflows_model.dataChanged.connect(  # type: ignore
                self.on_modified
            )
            self.tabs_model.add_tab(tab)
        self.selected_tab_combo_box.setCurrentIndex(0)
        self._tabs_file = value
        self.modified = False

    def _changed_tab(self, tab: int) -> None:
        model: QtCore.QAbstractListModel = cast(
            models.TabsModel,
            self.selected_tab_combo_box.model()
        )
        index = model.index(tab)
        if index.isValid():
            data = model.data(
                index,
                role=typing.cast(int, QtCore.Qt.ItemDataRole.UserRole)
            )
            self.tab_workflows_list_view.setModel(data.workflows_model)
        else:
            self.tab_workflows_list_view.setModel(
                models.WorkflowListModel2()
            )

    def _create_new_tab(self) -> None:
        while True:
            new_tab_name: str
            accepted: bool
            new_tab_name, accepted = QtWidgets.QInputDialog.getText(
                self.parentWidget(), "Create New Tab", "Tab name")

            # The user cancelled
            if not accepted:
                return

            if new_tab_name in self.tabs_model:
                message = f"Tab named \"{new_tab_name}\" already exists."
                error = QtWidgets.QMessageBox(self)
                error.setText(message)
                error.setWindowTitle("Unable to Create New Tab")
                error.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                error.exec()
                continue

            new_tab = qtwidgets.tabs.TabData(
                new_tab_name,
                models.WorkflowListModel2()
            )

            self.tabs_model.add_tab(new_tab)
            new_index = self.selected_tab_combo_box.findText(new_tab_name)
            self.selected_tab_combo_box.setCurrentIndex(new_index)
            return

    def _delete_tab(self) -> None:
        data = self.selected_tab_combo_box.currentData()
        model = self.selected_tab_combo_box.model()
        model.remove_tab(data)

    def _add_items_to_tab(self) -> None:
        model = cast(
            models.WorkflowListModel2,
            self.tab_workflows_list_view.model()
        )
        for i in self.all_workflows_list_view.selectedIndexes():
            new_workflow = i.data(role=QtCore.Qt.ItemDataRole.UserRole)
            model.add_workflow(new_workflow)
        model.sort(0)

    def _remove_items(self) -> None:
        model = cast(
            models.WorkflowListModel2,
            self.tab_workflows_list_view.model()
        )
        items_to_remove = [
            i.data(role=QtCore.Qt.ItemDataRole.UserRole)
            for i in self.tab_workflows_list_view.selectedIndexes()
        ]

        for item in items_to_remove:
            model.remove_workflow(item)
        model.sort()

    def set_all_workflows(
            self,
            workflows: Dict[str, Type[job.Workflow]]
    ) -> None:
        """Set up all workflows."""
        for values in workflows.values():
            self._all_workflows_model.add_workflow(values)

        self._all_workflows_model.sort(0)
        self.all_workflows_list_view.setModel(self._all_workflows_model)

    @property
    def current_tab(self) -> QtWidgets.QWidget:
        """Get current tab widget."""
        return self.selected_tab_combo_box.currentData()
