import multiprocessing
import sys
from PyQt5 import QtWidgets, QtCore, QtGui
import warnings
import forseti.tool
import forseti.tools.abstool
from forseti.ui import main_window_shell_ui
from forseti import tool as t, processing, worker
from collections import namedtuple

PROJECT_NAME = "Forseti"

Setting = namedtuple("Setting", ("label", "widget"))

class ToolConsole(QtWidgets.QGroupBox):

    def __init__(self, *__args):
        super().__init__(*__args)
        self.setTitle("Console")
        self.setLayout(QtWidgets.QVBoxLayout())
        self._console = QtWidgets.QTextBrowser(self)
        self._console.setContentsMargins(0,0,0,0)
        self.layout().addWidget(self._console)

        #  Use a monospaced font based on what's on system running
        monospaced_font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        self._log = QtGui.QTextDocument()
        self._log.setDefaultFont(monospaced_font)

        self._console.setSource(self._log.baseUrl())
        self._console.setUpdatesEnabled(True)

    def add_message(self, message):
        self._console.append(message)



class ToolWorkspace(QtWidgets.QGroupBox):

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.setTitle("Tool")
        self._tool_selected = ""
        self._description = ""
        self._options_model = t.ToolOptionsPairsModel(dict())
        self._print_reporter = worker.StdoutReporter()
        self._tool = None
        if 'reporter' in kwargs:
            self._reporter = kwargs['reporter']
        else:
            self._reporter = None
        self._selected_tool_name_line = QtWidgets.QLineEdit(self)
        self._description_information = QtWidgets.QTextEdit(self)
        self.start_button = QtWidgets.QPushButton(self)
        self.settings = QtWidgets.QTableView(self)
        self.settings.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.settings.horizontalHeader().setVisible(False)
        self.settings.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.settings.setModel(self._options_model)
        self.settings.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.settings.verticalHeader().setSectionsClickable(False)

        self.settings.setMinimumHeight(50)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setVerticalStretch(1)
        self.settings.setSizePolicy(sizePolicy)


        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setObjectName("main_layout")

        self.main_layout.addLayout(self.build_metadata_layout())
        self.main_layout.addWidget(self.settings, stretch=0)
        # self.main_layout.addLayout(self.build_settings_layout())
        self.main_layout.addLayout(self.build_operations_layout())
        self.setLayout(self.main_layout)

    def build_metadata_layout(self):
        metadata_layout = QtWidgets.QFormLayout()
        metadata_layout.setVerticalSpacing(0)
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

    def set_tool(self, tool: forseti.tools.abstool.AbsTool):
        self._tool = tool
        self.tool_selected = tool.name
        self.tool_description = tool.description
        self._options_model = t.ToolOptionsModel2(self._tool.get_user_options())
        self.settings.setModel(self._options_model)
        self.settings.resizeColumnsToContents()
        self.settings.resizeRowsToContents()
        # self.settings.update()

    def build_operations_layout(self):
        operations_layout = QtWidgets.QHBoxLayout()
        self.start_button.setText("Start")
        self.start_button.clicked.connect(self.start)
        operations_layout.addSpacerItem(QtWidgets.QSpacerItem(0, 40, QtWidgets.QSizePolicy.Expanding))
        operations_layout.addWidget(self.start_button)
        return operations_layout

    def start(self):
        if issubclass(self._tool, forseti.tools.abstool.AbsTool):
            options = self._options_model.get()
            # print("options are {}".format(options))
            wm = worker.WorkManager(self)
            wm.finished.connect(self.on_success)
            if self._reporter:
                wm.log_manager.add_reporter(self._reporter)
            # options = self._tool.get_configuration()
            # print(options)
            tool_ = self._tool()
            try:
                jobs = self._tool.discover_jobs(**options)
                wm.prog.setWindowTitle(str(tool_.name).title())
                for _job_args in jobs:
                    job = tool_.new_job()
                    wm.add_job(job, **_job_args)
                try:
                    wm.run()
                except RuntimeError as e:
                    QtWidgets.QMessageBox.warning(self, "Process failed", str(e))
            except ValueError as e:
                wm.cancel()
                QtWidgets.QMessageBox.warning(self, "Invalid setting", str(e))
        else:
            QtWidgets.QMessageBox.warning(self, "No op", "No tool selected.")

    def on_success(self, results):
        QtWidgets.QMessageBox.about(self, "Finished", "Finished")
        user_args = self._options_model.get()
        report = self._tool.generate_report(results=results, user_args=user_args)
        if report:
            self._reporter.update(report)
        self._tool.on_completion(results=results, user_args=user_args)


    @property
    def tool_selected(self):
        return self._tool_selected

    @tool_selected.setter
    def tool_selected(self, value):
        self._tool_selected = value
        self._selected_tool_name_line.setText(value.title())

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
        self.tabWidget.setTabEnabled(1, False)
        self.splitter = QtWidgets.QSplitter(self.tab_tools)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self._options_model = None
        self.label_2.setText(PROJECT_NAME)
        # self.tool_selector = self.create_tool_selector_widget()

        self.tool_selector_view = QtWidgets.QListView(self)
        self.tool_selector_view.setFixedHeight(100)

        # self.tool_selector_view.clicked.connect(self.tool_selected)
        # self.tool_selector_view.indexesMoved.connect(self.tool_selected)

        # self.tool_selector_view.clicked.connect(lambda s: print("clicked on {}".format(s.row())))

        # self.tool_selector.toolChanged.connect(self.change_tool)
        self.tool_workspace = self.create_tool_workspace()
        self.console = self.create_console()
        self._reporter = worker.SimpleCallbackReporter(self.console.add_message)
        self._reporter.update("Ready!")



        self.tab_tools_layout.addWidget(self.tool_selector_view)
        # self.tab_tools_layout.addWidget(self.tool_selector)
        self.tab_tools_layout.addWidget(self.splitter)


        self.tool_workspace._reporter = self._reporter
        self.load_tools()
        self.tool_list = t.ToolsListModel(t.available_tools())
        self.tool_selector_view.setModel(self.tool_list)
        self.tool_selector_view.selectionModel().currentChanged.connect(self.tool_selected)
        # self.tool_selector_view.selectionChanged.conne

        # self.mapper = QtWidgets.QDataWidgetMapper(self)
        # self.mapper.setModel(self.tool_list)
        # print(self.mapper.currentIndex())
        # self.mapper.addMapping(self._selected_tool_name_line,  0)
        # self.mapper.addMapping(self._selected_tool_description_line,  1)
        # self.mapper.toFirst()
        # print(self.mapper.currentIndex())
        # self.mapper.toNext()
        # print(self.mapper.currentIndex())

        self.show()

    def tool_selected(self, index: QtCore.QModelIndex):
        tool = self.tool_list.data(index, QtCore.Qt.UserRole)
        # model.
        self.tool_workspace.set_tool(tool)
        # self._selected_tool_name_line.setText(tool.name)
        # self._selected_tool_description_line.setText(tool.description)
        # print(tool)
        # print(index)

    def create_tool_workspace(self):
        new_workspace = ToolWorkspace(self.splitter)
        # new_workspace.setMinimumSize(QtCore.QSize(0, 300))

        return new_workspace

    def create_console(self):
        console = ToolConsole(self.splitter)

        return console

    def _load_tool(self, tool):
        pass
        # self.tool_selector.add_tool_to_available(tool)

    def load_tools(self):
        # tools =

        for k, v in t.available_tools().items():
            self._load_tool(v())


    def change_tool(self, tool: forseti.tools.abstool.AbsTool):
        self.tool_workspace.set_tool(tool)

def main():
    app = QtWidgets.QApplication(sys.argv)
    windows = MainWindow()
    windows.setWindowTitle(PROJECT_NAME)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
