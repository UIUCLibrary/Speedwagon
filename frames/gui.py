import sys
from PyQt5 import QtWidgets, QtCore
from frames.ui import main_window_ui
from frames.ui import main_window_shell_ui
# from frames.tool import AbsTool, MakeChecksumBatch
from frames import tool as t

class MainWindow(QtWidgets.QMainWindow, main_window_shell_ui.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__()
        self._tools = []
        self.setupUi(self)
        self.available_group = QtWidgets.QButtonGroup(self.frame_available_tools)


        new_tool = t.MakeChecksumBatch()
        self.add_tool_to_available(new_tool)
        new_tool2 = t.Foo()
        self.add_tool_to_available(new_tool2)

        self.show()

    def add_tool_to_available(self, tool: t.AbsTool):

        new_tool_option = QtWidgets.QRadioButton(self.frame_available_tools)
        new_tool_option.setObjectName(tool.name)
        new_tool_option.setText(tool.name)
        new_tool_option.toggled.connect(lambda: self.tool_selected(tool))
        # self.verticalLayout_8.addWidget(new_tool_option)
        self.verticalLayout_4.addWidget(new_tool_option)
        self.available_group.addButton(new_tool_option)

    def tool_selected(self, tool: t.AbsTool):
        print(tool.name)
        self.lineEdit.setText(tool.name)
        self.textEdit.setText(tool.description)
        # for foo in tool.options:
        #     new_label = QtWidgets.QLabel(self.frame_script_options)
        #     new_label.setText(foo[0])
        #     print(foo)
        #     self.formLayout_3.addWidget(new_label)



class MainWindow_example(QtWidgets.QMainWindow, main_window_ui.Ui_MainWindow):
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