import os
import platform

from PyQt5 import QtWidgets, QtCore  # type: ignore

from speedwagon import config, models, tabs, job
from speedwagon.config import build_setting_model
from speedwagon.ui import tab_editor_ui


class SettingsDialog(QtWidgets.QDialog):

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.settings_location = None

        self.setWindowTitle("Settings")
        self.layout = QtWidgets.QVBoxLayout(self)
        self.tabsWidget = QtWidgets.QTabWidget(self)
        self.layout.addWidget(self.tabsWidget)

        self.open_settings_path_button = QtWidgets.QPushButton(self)
        self.open_settings_path_button.setText("Open Config File Directory")
        self.open_settings_path_button.clicked.connect(self.open_settings_dir)

        self.layout.addWidget(self.open_settings_path_button)

        self._button_box = \
            QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel
                                       | QtWidgets.QDialogButtonBox.Ok)

        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        self.layout.addWidget(self._button_box)

        self.setLayout(self.layout)
        self.setFixedHeight(480)
        self.setFixedWidth(600)

    def add_tab(self, tab, tab_name):
        self.tabsWidget.addTab(tab, tab_name)

    def open_settings_dir(self):
        if self.settings_location is not None:
            print("Opening")
            if platform.system() == "Windows":
                os.startfile(self.settings_location)
            elif platform.system() == "Darwin":
                os.system("open {}".format(self.settings_location))
            else:
                msg = QtWidgets.QMessageBox(parent=self)
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setText("Don't know how to do that on {}".format(platform.system()))
                msg.show()


class GlobalSettingsTab(QtWidgets.QWidget):

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.config_file = None
        self._modified = False

        self.layout = QtWidgets.QVBoxLayout(self)

        self.settings_table = QtWidgets.QTableView(self)

        self.settings_table.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)

        self.settings_table.horizontalHeader().setStretchLastSection(True)

        self.layout.addWidget(self.settings_table)

    def read_config_data(self):
        if self.config_file is None:
            raise FileNotFoundError("No Configuration file set")
        if not os.path.exists(self.config_file):
            raise FileNotFoundError("Invalid Configuration file set")

        self.settings_table.setModel(build_setting_model(self.config_file))
        self.settings_table.model().dataChanged.connect(self.on_modified)

    def on_modified(self):
        self._modified = True

    def on_okay(self):
        if self._modified:
            print("Saving changes")
            data = config.serialize_settings_model(self.settings_table.model())

            with open(self.config_file, "w") as fw:
                fw.write(data)

            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle("Saved changes")
            msg_box.setText("Please restart changes to take effect")
            msg_box.exec()


class TabsConfigurationTab(QtWidgets.QWidget):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.settings_location = None
        self._modified = False

        self.layout = QtWidgets.QVBoxLayout(self)
        self.editor = TabEditor()
        self.editor.layout().setContentsMargins(0, 0, 0, 0)

        self.layout.addWidget(self.editor)

    def on_okay(self):
        if self.editor.modified is True:
            print(f"Saving changes to {self.settings_location}")
            tabs.write_tabs_yaml(
                self.settings_location,
                tabs.extract_tab_information(
                    self.editor.selectedTabComboBox.model())
            )

            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle("Saved changes to tabs files")
            msg_box.setText("Please restart changes to take effect")
            msg_box.exec()

    def load(self):
        print(f"loading {self.settings_location}")
        self.editor.tabs_file = self.settings_location
        workflows = job.available_workflows()
        self.editor.set_all_workflows(workflows)


class TabEditor(QtWidgets.QWidget, tab_editor_ui.Ui_Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self._tabs_file = None

        self._tabs_model = models.TabsModel()

        self._all_workflows_model = models.WorkflowListModel2()
        self._active_tab_worksflows_model = models.WorkflowListModel2()

        self.tabWorkflowsListView.setModel(self._active_tab_worksflows_model)

        self.selectedTabComboBox.setModel(self._tabs_model)

        self.selectedTabComboBox.currentIndexChanged.connect(self._changed_tab)

        self.newTabButton.clicked.connect(self._create_new_tab)

        self.deleteCurrentTabButton.clicked.connect(self._delete_tab)
        self.addItemsButton.clicked.connect(self._add_items_to_tab)
        self.removeItemsButton.clicked.connect(self._remove_items)
        self._tabs_model.dataChanged.connect(self.on_modified)
        self.modified = False
        self.splitter.setChildrenCollapsible(False)

    def on_modified(self):
        self.modified = True

    @property
    def tabs_file(self):
        return self._tabs_file

    @tabs_file.setter
    def tabs_file(self, value):

        for tab in tabs.read_tabs_yaml(value):

            tab.workflows_model.dataChanged.connect(self.on_modified)
            self._tabs_model.add_tab(tab)
        self.selectedTabComboBox.setCurrentIndex(0)
        self._tabs_file = value
        self.modified = False

    def _changed_tab(self, tab):
        model = self.selectedTabComboBox.model()
        index = model.index(tab)
        if index.isValid():
            data = model.data(index, role=QtCore.Qt.UserRole)
            self.tabWorkflowsListView.setModel(data.workflows_model)
        else:
            self.tabWorkflowsListView.setModel(models.WorkflowListModel2())

    def _create_new_tab(self):
        while True:
            new_tab_name, accepted = QtWidgets.QInputDialog.getText(
                self.parent(), "Create New Tab", "Tab name")

            # The user cancelled
            if not accepted:
                return

            if new_tab_name in self._tabs_model:
                message = f"Tab named \"{new_tab_name}\" already exists."
                error = QtWidgets.QMessageBox(self)
                error.setText(message)
                error.setWindowTitle("Unable to Create New Tab")
                error.setIcon(QtWidgets.QMessageBox.Critical)
                error.exec()
                continue

            new_tab = tabs.TabData(new_tab_name, models.WorkflowListModel2())
            self._tabs_model.add_tab(new_tab)
            new_index = self.selectedTabComboBox.findText(new_tab_name)
            self.selectedTabComboBox.setCurrentIndex(new_index)
            return

    def _delete_tab(self):
        data = self.selectedTabComboBox.currentData()
        model: None = self.selectedTabComboBox.model()
        model -= data

    def _add_items_to_tab(self):
        model = self.tabWorkflowsListView.model()
        for i in self.allWorkflowsListView.selectedIndexes():
            new_workflow = i.data(role=QtCore.Qt.UserRole)
            model.add_workflow(new_workflow)
        model.sort()

    def _remove_items(self):
        model = self.tabWorkflowsListView.model()
        items_to_remove = [
            i.data(role=QtCore.Qt.UserRole)
            for i in self.tabWorkflowsListView.selectedIndexes()
        ]

        for item in items_to_remove:
            model.remove_workflow(item)
        model.sort()

    def set_all_workflows(self, workflows):
        for k, v in workflows.items():
            self._all_workflows_model.add_workflow(v)
        self._all_workflows_model.sort()
        self.allWorkflowsListView.setModel(self._all_workflows_model)

    @property
    def current_tab(self):
        return self.selectedTabComboBox.currentData()
