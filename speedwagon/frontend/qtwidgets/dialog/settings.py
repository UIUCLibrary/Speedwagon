"""Configuration settings."""
import abc
import configparser
import io
import os
import platform
import typing
from typing import Optional, Dict, cast, Type, List, Tuple
import sys

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
    OpenSettingsDirectory, \
    ConfigLoader, \
    SettingsData, \
    PluginDataType

from speedwagon import job
from speedwagon.frontend import qtwidgets
from speedwagon.frontend.qtwidgets.widgets import PluginConfig
from speedwagon.frontend.qtwidgets import models, tabs

if sys.version_info < (3, 10):  # pragma: no cover
    import importlib_metadata as metadata
else:
    from importlib import metadata

__all__ = ['GlobalSettingsTab', 'TabsConfigurationTab', 'TabEditor']

SaveCallback = typing.Callable[["SettingsTab"], Dict[str, typing.Any]]


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


class SettingsTab(QtWidgets.QWidget):
    changes_made = QtCore.Signal()

    def data_is_modified(self) -> bool:
        raise NotImplementedError(
            f"required method, data_is_modified has not be implemented in "
            f"{self.__class__.__name__}"
        )

    def get_data(self) -> Optional[Dict[str, typing.Any]]:
        return None


class SettingsDialog(QtWidgets.QDialog):
    changes_made = QtCore.Signal()

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

        self.button_box = \
            QtWidgets.QDialogButtonBox(
                cast(
                    QtWidgets.QDialogButtonBox.StandardButton,
                    QtWidgets.QDialogButtonBox.StandardButton.Cancel |
                    QtWidgets.QDialogButtonBox.StandardButton.Ok
                )
            )

        # Okay button will start out disabled because no changes have been made
        self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).setEnabled(False)

        self.button_box.accepted.connect(  # type: ignore
            self.accept
        )
        self.button_box.rejected.connect(  # type: ignore
            self.reject
        )
        layout.addWidget(self.button_box)

        self.setLayout(layout)
        self.setFixedHeight(480)
        self.setFixedWidth(600)
        self.changes_made.connect(self._handle_changes)

    @property
    def settings_tabs(self) -> Dict[str, SettingsTab]:
        settings: Dict[str, SettingsTab] = {}
        for index in range(self.tabs_widget.count()):
            settings[self.tabs_widget.tabText(index)] = \
                typing.cast(
                    SettingsTab,
                    self.tabs_widget.widget(index)
                )

            self.tabs_widget.widget(index)
        return settings

    def _handle_changes(self):
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
            QtWidgets.QDialogButtonBox.StandardButton.Cancel |
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        ok_button = self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        ok_button.setEnabled(modified)

    def add_tab(self, tab: SettingsTab, tab_name: str) -> None:
        tab.changes_made.connect(self.changes_made)
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


class PluginModelLoader(abc.ABC):  # pylint: disable=too-few-public-methods
    @abc.abstractmethod
    def load_plugins_into_model(
            self,
            model: models.PluginActivationModel
    ) -> None:
        """Load plugins into the model."""


class EntrypointsPluginModelLoader(PluginModelLoader):
    entrypoint_group_name = 'speedwagon.plugins'

    def __init__(self, config_file: str) -> None:
        super().__init__()
        self.config_file = config_file

    @classmethod
    def plugin_entry_points(cls) -> metadata.EntryPoints:
        return metadata.entry_points(
            group=cls.entrypoint_group_name
        )

    def is_entry_point_active(self, entry_point: metadata.EntryPoint) -> bool:
        settings = ConfigLoader.read_settings_file_plugins(self.config_file)
        return (
            entry_point.module in settings
            and entry_point.name in settings[entry_point.module]
            and settings[entry_point.module][entry_point.name] is True
        )

    def load_plugins_into_model(
            self,
            model: models.PluginActivationModel
    ) -> None:
        for entry_point in self.plugin_entry_points():
            model.add_entry_point(
                entry_point, self.is_entry_point_active(entry_point)
            )


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

    def get_data(self) -> Optional[Dict[str, typing.Any]]:
        return {
            "enabled_plugins": self.plugins_activation.enabled_plugins()
        }

    def load(self, settings_ini: str) -> None:
        model_loader = EntrypointsPluginModelLoader(settings_ini)
        model_loader.load_plugins_into_model(self.plugins_activation.model)


class GlobalSettingsTab(SettingsTab):
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

        self._table_model: Optional[models.SettingsModel] = \
            models.SettingsModel()
        self._table_model.dataChanged.connect(self.changes_made)
        self.changes_made.connect(self.on_modified)
        layout = QtWidgets.QVBoxLayout(self)

        self.settings_table = QtWidgets.QTableView(self)

        self.settings_table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self.settings_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.settings_table)
        self.setLayout(layout)

    def get_data(self) -> Optional[SettingsData]:
        """Get the global settings data."""
        if self._table_model:
            return models.unpack_global_settings_model(self._table_model)
        return None

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
        self._table_model = models.build_setting_qt_model(self.config_file)
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
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0)
    ) -> None:
        """Create a tab configuration widget."""
        super().__init__(parent, flags)
        self.settings_location: Optional[str] = None
        self._modified = False
        layout = QtWidgets.QVBoxLayout(self)
        self.editor = TabEditor()
        self.editor.changed_made.connect(self.changes_made)
        self.editor.layout().setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        self.setLayout(layout)

    def data_is_modified(self) -> bool:
        """Check if data has changed since originally set."""
        return self.editor.modified

    def get_data(self) -> Optional[Dict[str, typing.Any]]:
        """Get the data the user entered."""
        data = qtwidgets.tabs.extract_tab_information(
            cast(
                models.TabsModel,
                self.editor.selected_tab_combo_box.model()
            )
        )
        return {"tab_information": data}

    def on_okay(self) -> None:
        """Execute when a user selects okay."""
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

    def load(self, yaml_file: str) -> None:
        """Load configuration settings."""
        self.editor.tabs_file = yaml_file

        workflows = job.available_workflows()
        self.editor.set_all_workflows(workflows)


class AbsConfigSaver(abc.ABC):  # pylint: disable=too-few-public-methods
    def __init__(self, parent: Optional[QtWidgets.QWidget]) -> None:
        super().__init__()
        self.parent = parent

    @abc.abstractmethod
    def save(self, tab_widgets: Dict[str, SettingsTab]) -> None:
        """Save data to a file."""


class ConfigSaver(AbsConfigSaver):

    def __init__(self, parent: Optional[QtWidgets.QWidget]) -> None:
        super().__init__(parent)
        self.config_file_path: Optional[str] = None
        self.tabs_yaml_path: Optional[str] = None
        self._success_callbacks: List[
            typing.Callable[[Optional[QtWidgets.QWidget]], None]
        ] = []

    def set_notify_success(
            self,
            callback: typing.Callable[[Optional[QtWidgets.QWidget]], None]
    ) -> None:
        self._success_callbacks.append(callback)

    def write_config_file(self, data: str) -> None:
        if self.config_file_path:
            with open(
                    self.config_file_path,
                    "w",
                    encoding="utf-8"
            ) as write_pointer:
                write_pointer.write(data)

    def write_tabs_yml(self, data: str) -> None:
        if self.tabs_yaml_path:
            with open(
                    self.tabs_yaml_path,
                    "w",
                    encoding="utf-8"
            ) as write_pointer:
                write_pointer.write(data)

    @staticmethod
    def _get_global_data(
            tab_widgets: Dict[str, SettingsTab]
    ) -> SettingsData:
        global_data: SettingsData = {}

        global_settings_tab: Optional[SettingsTab] = \
            tab_widgets.get("Global Settings")

        if global_settings_tab:
            global_data = {
                **global_data,
                **(global_settings_tab.get_data() or {})
            }
        return global_data

    def save(self, tab_widgets: Dict[str, SettingsTab]) -> None:
        config_data = configparser.ConfigParser()
        config_data["GLOBAL"] = self._make_config_parsable(
            self._get_global_data(tab_widgets)
        )

        for key, value in self._prepare_plugin_info(tab_widgets).items():
            config_data[key] = self._make_config_parsable(value)

        with io.StringIO() as string_writer:
            config_data.write(string_writer)
            self.write_config_file(string_writer.getvalue())
        self.write_tabs_yml(self._get_tabs_yaml(tab_widgets))
        self.on_success()

    def on_success(self) -> None:
        for callback in self._success_callbacks:
            callback(self.parent)

    @staticmethod
    def _get_tabs_yaml(tab_widgets: Dict[str, SettingsTab]) -> str:
        tabs_editor_widget = tab_widgets.get('Tabs')
        if not tabs_editor_widget:
            return ''
        data = tabs_editor_widget.get_data()
        if data:
            return tabs.serialize_tabs_yaml(data.get('tab_information', []))
        return ''

    @staticmethod
    def _prepare_plugin_info(
            tab_widgets: Dict[str, SettingsTab]
    ) -> PluginDataType:
        plugin_settings = cast(
            Optional[PluginsTab],
            tab_widgets.get("Plugins")
        )
        plugin_data = {}
        if plugin_settings:
            data = plugin_settings.get_data()
            if data:
                plugins = data['enabled_plugins']
                for plugin_source in plugins:
                    plugin_key = f"PLUGINS.{plugin_source}"
                    plugin_data[plugin_key] = {
                        plugin_name: True for plugin_name in
                        plugins[plugin_source]
                    }
        return plugin_data

    @staticmethod
    def _make_config_parsable(
            source_data: typing.Union[Dict[str, bool], SettingsData]
    ) -> Dict[str, str]:
        return {
            key: str(value)
            for key, value in source_data.items()
        }


class SettingsBuilder2:
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        self._parent = parent
        self._tabs: List[Tuple[str, SettingsTab]] = []
        self._on_save_callback = None
        self._save_strategy: Optional[AbsConfigSaver] = None

    def build(self) -> SettingsDialog:
        config_dialog = SettingsDialog(parent=self._parent)
        for name, tab in self._tabs:
            tab.setParent(config_dialog.tabs_widget)
            tab.changes_made.connect(config_dialog.changes_made)
            config_dialog.add_tab(tab, name)

        if self._save_strategy is not None:
            config_dialog.accepted.connect(  # type: ignore
                lambda callback=self._on_save_callback:
                self._save_strategy.save(
                    config_dialog.settings_tabs
                )
            )

        if self._on_save_callback is not None:
            config_dialog.accepted.connect(
                lambda callback=self._on_save_callback: callback(
                    config_dialog,
                    config_dialog.settings_tabs
                )
            )
        return config_dialog

    def add_tab(
            self,
            name: str,
            widget: SettingsTab,
    ) -> None:
        self._tabs.append((name, widget))

    def set_saver_strategy(self, value: AbsConfigSaver) -> None:
        self._save_strategy = value

    def add_on_save_callback(self, on_save_callback) -> None:
        self._on_save_callback = on_save_callback


class TabEditorWidget(QtWidgets.QWidget):  # pylint: disable=R0903
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

    all_workflows_list_view: QtWidgets.QListView
    changed_made = QtCore.Signal()

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0)
    ) -> None:
        """Create a tab editor widget."""
        super().__init__(parent, flags)
        self._tabs_model = models.TabsModel()

        self._tabs_model.dataChanged.connect(  # type: ignore
            self.changed_made
        )
        self.selected_tab_combo_box.setModel(self._tabs_model)

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
        self.splitter.setChildrenCollapsible(False)

    @property
    def modified(self):
        """Get if editor data has been modified since originally added."""
        if self._tabs_model.data_modified is True:
            return self._tabs_model.data_modified
        for tab in self._tabs_model.tabs:
            if tab.workflows_model.data_modified:
                return True
        return False

    @property
    def model(self) -> models.TabsModel:
        """Get the model used by the editor widget."""
        return self._tabs_model

    @model.setter
    def model(self, value: models.TabsModel) -> None:
        if self._tabs_model:
            self._tabs_model.dataChanged.disconnect(  # type: ignore
                self.changed_made
            )
        self._tabs_model = value
        self._tabs_model.dataChanged.connect(  # type: ignore
            self.changed_made
        )
        self.selected_tab_combo_box.setModel(self._tabs_model)

    def set_current_tab(self, tab_name: str) -> None:
        """Set current tab."""
        new_index = self.selected_tab_combo_box.findText(tab_name)
        self.selected_tab_combo_box.setCurrentIndex(new_index)

    @property
    def tabs_file(self) -> Optional[str]:
        """Get tabs file used."""
        return self._tabs_file

    @tabs_file.setter
    def tabs_file(self, value: str) -> None:

        for tab in qtwidgets.tabs.read_tabs_yaml(value):
            self._tabs_model.add_tab(tab)
        self._tabs_model.reset_modified()
        self.selected_tab_combo_box.setCurrentIndex(0)
        self._tabs_file = value

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

            if new_tab_name in self._tabs_model:
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

            self._tabs_model.add_tab(new_tab)
            self.set_current_tab(new_tab_name)
            self.changed_made.emit()
            return

    def _delete_tab(self) -> None:
        data = self.selected_tab_combo_box.currentData()
        model = cast(models.TabsModel, self.selected_tab_combo_box.model())
        model.remove_tab(data)
        self.changed_made.emit()

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
        new_model = models.WorkflowListModel2.init_from_data(
            workflows=workflows.values()
        )
        new_model.sort(0)
        self._all_workflows_model = new_model
        self.all_workflows_list_view.setModel(self._all_workflows_model)

    @property
    def current_tab(self) -> QtWidgets.QWidget:
        """Get current tab widget."""
        return self.selected_tab_combo_box.currentData()
