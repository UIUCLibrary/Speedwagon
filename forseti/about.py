from PyQt5 import QtWidgets
import forseti
import email
import pkg_resources


def about_dialog_box(parent):
    try:
        distribution = forseti.get_project_distribution()
        metadata = dict(
            email.message_from_string(
                distribution.get_metadata(distribution.PKG_INFO)))
        summary = metadata['Summary']
        message = f"{forseti.__name__.title()}: {forseti.__version__}" \
                  f"\n" \
                  f"\n" \
                  f"{summary}"

    except pkg_resources.DistributionNotFound:
                message = f"{forseti.__name__.title()}: {forseti.__version__}"

    QtWidgets.QMessageBox.about(parent, "About", message)
