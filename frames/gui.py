import sys
from PyQt5 import QtWidgets, QtCore
from frames.ui import main_window_ui
from frames.ui import main_window_shell_ui
# from frames.tool import AbsTool, MakeChecksumBatch
from frames import tool as t


class ToolDisplay(QtWidgets.QWidget):

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.available_group = QtWidgets.QButtonGroup(self)
        self.group_layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.group_layout)

        # Get this size right!


    def add_tool_to_available(self, tool: t.AbsTool):
        new_tool_option = QtWidgets.QRadioButton(self)
        new_tool_option.setObjectName(tool.name)
        new_tool_option.setText(tool.name)
        # new_tool_option.toggled.connect(lambda: self.tool_selected(tool))
        # self.verticalLayout_8.addWidget(new_tool_option)
        self.group_layout.addWidget(new_tool_option)
        # self.layout.addWidget(new_tool_option)
        self.available_group.addButton(new_tool_option)

class MainWindow(QtWidgets.QMainWindow, main_window_shell_ui.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__()
        self._tools = []
        self.setupUi(self)
        self._tools_view = ToolDisplay(self.frame_available_tools)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self._tools_view.setSizePolicy(sizePolicy)
        self._tools_view.setMinimumSize(QtCore.QSize(0, 50))

        self.verticalLayout_4.addWidget(self._tools_view)
        # self.verticalLayout_4.insertWidget(0, self._tools_view)
        # self.frame_available_tools.add
        # self.self.verticalLayout_7.addWidget(self.verticalLayout_4)
        # self._tools_view.setLayout(self.verticalLayout_7)

        new_tool = t.MakeChecksumBatch()

        self._tools_view.add_tool_to_available(new_tool)
        self._tools_view.add_tool_to_available(t.Foo())
        self._tools_view.add_tool_to_available(t.Foo())

        self.show()
    #
    # def add_tool_to_available(self, tool: t.AbsTool):
    #     self._tools_view.add_tool_to_available(tool)
        # new_tool_option = QtWidgets.QRadioButton(self.frame_available_tools)
        # new_tool_option.setObjectName(tool.name)
        # new_tool_option.setText(tool.name)
        # new_tool_option.toggled.connect(lambda: self.tool_selected(tool))
        # # self.verticalLayout_8.addWidget(new_tool_option)
        # self.verticalLayout_4.addWidget(new_tool_option)
        # self._tools_view.available_group.addButton(new_tool_option)

    def tool_selected(self, tool: t.AbsTool):
        print(tool.name)
        self.lineEdit.setText(tool.name)
        self.textEdit.setText(tool.description)
        for foo in tool.options:
            new_label = QtWidgets.QLabel(self.frame_script_options)
            new_label.setText(foo[0])
            print(foo)
            self.formLayout_3.addWidget(new_label)



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
    rc = app.exec_()
    print("end")
    sys.exit(rc)


if __name__ == '__main__':
    
    main()