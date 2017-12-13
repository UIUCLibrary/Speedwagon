import multiprocessing
import sys
from PyQt5 import QtWidgets, QtCore, QtGui

import frames.tool
import frames.tools.abstool
from frames.ui import main_window_ui
from frames.ui import main_window_shell_ui
# from frames.tool import AbsTool, MakeChecksumBatch
from frames import tool as t, processing, worker
from collections import namedtuple
Setting = namedtuple("Setting", ("label", "widget"))


class ToolSelectionDisplay(QtWidgets.QGroupBox):
    toolChanged = QtCore.pyqtSignal(frames.tools.abstool.AbsTool)

    def __init__(self, *__args):
        super().__init__(*__args)
        self.available_group_in = QtWidgets.QGroupBox(self)
        size_p = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.MinimumExpanding)
        # self.setSizePolicy(size_p)
        self.available_group_in.setSizePolicy(size_p)
        # self.available_group_in.setFixedHeight(100)
        self.group_layout_in = QtWidgets.QVBoxLayout(self.available_group_in)
        # self.group_layout_in.setSpacing(0)
        self.group_layout_in.setContentsMargins(0,0,0,0)
        self.group_layout_out = QtWidgets.QVBoxLayout(self)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidget(self.available_group_in)
        self.scroll_area.setWidgetResizable(True)
        self._current_selected = None

        self.group_layout_out.addWidget(self.scroll_area)
        self.setLayout(self.group_layout_out)

    def add_tool_to_available(self, tool: frames.tools.abstool.AbsTool):
        new_tool_option = QtWidgets.QRadioButton(self)
        new_tool_option.setObjectName(tool.name)
        new_tool_option.setText(tool.name)
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
        self._console.setContentsMargins(0,0,0,0)
        self.layout().addWidget(self._console)
        font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        print(font)
        self._log = QtGui.QTextDocument()
        self._log.setDefaultFont(font)
        self._console.setSource(self._log.baseUrl())
        # self._log.contentsChanged.connect(self._console.)
        self._console.setUpdatesEnabled(True)

    def add_message(self, message):
        self._console.append(message)
        # self._log.setPlainText(message)
        # self._console.setText(self._log.toPlainText())
        # self._console.setText(message)

class ToolSettings(QtWidgets.QGroupBox):

    def __init__(self, parent=None, *__args):
        # self.(parent)
        super().__init__(parent, *__args)

        self.setTitle("Settings")
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.MinimumExpanding)
        self.create_inside_group(sizePolicy)
        self.create_outside_group()
        self.setMinimumHeight(80)
        self.settings = dict()

    def create_inside_group(self, sizePolicy):
        self.settings_group_in = QtWidgets.QGroupBox(self)

        self.settings_group_in.setSizePolicy(sizePolicy)
        self.group_layout_in = QtWidgets.QFormLayout(self.settings_group_in)

    def create_outside_group(self):
        self.settings_layout_out = QtWidgets.QVBoxLayout(self)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidget(self.settings_group_in)
        self.scroll_area.setWidgetResizable(True)
        # self.setSizePolicy(sizePolicy)
        # self.settings_layout_out.setFieldGrowthPolicy(self.settings_layout_out.AllNonFixedFieldsGrow)
        self.settings_layout_out.addWidget(self.scroll_area)
        self.setLayout(self.settings_layout_out)

    def add_setting(self, label: str, widget: QtWidgets.QWidget):
        widget.setParent(self)

        new_setting = Setting(QtWidgets.QLabel(text=label, parent=self), widget=widget)

        self.settings[label] = new_setting
        try:
            self.group_layout_in.addRow(*new_setting)
        except Exception as e:
            print(e, file=sys.stderr)
            raise

    def remove_row(self, row):
        print(row)
        fi = row.fieldItem
        li = row.labelItem
        print(fi)
        print(li)
        li.widget().deleteLater()
        fi.widget().deleteLater()




    def clear(self):
        l = self.group_layout_in
        # l = self.layout()

        while l.rowCount():
            row = l.takeRow(0)
            #
            self.remove_row(row)
            # l.removeRow(0)
            # print(w)
            # if w in not Noneand w.widget():
            #     w.widget().deleteLater()

            # w.deleteLater()
            # print(l.rowCount())
            # f = l.removeWidget(l.removeItem())
            # l.removeWidget(f)
            # print(l.rowCount()l)
            # print(f)
            # l.removeRow(0)
        self.settings.clear()
        # self.create_inside_group()


class ToolWorkspace(QtWidgets.QGroupBox):

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.setTitle("Tool")
        self._tool_selected = ""
        self._description = ""
        self._options_model = t.ToolOptionsModule(dict())
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

    def set_tool(self, tool: frames.tools.abstool.AbsTool):
        self._tool = tool
        self.tool_selected = tool.name
        self.tool_description = tool.description
        self._options_model = t.ToolOptionsModule(self._tool.get_arguments())
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
        if issubclass(self._tool, frames.tools.abstool.AbsTool):
            options = self._options_model.get()
            print("options are {}".format(options))
            wm = worker.WorkManager(self)
            if self._reporter:
                wm.log_manager.add_reporter(self._reporter)
            # options = self._tool.get_configuration()
            # print(options)
            tool_ = self._tool()
            try:
                jobs = self._tool.discover_jobs(**options)
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
        # self._load_tool(t.MakeChecksumBatch())
        # self._load_tool(t.Spam())
        # self._load_tool(t.Eggs())
        # self._load_tool(t.ZipPackages())

    def create_tool_selector_widget(self):

        tool_view = ToolSelectionDisplay(self.tab_tools)
        tool_view.setFixedHeight(100)
        # size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        # tool_view.setSizePolicy(size_policy)
        # tool_view.setMinimumSize(QtCore.QSize(0, 100))
        return tool_view

    def change_tool(self, tool: frames.tools.abstool.AbsTool):
        self.tool_workspace.set_tool(tool)

def main():
    app = QtWidgets.QApplication(sys.argv)
    windows = MainWindow()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
