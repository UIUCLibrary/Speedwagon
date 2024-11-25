"""Configuration settings."""
from __future__ import annotations
import abc
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
    Mapping,
    TYPE_CHECKING,
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
)
from speedwagon.frontend.qtwidgets import models


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


class SettingsTab(QtWidgets.QWidget):
    changes_made = QtCore.Signal()

    def data_is_modified(self) -> bool:
        raise NotImplementedError(
            f"required method, data_is_modified has not be implemented in "
            f"{self.__class__.__name__}"
        )

    def get_data(self) -> Mapping[str, typing.Any]:
        return {}


class SettingsDialog(QtWidgets.QDialog):
    changes_made = QtCore.Signal()

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        flags: QtCore.Qt.WindowType = DEFAULT_WINDOW_FLAGS,
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
        # This needs a lambda to delay execution. Otherwise, Qt might segfault
        # when it tries to open the dialog box
        self.open_settings_path_button.clicked.connect(  # type: ignore
            lambda: self.open_settings_dir()
        )
        # pylint: enable=unnecessary-lambda

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

    def open_settings_dir(
        self, strategy: Optional[AbsOpenSettings] = None
    ) -> None:
        if self.settings_location is None:
            return

        strategies: Dict[str, AbsOpenSettings] = {
            "Darwin": DarwinOpenSettings(self.settings_location),
            "Windows": WindowsOpenSettings(self.settings_location),
        }

        folder_opener = OpenSettingsDirectory(
            strategy
            if strategy is not None
            else strategies.get(
                platform.system(),
                UnsupportedOpenSettings(
                    settings_directory=self.settings_location, parent=self
                ),
            )
        )
        folder_opener.open()


class PluginsTab(SettingsTab):
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

    def get_data(self) -> Dict[str, typing.Any]:
        return {"enabled_plugins": self.plugins_activation.enabled_plugins()}

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


class GlobalSettingsTab(SettingsTab):
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


class TabsConfigurationTab(SettingsTab):
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
        self.editor.changes_made.connect(self.changes_made)
        self.editor.layout().setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        self.setLayout(layout)

    def data_is_modified(self) -> bool:
        """Check if data has changed since originally set."""
        return self.editor.modified

    def get_data(self) -> TabsSettingsData:
        """Get the data the user entered."""
        return {"tab_information": self.editor.model.tab_information()}

    def tab_config_management_strategy(self) -> AbsTabsConfigDataManagement:
        """Get the default strategy for working with custom tab YAML files."""
        if self.settings_location is None:
            raise RuntimeError("settings_location not set")
        return config.tabs.CustomTabsYamlConfig(self.settings_location)

    def on_okay(self) -> None:
        """Execute when a user selects okay."""
        if self.settings_location is None:
            msg = QtWidgets.QMessageBox(parent=self)
            msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            msg.setText("Unable to save settings. No settings location set")
            msg.exec()
            return
        print(f"Saving changes to {self.settings_location}")
        yaml_tab_config = self.tab_config_management_strategy()
        yaml_tab_config.save(
            list(
                filter(
                    lambda tab: tab.tab_name != "All",
                    self.editor.model.tab_information(),
                )
            )
        )

        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("Saved changes to tabs files")
        msg_box.setText("Please restart changes to take effect")
        msg_box.exec()

    def load(self, strategy: tab_models.AbsLoadTabDataModelStrategy) -> None:
        """Load configuration settings."""
        strategy.load(self.editor.model)
        self.editor.selected_tab_combo_box.setCurrentIndex(0)


class ConfigWorkflowSettingsTab(SettingsTab):
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

    def get_data(self) -> Dict[str, typing.Any]:
        return {"workflow settings": self.model.results()}


class AbsConfigSaver2(abc.ABC):  # pylint: disable=too-few-public-methods
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__()
        self.parent = parent

    @abc.abstractmethod
    def save(self) -> None:
        """Save to file."""


class AbsSaveStrategy(abc.ABC):
    @abc.abstractmethod
    def write_file(self, data: str, file: str) -> None:
        """Write data to a file."""

    @abc.abstractmethod
    def serialize_data(self) -> str:
        """Serialize data into a string."""


class AbsConfigSaverCallbacks(AbsConfigSaver2, abc.ABC):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._success_callbacks: List[
            Callable[[Optional[QtWidgets.QWidget]], None]
        ] = []

    def add_success_call_back(
        self, callback: typing.Callable[[Optional[QtWidgets.QWidget]], None]
    ) -> None:
        self._success_callbacks.append(callback)

    def notify_success(self):
        for callback in self._success_callbacks:
            callback(self.parent)


class MultiSaver(AbsConfigSaverCallbacks):
    def __init__(
        self,
        config_savers: Optional[List[AbsConfigSaver2]] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.config_savers: list[AbsConfigSaver2] = config_savers or []

    def save(self):
        for saver in self.config_savers:
            saver.save()
        self.notify_success()


class AbsConfigSaver(abc.ABC):  # pylint: disable=too-few-public-methods
    def __init__(self, parent: Optional[QtWidgets.QWidget]) -> None:
        super().__init__()
        self.parent = parent

    @abc.abstractmethod
    def save(self, tab_widgets: Dict[str, SettingsTab]) -> None:
        """Save data to a file."""


class ConfigFileSaver(AbsConfigSaverCallbacks):
    def __init__(
        self,
        save_strategy: AbsSaveStrategy,
        file_path: str,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.save_strategy = save_strategy
        self.file_path = file_path

    def save(self) -> None:
        data = self.save_strategy.serialize_data()
        self.save_strategy.write_file(data, self.file_path)


class SaveStrategy(AbsSaveStrategy, abc.ABC):
    def write_file(self, data: str, file: str) -> None:
        with open(file, "w", encoding="utf8") as file_handel:
            file_handel.write(data)


class SettingsTabSaveStrategy(SaveStrategy):
    def __init__(
        self,
        settings_tab_widget: SettingsTab,
        serialization_function: Callable[[SettingsTab], str],
    ) -> None:
        self.widget = settings_tab_widget
        self.serialization_function = serialization_function

    def serialize_data(self) -> str:
        return self.serialization_function(self.widget)


class ConfigSaver(AbsConfigSaver):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.tabs_yaml_path: Optional[str] = None
        self._success_callbacks: List[
            typing.Callable[[Optional[QtWidgets.QWidget]], None]
        ] = []
        self.file_manager: Optional[config.IniConfigManager] = None

    @property
    def config_file_path(self) -> Optional[str]:
        return (
            None
            if self.file_manager is None
            else self.file_manager.config_file
        )

    @config_file_path.setter
    def config_file_path(self, value: str) -> None:
        self.file_manager = config.IniConfigManager(value)

    def add_success_call_back(
        self, callback: typing.Callable[[Optional[QtWidgets.QWidget]], None]
    ) -> None:
        self._success_callbacks.append(callback)

    @staticmethod
    def _get_global_data(
        tab_widgets: Dict[str, SettingsTab]
    ) -> config.SettingsData:
        global_data: config.SettingsData = {}

        global_settings_tab: Optional[SettingsTab] = tab_widgets.get(
            "Global Settings"
        )

        if global_settings_tab:
            global_data = {
                **global_data,
                **(global_settings_tab.get_data() or {}),
            }
        return global_data

    def get_tab_config_strategy(self) -> AbsTabsConfigDataManagement:
        if not self.tabs_yaml_path:
            raise RuntimeError("ConfigSaver.tabs_yaml_path not set")
        return config.tabs.CustomTabsYamlConfig(self.tabs_yaml_path)

    def _save_tabs(self, editor: TabEditor) -> None:
        yaml_config = self.get_tab_config_strategy()
        yaml_config.save(
            list(
                filter(
                    lambda tab: tab.tab_name != "All",
                    editor.model.tab_information(),
                )
            )
        )

    def _save_config(self, tab_widgets: Dict[str, SettingsTab]) -> None:
        if self.file_manager is None:
            return
        config_data = {
            "GLOBAL": self._make_config_parsable(
                self._get_global_data(tab_widgets)
            )
        }
        self.file_manager.save(config_data)

    def save(self, tab_widgets: Dict[str, SettingsTab]) -> None:
        self._save_config(tab_widgets)
        tabs_tab = cast(TabsConfigurationTab, tab_widgets["Tabs"])
        self._save_tabs(tabs_tab.editor)
        self.on_success()

    def on_success(self) -> None:
        for callback in self._success_callbacks:
            callback(self.parent)

    @staticmethod
    def _make_config_parsable(
        source_data: typing.Union[Dict[str, bool], config.SettingsData]
    ) -> config.SettingsData:
        return {key: str(value) for key, value in source_data.items()}


class SettingsBuilder2:
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        self._parent = parent
        self._tabs: List[Tuple[str, SettingsTab]] = []
        self._on_save_callback: Optional[
            Callable[[SettingsDialog, Dict[str, SettingsTab]], None]
        ] = None
        self._save_strategy: Optional[AbsConfigSaverCallbacks] = None
        self.app_data_dir: Optional[str] = None

    def build(self) -> SettingsDialog:
        config_dialog = SettingsDialog(parent=self._parent)
        if self.app_data_dir:
            config_dialog.settings_location = self.app_data_dir
        for name, tab in self._tabs:
            tab.setParent(config_dialog.tabs_widget)
            tab.changes_made.connect(config_dialog.changes_made)
            config_dialog.add_tab(tab, name)

        if self._save_strategy is not None:
            config_dialog.accepted.connect(  # type: ignore
                self._save_strategy.save
            )

        if self._on_save_callback is not None:
            config_dialog.accepted.connect(
                lambda callback=self._on_save_callback: callback(
                    config_dialog, config_dialog.settings_tabs
                )
            )
        return config_dialog

    def add_tab(
        self,
        name: str,
        widget: SettingsTab,
    ) -> None:
        self._tabs.append((name, widget))

    def set_saver_strategy(self, value: AbsConfigSaverCallbacks) -> None:
        self._save_strategy = value

    def add_on_save_callback(
        self,
        on_save_callback: Callable[
            [SettingsDialog, Dict[str, SettingsTab]], None
        ],
    ) -> None:
        self._on_save_callback = on_save_callback


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
            tab_models.AbsLoadTabDataModelStrategy = \
            tab_models.TabDataModelConfigLoader()

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

    def _handle_current_tab_index_changed(self, index: int) -> None:
        base_index = self._user_tabs_model.mapToSource(
            self.selected_tab_combo_box.model().index(index, 0)
        )

        self._active_tab_workflows_model.set_source_tab(
            self.model.data(base_index)
        )
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
                self.parentWidget(), "Create New Tab", "Tab name"
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


class DarwinOpenSettings(AbsOpenSettings):
    def system_open_directory(self, settings_directory: str) -> None:
        subprocess.call(["/usr/bin/open", settings_directory])


class WindowsOpenSettings(AbsOpenSettings):
    def system_open_directory(self, settings_directory: str) -> None:
        # pylint: disable=no-member
        os.startfile(settings_directory)  # type: ignore[attr-defined]


class OpenSettingsDirectory:
    def __init__(self, strategy: AbsOpenSettings) -> None:
        self.strategy = strategy

    def system_open_directory(self, settings_directory: str) -> None:
        self.strategy.system_open_directory(settings_directory)

    def open(self) -> None:
        self.strategy.open()
