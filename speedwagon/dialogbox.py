import textwrap

from PyQt5 import QtWidgets


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

    def setLabelText(self, p_str):
        # Don't make the label too long one a single size and stretch out the
        # dialog box too much
        super().setLabelText("\n".join(textwrap.wrap(p_str, width=50)))
