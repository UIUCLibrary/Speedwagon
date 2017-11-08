import sys
from PyQt5 import QtWidgets
from frames.ui import main_window

class MainWindow(QtWidgets.QMainWindow, main_window.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.show()

def main():
    print("HERE")
    app = QtWidgets.QApplication(sys.argv)
    windows = MainWindow()
    # windows.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    
    main()