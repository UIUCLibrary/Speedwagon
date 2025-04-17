"""Configuration settings."""
from __future__ import annotations
import abc
import logging
import os
import platform
import subprocess
import typing
from typing import (
    Optional,
    Dict,
    cast,
    List,
    Tuple,
    Callable,
    Iterable,
    TypedDict,
    Generic, TypeVar,
    TYPE_CHECKING,
    Type,
)
import sys
# pylint: disable=wrong-import-position
from importlib import resources
from importlib.resources import as_file

from PySide6 import QtWidgets, QtCore  # type: ignore

from speedwagon import config
from speedwagon.frontend.qtwidgets.ui_loader import load_ui
from speedwagon.frontend.qtwidgets.widgets import (
    PluginConfig,
    WorkflowSettingsEditor,
)
from speedwagon.frontend.qtwidgets.models import tabs as tab_models
from speedwagon.frontend.qtwidgets.models.settings import (
    unpack_global_settings_model,
    build_setting_qt_model,
    WorkflowsSettings
)
from speedwagon.frontend.qtwidgets import models
from speedwagon.config.tabs import NullTabsConfig

if TYPE_CHECKING:
    from speedwagon.config.tabs import AbsTabsConfigDataManagement
    from speedwagon.job import Workflow


if sys.version_info < (3, 10):  # pragma: no cover
    import importlib_metadata as metadata
else:
    from importlib import metadata

__all__ = ["GlobalSettingsTab", "TabsConfigurationTab", "TabEditor"]

SaveCallback = Callable[["SettingsTab"], Dict[str, typing.Any]]

DEFAULT_WINDOW_FLAGS = QtCore.Qt.WindowType(0)

T = TypeVar("T")

logger = logging.getLogger(__name__)


class TabsSettingsData(TypedDict):
    tab_information: List[config.tabs.CustomTabData]


class AbsOpenSettings(abc.ABC):
    def __init__(self, settings_directory: str) -> None:
        super().__init__()
        self.settings_dir = settings_directory

    @abc.abstractmethod
    def system_open_directory(self, settings_directory: str) -> None:
        """Open the directory in os's file browser.

        Args:
            settings_directory: Path to the directory

        """

    def open(self) -> None:
        self.system_open_directory(self.settings_dir)


class UnsupportedOpenSettings(AbsOpenSettings):
    def __init__(
        self,
        settings_directory: str,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(settings_directory)
        self.parent = parent

    def system_open_directory(self, settings_directory: str) -> None:
        msg = QtWidgets.QMessageBox(parent=self.parent)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msg.setText(f"Don't know how to do that on {platform.system()}")

        msg.show()


class SettingsTab(QtWidgets.QWidget, Generic[T]):
    changes_made = QtCore.Signal()

    def data_is_modified(self) -> bool:
        raise NotImplementedError(
            f"required method, data_is_modified has not be implemented in "
            f"{self.__class__.__name__}"
        )

    def get_data(self) -> T:
        raise NotImplementedError(
            f"required method, get_data2 has not be implemented in "
            f"{self.__class__.__name__}"
        )


class SettingsDialog(QtWidgets.QDialog):
    changes_made = QtCore.Signal()
    open_settings_dir = QtCore.Signal()

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        flags: QtCore.Qt.WindowType = DEFAULT_WINDOW_FLAGS,
    ) -> None:
        super().__init__(parent, flags)

        self.setWindowTitle("Settings")
        layout = QtWidgets.QVBoxLayout(self)
        self.tabs_widget = QtWidgets.QTabWidget(self)
        layout.addWidget(self.tabs_widget)

        self.open_settings_path_button = QtWidgets.QPushButton(self)
        self.open_settings_path_button.setText("Open Config File Directory")

        self.open_settings_path_button.clicked.connect(self.open_settings_dir)

        layout.addWidget(self.open_settings_path_button)

        self.button_box = QtWidgets.QDialogButtonBox(
            cast(
                QtWidgets.QDialogButtonBox.StandardButton,
                QtWidgets.QDialogButtonBox.StandardButton.Cancel
                | QtWidgets.QDialogButtonBox.StandardButton.Ok,
            )
        )

        # Okay button will start out disabled because no changes have been made
        self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).setEnabled(False)

        self.button_box.accepted.connect(self.accept)  # type: ignore
        self.button_box.rejected.connect(self.reject)  # type: ignore
        layout.addWidget(self.button_box)

        self.setLayout(layout)
        self.setMinimumHeight(480)
        self.setMinimumWidth(600)
        self.changes_made.connect(self._handle_changes)

    @property
    def settings_tabs(self) -> Dict[str, SettingsTab]:
        settings: Dict[str, SettingsTab] = {}
        for index in range(self.tabs_widget.count()):
            settings[self.tabs_widget.tabText(index)] = typing.cast(
                SettingsTab, self.tabs_widget.widget(index)
            )

            self.tabs_widget.widget(index)
        return settings

    def _handle_changes(self) -> None:
        modified = False
        for tab in self.settings_tabs.values():
            if tab.data_is_modified():
                modified = True

        # This is an odd quirk with the current version of PySide6 (6.4.2) as
        # of this writing. For some reason, StandardButton buttons won't update
        # when called in a slot. Therefore, the buttons uses have to be
        # completely assigned  new buttons with updated attributes to see any
        # changes.
        self.button_box.setStandardButtons(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
            | QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        ok_button = self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        ok_button.setEnabled(modified)

    def add_tab(self, tab: SettingsTab, tab_name: str) -> None:
        tab.changes_made.connect(self.changes_made)
        self.tabs_widget.addTab(tab, tab_name)


class DarwinOpenSettings(AbsOpenSettings):
    def system_open_directory(self, settings_directory: str) -> None:
        subprocess.call(["/usr/bin/open", settings_directory])


class WindowsOpenSettings(AbsOpenSettings):
    def system_open_directory(self, settings_directory: str) -> None:
        # pylint: disable=no-member
        os.startfile(settings_directory)  # type: ignore[attr-defined]


DEFAULT_SETTINGS_DIR_STRATEGIES: Dict[str, Type[AbsOpenSettings]] = {
    "Darwin": DarwinOpenSettings,
    "Windows": WindowsOpenSettings,
    "Linux": UnsupportedOpenSettings
}


def open_settings_dir(
    settings_location: str,
    strategy: Optional[AbsOpenSettings] = None,
    parent: Optional[QtWidgets.QWidget] = None,
) -> None:
    if strategy is None:
        strategy_klass = DEFAULT_SETTINGS_DIR_STRATEGIES.get(
            platform.system()
        )
        if strategy_klass is None:
            strategy = UnsupportedOpenSettings(
                settings_directory=settings_location, parent=parent
            )
        else:
            strategy = strategy_klass(settings_location)

    folder_opener = OpenSettingsDirectory(strategy)
    folder_opener.open()


class PluginsTab(SettingsTab[Dict[str, List[Tuple[str, bool]]]]):
    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout()
        self.plugins_activation = PluginConfig(self)
        layout.addWidget(self.plugins_activation)
        self.setLayout(layout)
        self.plugins_activation.changes_made.connect(self.changes_made)

    def data_is_modified(self) -> bool:
        return self.plugins_activation.model.data_modified

    def get_data(self) -> Dict[str, List[Tuple[str, bool]]]:
        return self.plugins_activation.plugins()

    def load(self, settings_ini: str) -> None:
        settings = config.plugins.read_settings_file_plugins(settings_ini)
        for entry_point in metadata.entry_points(group="speedwagon.plugins"):
            active = False
            if (
                entry_point.module in settings
                and entry_point.name in settings[entry_point.module]
                and settings[entry_point.module][entry_point.name] is True
            ):
                active = True

            self.plugins_activation.model.add_entry_point(entry_point, active)


class GlobalSettingsTab(SettingsTab[config.SettingsData]):
    """Widget for editing global settings."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        flags: QtCore.Qt.WindowType = DEFAULT_WINDOW_FLAGS,
    ) -> None:
        """Create a global settings tab widget."""
        super().__init__(parent, flags)
        self.config_file: Optional[str] = None
        self._modified = False

        self._table_model: Optional[
            models.SettingsModel
        ] = models.SettingsModel()
        self._table_model.dataChanged.connect(self.changes_made)
        self.changes_made.connect(self.on_modified)
        layout = QtWidgets.QVBoxLayout(self)

        self.settings_table = QtWidgets.QTableView(self)

        self.settings_table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )

        self.settings_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.settings_table)
        self.setLayout(layout)

    def get_data(self) -> config.SettingsData:
        """Get the global settings data."""
        if self._table_model:
            return unpack_global_settings_model(self._table_model)
        return {}

    def data_is_modified(self) -> bool:
        """Get if the data has been modified since originally added."""
        return self._modified

    @property
    def model(self) -> Optional[models.SettingsModel]:
        """Get the model used in the table widget."""
        return self._table_model

    @model.setter
    def model(self, value: models.SettingsModel) -> None:
        self._table_model = value
        self.settings_table.setModel(self._table_model)

    def read_config_data(self) -> None:
        """Read configuration file."""
        if self.config_file is None:
            raise FileNotFoundError("No Configuration file set")
        if not os.path.exists(self.config_file):
            raise FileNotFoundError("Invalid Configuration file set")
        self._table_model = build_setting_qt_model(self.config_file)

        self.settings_table.setModel(self._table_model)

        self._table_model.dataChanged.connect(  # type: ignore
            self.changes_made
        )

    def load_ini_file(self, ini_file_path: str) -> None:
        """Load tab widget based on data in the given ini file."""
        self.config_file = ini_file_path
        self.read_config_data()

    def on_modified(self) -> None:
        """Set modified to true."""
        if self._table_model:
            self._modified = self._table_model.data_modified


class TabsConfigurationTab(SettingsTab[List[config.tabs.CustomTabData]]):
    """Tabs configuration widget."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        flags: QtCore.Qt.WindowType = DEFAULT_WINDOW_FLAGS,
    ) -> None:
        """Create a tab configuration widget."""
        super().__init__(parent, flags)
        self.settings_location: Optional[str] = None
        self._modified = False
        layout = QtWidgets.QVBoxLayout(self)
        self.editor = TabEditor()
        self._load_tab_data_model_strategy = (
            tab_models.TabDataModelConfigLoader(NullTabsConfig())
        )

        self.editor.changes_made.connect(self.changes_made)
        if editor_layout := self.editor.layout():
            editor_layout.setContentsMargins(0, 0, 0, 0)
        else:
            logger.error("%s has no layout", {self.editor.__class__.__name__})
        layout.addWidget(self.editor)
        self.setLayout(layout)

    @property
    def load_tab_data_model_strategy(self):
        """Get the load data model strategy."""
        return self.editor.load_tab_data_model_strategy

    @load_tab_data_model_strategy.setter
    def load_tab_data_model_strategy(self, value):
        self.editor.load_tab_data_model_strategy = value

    def data_is_modified(self) -> bool:
        """Check if data has changed since originally set."""
        return self.editor.modified

    def get_data(self) -> List[config.tabs.CustomTabData]:
        """Get the data the user entered."""
        return [
            tab for tab
            in self.editor.model.tab_information() if tab.tab_name != "All"
        ]

    def tab_config_management_strategy(self) -> AbsTabsConfigDataManagement:
        """Get the default strategy for working with custom tab YAML files."""
        return self.editor.load_tab_data_model_strategy.tabs_manager

    def load(self, strategy: tab_models.AbsLoadTabDataModelStrategy) -> None:
        """Load configuration settings."""
        strategy.load(self.editor.model)
        self.editor.selected_tab_combo_box.setCurrentIndex(0)


class ConfigWorkflowSettingsTab(SettingsTab[WorkflowsSettings]):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        self._editor = WorkflowSettingsEditor(self)
        layout.addWidget(self._editor)
        self.setLayout(layout)
        self._editor.workflow_settings_view.header().resizeSection(0, 300)
        self.model = models.WorkflowSettingsModel()
        self._editor.model = self.model

    def set_workflows(self, workflows: Iterable[Workflow]):
        self.model.clear()
        for workflow in workflows:
            self.model.add_workflow(workflow)
        self.model.reset_modified()
        self._editor.workflow_settings_view.expandAll()
        self.model.dataChanged.connect(self.changes_made)

    def data_is_modified(self) -> bool:
        return self.model.modified()

    def get_data(self) -> WorkflowsSettings:
        return self.model.results()


class SettingsBuilder:
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        self._parent = parent
        self._tabs: List[Tuple[str, SettingsTab]] = []
        self._on_save_callbacks: List[
            Callable[[SettingsDialog, Dict[str, SettingsTab]], None]
        ] = []
        self.on_open_settings_dir: Callable[
            [Optional[QtWidgets.QWidget]],
            None
        ] = lambda _: None

    def build(self) -> SettingsDialog:
        config_dialog = SettingsDialog(parent=self._parent)
        config_dialog.open_settings_dir.connect(
            lambda: self.on_open_settings_dir(config_dialog)
        )
        for name, tab in self._tabs:
            tab.setParent(config_dialog.tabs_widget)
            tab.changes_made.connect(config_dialog.changes_made)
            config_dialog.add_tab(tab, name)

        for callback_ in self._on_save_callbacks:
            config_dialog.accepted.connect(callback_)
        return config_dialog

    def add_tab(
        self,
        name: str,
        widget: SettingsTab,
    ) -> None:
        self._tabs.append((name, widget))

    def add_on_save_callback(
        self,
        on_save_callback: Callable[
            [SettingsDialog, Dict[str, SettingsTab]], None
        ],
    ) -> None:
        self._on_save_callbacks.append(on_save_callback)


class TabEditorWidgetUI(QtWidgets.QWidget):  # pylint: disable=R0903
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
        flags: QtCore.Qt.WindowType = DEFAULT_WINDOW_FLAGS,
    ) -> None:
        """Create a tab editor widget."""
        super().__init__(parent, flags)
        self.load_ui_file()

    def load_ui_file(self) -> None:
        with as_file(
            resources.files("speedwagon.frontend.qtwidgets.ui").joinpath(
                "tab_editor.ui"
            )
        ) as ui_file:
            load_ui(str(ui_file), self)


class TabEditor(TabEditorWidgetUI):
    """Widget for editing tabs."""

    all_workflows_list_view: QtWidgets.QListView
    _tabs_model: models.TabsTreeModel

    current_tab_index_changed = QtCore.Signal(QtCore.QModelIndex)
    changes_made = QtCore.Signal()

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        flags: QtCore.Qt.WindowType = DEFAULT_WINDOW_FLAGS,
    ) -> None:
        """Create a tab editor widget."""
        super().__init__(parent, flags)
        self.load_tab_data_model_strategy: \
            tab_models.TabDataModelConfigLoader = \
            tab_models.TabDataModelConfigLoader(NullTabsConfig())

        self.model = models.TabsTreeModel()
        self._user_tabs_model = QtCore.QSortFilterProxyModel()

        self._user_tabs_model.setDynamicSortFilter(True)

        self._user_tabs_model.setFilterRegularExpression("^((?!All).)*$")
        self._user_tabs_model.setSourceModel(self._tabs_model)

        self._tabs_model.dataChanged.connect(self.changes_made)  # type: ignore
        self.selected_tab_combo_box.setModel(self._user_tabs_model)

        self._tabs_file: Optional[str] = None

        self._all_workflows_model = tab_models.TabProxyModel()
        self._all_workflows_model.setSourceModel(self._tabs_model)
        self._all_workflows_model.set_source_tab("All")
        self.all_workflows_list_view.setModel(self._all_workflows_model)

        self._active_tab_workflows_model = tab_models.TabProxyModel()
        self._active_tab_workflows_model.setSourceModel(self._tabs_model)

        self.tab_workflows_list_view.setModel(self._active_tab_workflows_model)
        self.tab_workflows_list_view.setAlternatingRowColors(True)
        self.selected_tab_combo_box.currentIndexChanged.connect(
            self._handle_current_tab_index_changed
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
        self.splitter.setChildrenCollapsible(False)
        self._handle_current_tab_index_changed(0)

    def _handle_current_tab_index_changed(self, index: int) -> None:
        base_index = self._user_tabs_model.mapToSource(
            self.selected_tab_combo_box.model().index(index, 0)
        )

        self._active_tab_workflows_model.set_source_tab(
            self.model.data(base_index)
        )

        if self._active_tab_workflows_model.source_tab is None:
            self.add_items_button.setEnabled(False)
            self.remove_items_button.setEnabled(False)
            self.delete_current_tab_button.setEnabled(False)
        else:
            self.remove_items_button.setEnabled(True)
            self.delete_current_tab_button.setEnabled(True)
            self.add_items_button.setEnabled(True)
        self.current_tab_index_changed.emit(base_index)

    @property
    def modified(self) -> bool:
        """Get if editor data has been modified since originally added."""
        if self._tabs_model.data_modified is True:
            return self._tabs_model.data_modified

        return any(tab.data_modified for tab in self._tabs_model.tabs)

    @property
    def model(self) -> models.TabsTreeModel:
        """Get the model used by the editor widget."""
        return self._tabs_model

    @model.setter
    def model(self, value: models.TabsTreeModel) -> None:
        if hasattr(self, "_tabs_model"):
            self._tabs_model.dataChanged.disconnect(  # type: ignore
                self.changes_made
            )
        self._tabs_model = value
        self._tabs_model.setParent(self)
        self._tabs_model.dataChanged.connect(self.changes_made)  # type: ignore
        self.selected_tab_combo_box.setModel(self._tabs_model)

    def load_data(self) -> None:
        """Load tab data into model."""
        self.load_tab_data_model_strategy.load(self.model)
        self.all_workflows_list_view.setModel(self._all_workflows_model)
        self._all_workflows_model.set_source_tab("All")

    def set_current_tab(self, tab_name: str) -> None:
        """Set current tab."""
        new_index = self.selected_tab_combo_box.findText(tab_name)
        if new_index < 0:
            raise ValueError(f'"{tab_name}" not found in combo box')
        self.selected_tab_combo_box.setCurrentIndex(new_index)

    def _create_new_tab(self) -> None:
        while True:
            new_tab_name: str
            accepted: bool
            new_tab_name, accepted = QtWidgets.QInputDialog.getText(
                self, "Create New Tab", "Tab name"
            )

            # The user cancelled
            if not accepted:
                return

            if self._tabs_model.get_tab(new_tab_name):
                message = f'Tab named "{new_tab_name}" already exists.'
                error = QtWidgets.QMessageBox(self)
                error.setText(message)
                error.setWindowTitle("Unable to Create New Tab")
                error.setIcon(QtWidgets.QMessageBox.Icon.Critical)
                error.exec()
                continue

            self._tabs_model.append_workflow_tab(new_tab_name)
            self.set_current_tab(new_tab_name)
            self.changes_made.emit()
            return

    def _delete_tab(self) -> None:
        starting_index = self.selected_tab_combo_box.currentIndex()
        index = self._user_tabs_model.index(starting_index, 0)
        source_index = self._user_tabs_model.mapToSource(index)

        self.model.beginRemoveRows(
            source_index, source_index.row(), source_index.row()
        )

        self.selected_tab_combo_box.model().beginRemoveRows(
            index, index.row(), index.row()
        )
        self.model.removeRow(source_index.row())
        self.selected_tab_combo_box.model().endRemoveRows()
        self.model.endRemoveRows()
        self.model.modelReset.emit()
        self.changes_made.emit()

    def _add_items_to_tab(self) -> None:
        if self._active_tab_workflows_model.source_tab is None:
            logger.warning("No tab selected to add items to.")
            return
        model = cast(
            tab_models.TabProxyModel, self.tab_workflows_list_view.model()
        )
        for selected_index in self.all_workflows_list_view.selectedIndexes():
            new_workflow = self._all_workflows_model.data(
                selected_index, role=models.WorkflowClassRole
            )
            active_tab_index = self._active_tab_workflows_model.get_tab_index()
            starting_row_count = model.rowCount()

            model.add_workflow(new_workflow)
            self.model.dataChanged.emit(
                self.model.index(starting_row_count, parent=active_tab_index),
                self.model.index(model.rowCount(), parent=active_tab_index),
            )
        model.sort(0)

    def _remove_items(self) -> None:
        model = cast(
            models.WorkflowListProxyModel, self.tab_workflows_list_view.model()
        )
        items_to_remove = [
            i.data(role=models.WorkflowClassRole)
            for i in self.tab_workflows_list_view.selectedIndexes()
        ]

        for item in items_to_remove:
            model.remove_workflow(item)
        self.changes_made.emit()

    def set_all_workflows(self) -> None:
        """Set up all workflows."""
        self.all_workflows_list_view.setModel(self._all_workflows_model)

    @property
    def current_tab(self) -> QtWidgets.QWidget:
        """Get current tab widget."""
        return self.selected_tab_combo_box.currentData()


class OpenSettingsDirectory:
    def __init__(self, strategy: AbsOpenSettings) -> None:
        self.strategy = strategy

    def system_open_directory(self, settings_directory: str) -> None:
        self.strategy.system_open_directory(settings_directory)

    def open(self) -> None:
        self.strategy.open()
