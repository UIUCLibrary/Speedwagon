import email
import os
from typing import Collection

import pkg_resources
from PyQt5 import QtWidgets, QtCore

import speedwagon


class ErrorDialogBox(QtWidgets.QMessageBox):
    """Dialog box to use for Error Messages causes while trying to run a job
    in Speedwagon"""

    def __init__(self, *__args):
        super().__init__(*__args)
        self.setIcon(QtWidgets.QMessageBox.Critical)
        self.setStandardButtons(QtWidgets.QMessageBox.Abort)
        self.setSizeGripEnabled(True)

    def event(self, e):
        # Allow the dialog box to be resized so that the additional information
        # can be readable

        result = QtWidgets.QMessageBox.event(self, e)

        self.setMinimumHeight(100)
        self.setMaximumHeight(1024)
        self.setMinimumWidth(250)
        self.setMaximumWidth(1000)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        textEdit = self.findChild(QtWidgets.QTextEdit)
        if textEdit is not None:
            textEdit.setMinimumHeight(100)
            textEdit.setMaximumHeight(16777215)
            textEdit.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding)

        return result


class WorkProgressBar(QtWidgets.QProgressDialog):
    """Use this for showing progress """

    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)

    def __init__(self, *args):
        super().__init__(*args)
        self.setModal(True)
        self.setMinimumHeight(100)
        self.setMinimumWidth(250)
        self._label = QtWidgets.QLabel()
        self._label.setWordWrap(True)
        self.setLabel(self._label)

    def resizeEvent(self, QResizeEvent):
        super().resizeEvent(QResizeEvent)
        self._label.setMaximumWidth(self.width())
        self.setMinimumHeight(self._label.sizeHint().height() + 75)


def about_dialog_box(parent):
    try:
        distribution = speedwagon.get_project_distribution()
        metadata = dict(
            email.message_from_string(
                distribution.get_metadata(distribution.PKG_INFO)))
        summary = metadata['Summary']
        message = f"{speedwagon.__name__.title()}: {speedwagon.__version__}" \
                  f"\n" \
                  f"\n" \
                  f"{summary}"

    except pkg_resources.DistributionNotFound:
                message = \
                    f"{speedwagon.__name__.title()}: {speedwagon.__version__}"

    QtWidgets.QMessageBox.about(parent, "About", message)


class SystemInfoDialog(QtWidgets.QDialog):

    def __init__(self, parent: QtWidgets.QWidget, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)

        self.setWindowTitle("System Information")
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        self.installed_packages_title = QtWidgets.QLabel(parent)
        self.installed_packages_title.setText("Installed Python Packages:")

        installed_python_packages = self.get_installed_packages()

        self.installed_packages_widget = QtWidgets.QListWidget(parent)
        self.installed_packages_widget.addItems(installed_python_packages)

        layout.addWidget(self.installed_packages_title)
        layout.addWidget(self.installed_packages_widget)

        self._button_box = \
            QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)

        self._button_box.accepted.connect(self.accept)
        layout.addWidget(self._button_box)

    @staticmethod
    def get_installed_packages() -> Collection:

        installed_python_packages = \
            (str(pkg) for pkg in pkg_resources.working_set)

        return sorted(installed_python_packages, key=lambda x: str(x).lower())


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


class SettingsPlaceholderInformationTab(PlaceHolderTab):

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.settings_location = None

        self.notification_information.setText(
            "Configuration currently can be only be made by editing the "
            "program config file.")

        self.open_file_button.clicked.connect(self.open_settings)

    def open_settings(self):
        if self.settings_location is None:
            print("No settings found")
            return

        os.startfile(self.settings_location)

        QtWidgets.QMessageBox.information(
            self, "Info",
            "Opening config.ini\n"
            "Note: Please quit and restart Speedwagon to apply changes")


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

        self.setWindowTitle("Configuration")
        self.layout = QtWidgets.QVBoxLayout(self)
        self.tabsWidget = QtWidgets.QTabWidget(self)
        self.layout.addWidget(self.tabsWidget)

        self.open_settings_path_button = QtWidgets.QPushButton(self)
        self.open_settings_path_button.setText("Open Config File Directory")
        self.open_settings_path_button.clicked.connect(self.open_settings_dir)

        self.layout.addWidget(self.open_settings_path_button)

        self._button_box = \
            QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)

        self._button_box.accepted.connect(self.accept)
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
