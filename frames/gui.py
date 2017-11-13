import sys
from PyQt5 import QtWidgets, QtCore
from frames.ui import main_window_ui
from frames.ui import main_window_shell_ui
# from frames.tool import AbsTool, MakeChecksumBatch
from frames import tool as t


class ToolSelectionDisplay(QtWidgets.QGroupBox):

    def __init__(self, *__args):
        super().__init__(*__args)
        self.available_group_in = QtWidgets.QGroupBox(self)
        self.group_layout_in = QtWidgets.QVBoxLayout(self.available_group_in)
        self.group_layout_out = QtWidgets.QVBoxLayout(self)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidget(self.available_group_in)
        self.scroll_area.setWidgetResizable(True)

        self.group_layout_out.addWidget(self.scroll_area)
        self.setLayout(self.group_layout_out)

    def add_tool_to_available(self, tool: t.AbsTool):
        new_tool_option = QtWidgets.QRadioButton(self)
        new_tool_option.setObjectName(tool.name)
        new_tool_option.setText(tool.name)
        print(tool.name)
        # new_tool_option.toggled.connect(lambda: self.tool_selected(tool))
        # self.verticalLayout_8.addWidget(new_tool_option)
        self.group_layout_in.addWidget(new_tool_option)

        # self.layout.addWidget(new_tool_option)
        # self.available_group.addButton(new_tool_option)


class ToolConsole(QtWidgets.QGroupBox):

    def __init__(self, *__args):
        super().__init__(*__args)
        self.setTitle("Tool Console")
        self.setLayout(QtWidgets.QVBoxLayout())
        self._console = QtWidgets.QTextBrowser(self)
        self.layout().addWidget(self._console)


class ToolOptions(QtWidgets.QGroupBox):

    def __init__(self, *args):
        super().__init__(*args)
        self.setTitle("Tool Options")
        self._tool_selected = ""

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setObjectName("main_layout")
        self.metadata_layout = QtWidgets.QFormLayout()
        self.metadata_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.operations_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton(self)
        self.start_button.setText("Start")
        self.operations_layout.addSpacerItem(QtWidgets.QSpacerItem(0, 40, QtWidgets.QSizePolicy.Expanding))
        self.operations_layout.addWidget(self.start_button)

        self._selected_tool_name_line = QtWidgets.QLineEdit(self)

        self.metadata_layout.addRow(QtWidgets.QLabel("Tool Selected"), self._selected_tool_name_line)

        description_information = QtWidgets.QTextEdit()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setVerticalStretch(1)
        description_information.setSizePolicy(sizePolicy)
        self.metadata_layout.addRow(QtWidgets.QLabel("Description"), description_information)
        self.main_layout.addLayout(self.metadata_layout)
        self.main_layout.addLayout(self.operations_layout)
        self.setLayout(self.main_layout)

    @property
    def tool_selected(self):
        return self._tool_selected

    @tool_selected.setter
    def tool_selected(self, value):
        self._tool_selected = value
        self._selected_tool_name_line.setText(value)


class MainWindow(QtWidgets.QMainWindow, main_window_shell_ui.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        # self._tools = []
        self.setupUi(self)
        self.splitter = QtWidgets.QSplitter(self.tab_tools)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.run_tools_widget = self.create_runtool_widget()
        self.load_tools(self.run_tools_widget)

        self.tool_workspace = self.create_tool_workspace()
        self.tool_workspace.tool_selected = "asdfsd"

        self.console = self.create_console()

        # ADD tools

        self.tab_tools_layout.addWidget(self.run_tools_widget)

        self.tab_tools_layout.addWidget(self.splitter)
        self.show()

    def create_tool_workspace(self):
        new_workspace = ToolOptions(self.splitter)
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        # new_workspace.setSizePolicy(sizePolicy)
        new_workspace.setMinimumSize(QtCore.QSize(0, 200))

        return new_workspace

    def create_console(self):
        console = ToolConsole(self.splitter)
        return console

    @staticmethod
    def load_tools(run_tools_widget):
        run_tools_widget.add_tool_to_available(t.MakeChecksumBatch())
        run_tools_widget.add_tool_to_available(t.Foo())


    def create_runtool_widget(self):
        tool_view = ToolSelectionDisplay(self.tab_tools)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        tool_view.setSizePolicy(sizePolicy)
        tool_view.setMinimumSize(QtCore.QSize(0, 100))
        return tool_view

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
            self.scrollAreaWidgetContents.addWidget(new_label)


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
