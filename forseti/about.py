from PyQt5 import QtWidgets
import forseti


def about_dialog_box(parent):
    message = f"{forseti.__name__.title()}" \
              f"\n" \
              f"\n" \
              f"Collection of tools and workflows for DS" \
              f"\n" \
              f"\n" \
              f"Version {forseti.__version__}"
    QtWidgets.QMessageBox.about(parent, "About", message)
