import email
from typing import Collection

import pkg_resources
from PyQt5 import QtWidgets, QtCore  # type: ignore

import speedwagon
from speedwagon import models, tabs
from speedwagon.ui import tab_editor_ui


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


class TabEditor(QtWidgets.QWidget, tab_editor_ui.Ui_Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self._all_workflows_model = None
        self._tabs_file = None
        self._tabs_model = models.TabsModel()
        self.selectedTabComboBox.setModel(self._tabs_model)
        self.selectedTabComboBox.currentIndexChanged.connect(self._changed_tab)
        self._active_tab_worksflows_model = models.WorkflowListModel2()
        self.tabWorkflowsListView.setModel(self._active_tab_worksflows_model)
        self.newTabButton.clicked.connect(self._create_new_tab)
        self.deleteCurrentTabButton.clicked.connect(self._delete_tab)
        self.addItemsButton.clicked.connect(self._add_items_to_tab)
        self.removeItemsButton.clicked.connect(self._remove_items)
    #     TODO: Connect ok and cancel button to editor

    @property
    def tabs_file(self):
        return self._tabs_file

    @tabs_file.setter
    def tabs_file(self, value):
        for tab in tabs.read_tabs_yaml(value):
            self._tabs_model.add_tab(tab)
        self._tabs_file = value

    def _changed_tab(self, tab):
        model = self.selectedTabComboBox.model()
        index = model.index(tab)
        data = model.data(index, role=QtCore.Qt.UserRole)
        self.tabWorkflowsListView.setModel(data.workflows)

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

            new_tab = tabs.TabData()
            new_tab.tab_name = new_tab_name
            self._tabs_model.add_tab(new_tab)
            new_index = self.selectedTabComboBox.findText(new_tab_name)
            self.selectedTabComboBox.setCurrentIndex(new_index)
            return

    def _delete_tab(self):
        data = self.selectedTabComboBox.currentData()
        model = self.selectedTabComboBox.model()
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
        self._all_workflows_model = models.WorkflowListModel2()
        for k, v in workflows.items():
            self._all_workflows_model.add_workflow(v)
        self._all_workflows_model.sort()
        self.allWorkflowsListView.setModel(self._all_workflows_model)

    @property
    def current_tab(self):
        return self.selectedTabComboBox.currentData()
