import os

from PyQt5 import QtWidgets, QtCore

from speedwagon import config
from speedwagon.config import build_setting_model


class PlaceHolderTab(QtWidgets.QWidget):

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.notification_information = QtWidgets.QLabel()

        # self.notification_information.setMaximumWidth(300)
        self.notification_information.setWordWrap(True)
        self.layout = QtWidgets.QGridLayout(self)
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.layout.addWidget(self.notification_information, 0, 0)
        self.open_file_button = QtWidgets.QPushButton()
        self.open_file_button.setText("Open")
        self.layout.addWidget(self.open_file_button, 0, 1)
        self.setLayout(self.layout)


class SettingsPlaceholderTabsTab(PlaceHolderTab):

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.notification_information.setText(
            "Configuration tabs can be only be made by editing "
            "tabs.yaml file.")

        self.open_file_button.clicked.connect(self.open_yaml_file)
        self.settings_location = None

    def open_yaml_file(self):
        if self.settings_location is None:
            print("No settings found")
            return
        else:
            print(self.settings_location)
        os.startfile(self.settings_location)

        QtWidgets.QMessageBox.information(
            self, "Info",
            "Opening {}\n"
            "Note: Please quit and restart Speedwagon to apply "
            "changes".format(self.settings_location))


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
        self.setFixedHeight(350)
        self.setFixedWidth(500)

    def add_tab(self, tab, tab_name):
        self.tabsWidget.addTab(tab, tab_name)

    def open_settings_dir(self):

        if self.settings_location is not None:
            print("Opening")
            os.startfile(self.settings_location)


class GlobalSettingsTab(QtWidgets.QWidget):

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.config_file = None
        self._modified = False
        # self.settings = SettingsEditor(self)

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
