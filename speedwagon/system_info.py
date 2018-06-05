from PyQt5 import QtWidgets
import pkg_resources


class SystemInfoDialog(QtWidgets.QDialog):

    def __init__(self, parent: QtWidgets.QWidget, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)

        self.setWindowTitle("System Information")
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        self.installed_packages_title = QtWidgets.QLabel(parent)
        self.installed_packages_title.setText("Installed Python Packages:")

        installed_python_packages = sorted(
            (str(pkg) for pkg in pkg_resources.working_set),
            key=lambda x: str(x).lower()
        )

        self.installed_packages_widget = QtWidgets.QListWidget(parent)
        self.installed_packages_widget.addItems(installed_python_packages)

        layout.addWidget(self.installed_packages_title)
        layout.addWidget(self.installed_packages_widget)
