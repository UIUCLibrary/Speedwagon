import os

from PyQt5 import QtWidgets

from speedwagon.tools import options


class ChecksumFile(options.AbsBrowseableWidget):
    def browse_clicked(self):
        selection = QtWidgets.QFileDialog.getOpenFileName(
            filter="Checksum files (*.md5)")

        if selection[0]:
            self.data = selection[0]
            self.editingFinished.emit()


class ChecksumData(options.AbsCustomData2):

    @classmethod
    def is_valid(cls, value) -> bool:
        if not os.path.exists(value):
            return False
        if os.path.basename(value) == "checksum":
            print("No a checksum file")
            return False
        return True

    @classmethod
    def edit_widget(cls) -> QtWidgets.QWidget:
        return ChecksumFile()
