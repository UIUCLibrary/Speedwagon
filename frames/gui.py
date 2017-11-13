import sys
from PyQt5 import QtWidgets, QtCore
from frames.ui import main_window_ui
from frames.ui import main_window_shell_ui
# from frames.tool import AbsTool, MakeChecksumBatch
from frames import tool as t


class ToolSelectionDisplay(QtWidgets.QGroupBox):
    toolChanged = QtCore.pyqtSignal(t.AbsTool)

    def __init__(self, *__args):
        super().__init__(*__args)
        self.available_group_in = QtWidgets.QGroupBox(self)
        self.group_layout_in = QtWidgets.QVBoxLayout(self.available_group_in)
        self.group_layout_out = QtWidgets.QVBoxLayout(self)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidget(self.available_group_in)
        self.scroll_area.setWidgetResizable(True)
        self._current_selected = None

        self.group_layout_out.addWidget(self.scroll_area)
        self.setLayout(self.group_layout_out)

    def add_tool_to_available(self, tool: t.AbsTool):
        new_tool_option = QtWidgets.QRadioButton(self)
        new_tool_option.setObjectName(tool.name)
        new_tool_option.setText(tool.name)
        print(tool.name)
        new_tool_option.toggled.connect(lambda: self._tool_selected(tool))
        # self.verticalLayout_8.addWidget(new_tool_option)
        self.group_layout_in.addWidget(new_tool_option)

    def _tool_selected(self, tool):
        if tool != self._current_selected:
            self._current_selected = tool
            self.toolChanged.emit(tool)


class ToolConsole(QtWidgets.QGroupBox):

    def __init__(self, *__args):
        super().__init__(*__args)
        self.setTitle("Console")
        self.setLayout(QtWidgets.QVBoxLayout())
        self._console = QtWidgets.QTextBrowser(self)
        self.layout().addWidget(self._console)


class ToolWorkspace(QtWidgets.QGroupBox):

    def __init__(self, *args):
        super().__init__(*args)
        self.setTitle("Tool")
        self._tool_selected = ""
        self._description = ""
        self._selected_tool_name_line = QtWidgets.QLineEdit(self)
        self._description_information = QtWidgets.QTextEdit(self)
        self.settings = QtWidgets.QGroupBox(self)
        self.start_button = QtWidgets.QPushButton(self)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setObjectName("main_layout")

        self.main_layout.addLayout(self.build_metadata_layout())
        self.main_layout.addLayout(self.build_settings_layout())
        self.main_layout.addLayout(self.build_operations_layout())
        self.setLayout(self.main_layout)

    def build_metadata_layout(self):
        metadata_layout = QtWidgets.QFormLayout()
        metadata_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self._selected_tool_name_line.setReadOnly(True)
        self._description_information.setReadOnly(True)
        metadata_layout.addRow(QtWidgets.QLabel("Tool Selected"), self._selected_tool_name_line)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setVerticalStretch(1)
        self._description_information.setSizePolicy(sizePolicy)
        self._description_information.setMaximumHeight(100)
        metadata_layout.addRow(QtWidgets.QLabel("Description"), self._description_information)
        return metadata_layout

    def build_settings_layout(self):
        settings_layout = QtWidgets.QFormLayout()
        self.settings.setTitle("Settings")
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setVerticalStretch(1)

        self.settings.setSizePolicy(sizePolicy)
        self.settings.setMinimumHeight(40)
        settings_layout.addWidget(self.settings)

        return settings_layout

    def build_operations_layout(self):
        operations_layout = QtWidgets.QHBoxLayout()
        self.start_button.setText("Start")
        self.start_button.clicked.connect(self.start)
        operations_layout.addSpacerItem(QtWidgets.QSpacerItem(0, 40, QtWidgets.QSizePolicy.Expanding))
        operations_layout.addWidget(self.start_button)
        return operations_layout

    def start(self):
        QtWidgets.QMessageBox.information(self, "No op", "This does nothing for now")

    @property
    def tool_selected(self):
        return self._tool_selected

    @tool_selected.setter
    def tool_selected(self, value):
        self._tool_selected = value
        self._selected_tool_name_line.setText(value)

    @property
    def tool_description(self):
        return self._description

    @tool_description.setter
    def tool_description(self, value):
        self._description = value
        self._description_information.setText(value)


class MainWindow(QtWidgets.QMainWindow, main_window_shell_ui.Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.splitter = QtWidgets.QSplitter(self.tab_tools)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.tool_selector = self.create_tool_selector_widget()
        self.tool_workspace = self.create_tool_workspace()
        self.tool_selector.toolChanged.connect(self.change_tool)

        self.console = self.create_console()

        self.tab_tools_layout.addWidget(self.tool_selector)
        self.tab_tools_layout.addWidget(self.splitter)

        self.load_tools()
        self.show()

    def create_tool_workspace(self):
        new_workspace = ToolWorkspace(self.splitter)
        new_workspace.setMinimumSize(QtCore.QSize(0, 200))

        return new_workspace

    def create_console(self):
        console = ToolConsole(self.splitter)
        return console

    def _load_tool(self, tool):
        self.tool_selector.add_tool_to_available(tool)

    def load_tools(self):
        self._load_tool(t.MakeChecksumBatch())
        self._load_tool(t.Foo())

    def create_tool_selector_widget(self):
        tool_view = ToolSelectionDisplay(self.tab_tools)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        tool_view.setSizePolicy(size_policy)
        tool_view.setMinimumSize(QtCore.QSize(0, 100))
        return tool_view

    def change_tool(self, tool: t.AbsTool):
        self.tool_workspace.tool_selected = tool.name
        self.tool_workspace.tool_description = tool.description


def main():
    app = QtWidgets.QApplication(sys.argv)
    windows = MainWindow()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
