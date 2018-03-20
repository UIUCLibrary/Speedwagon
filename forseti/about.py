from PyQt5 import QtWidgets
import forseti
import email


def about_dialog_box(parent):
    distribution = forseti.get_project_distribution()
    metadata = dict(email.message_from_string(distribution.get_metadata(distribution.PKG_INFO)))
    summary = metadata['Summary']

    message = f"{forseti.__name__.title()}: {forseti.__version__}" \
              f"\n" \
              f"\n" \
              f"{summary}"
    QtWidgets.QMessageBox.about(parent, "About", message)
