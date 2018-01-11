import multiprocessing
import sys
from PyQt5 import QtWidgets, QtCore, QtGui
import warnings
import forseti.tool
import forseti.tools.abstool
from forseti.tools import tool_options
from forseti.ui import main_window_shell_ui
from forseti import tool as t, processing, worker
from collections import namedtuple
import traceback

PROJECT_NAME = "Forseti"

Setting = namedtuple("Setting", ("label", "widget"))


class ToolConsole(QtWidgets.QGroupBox):

    def __init__(self, *__args):
        super().__init__(*__args)
        self.setTitle("Console")
        self.setLayout(QtWidgets.QVBoxLayout())
        self._console = QtWidgets.QTextBrowser(self)
        self._console.setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._console)

        #  Use a monospaced font based on what's on system running
        monospaced_font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        self._log = QtGui.QTextDocument()
        self._log.setDefaultFont(monospaced_font)

        self._console.setSource(self._log.baseUrl())
        self._console.setUpdatesEnabled(True)
        self._console.setFont(monospaced_font)

    def add_message(self, message):
        self._console.append(message)


class ToolWorkspace(QtWidgets.QGroupBox):

    def __init__(self, *args, **kwargs):
        warnings.warn("Stop using this", DeprecationWarning)
        super().__init__(*args)
        self.setTitle("Tool")
        self.log_manager = worker.LogManager()
        self._tool_selected = ""
        self._description = ""
        # self._options_model = t.ToolOptionsPairsModel(dict())
        self._options_model = t.ToolOptionsModel2([])
        self._print_reporter = worker.StdoutReporter()
        self._tool = None
        if 'reporter' in kwargs:
            self._reporter = kwargs['reporter']
        else:
            self._reporter = None

        # self._selected_tool_name_line = QtWidgets.QLineEdit(self)
        # self._description_information = QtWidgets.QTextEdit(self)
        ####################################

        self.start_button = QtWidgets.QPushButton(self)
        self.settings = QtWidgets.QTableView(self)
        self.settings.setVisible(False)
        self.settings.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.settings.horizontalHeader().setVisible(False)
        self.settings.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.settings.setModel(self._options_model)
        self.settings.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.settings.verticalHeader().setSectionsClickable(False)

        # self.settings.setMinimumHeight(50)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setVerticalStretch(1)
        self.settings.setSizePolicy(sizePolicy)

        #  TODO: make self.main_layout add only widgets or layouts

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setObjectName("main_layout")

        self.main_layout.addLayout(self.build_metadata_layout(), stretch=0)
        self.main_layout.addWidget(self.settings, stretch=0, alignment=QtCore.Qt.AlignTop)
        # self.main_layout.addLayout(self.build_settings_layout())
        self.main_layout.addLayout(self.build_operations_layout())
        self.setLayout(self.main_layout)

        ####################################

    def build_metadata_layout(self):
        metadata_layout = QtWidgets.QFormLayout()
        metadata_layout.setVerticalSpacing(1)
        metadata_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        # self._selected_tool_name_line.setReadOnly(True)
        # self._description_information.setReadOnly(True)
        # metadata_layout.addRow(QtWidgets.QLabel("Tool Selected"), self._selected_tool_name_line)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setVerticalStretch(0)
        # self._description_information.setSizePolicy(sizePolicy)
        # self._description_information.setMaximumHeight(100)
        # metadata_layout.addRow(QtWidgets.QLabel("Description"), self._description_information)
        return metadata_layout

    def set_tool(self, tool: forseti.tools.abstool.AbsTool):
        self._tool = tool
        # self.tool_selected = tool.name
        # self.tool_description = tool.description
        self._options_model = t.ToolOptionsModel2(self._tool.get_user_options())  # type: ignore
        self.settings.setVisible(False)
        self.settings.setModel(self._options_model)
        for i in range(self._options_model.rowCount()):
            index = self._options_model.index(i, 0)
            data = self._options_model.data(index, role=QtCore.Qt.UserRole)
            delegate = ToolWorkspace.get_delegate(data.data_type)
            # self.settings.setItemDelegateForRow(i, None)
            self.settings.setItemDelegateForRow(i, delegate(self))
        # print()
        # self.settings.
        # self.settings.setMaximumHeight(24 * self._options_model.rowCount())
        self.settings.resizeColumnsToContents()
        self.settings.resizeRowsToContents()
        # self.settings.update()
        # self.settings.setVisible(True)

    @staticmethod
    def get_delegate(data_type):
        delegates = {
            str: QtWidgets.QItemDelegate,
            bool: CheckBoxDelegate
        }
        try:
            delegate = delegates[data_type]
            return delegate
        except KeyError:
            return QtWidgets.QItemDelegate

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

            wm = worker.WorkManager2(self)
            wm.finished.connect(self.on_success)
            wm.completion_callback = self._tool.on_completion
            # wm.finished.connect(self._tool.on_completion)
            # wm.finished.connect(lambda: self._tool.on_completion())
            if self._reporter:
                self.log_manager.add_reporter(self._reporter)
                wm.log_manager.add_reporter(self._reporter)
            # options = self._tool.get_configuration()
            # print(options)
            tool_ = self._tool()
            try:
                self._tool.validate_args(**options)
                # wm.completion_callback = lambda: self._tool.on_completion()
                jobs = self._tool.discover_jobs(**options)
                wm.progress_window.setWindowTitle(str(tool_.name))
                for _job_args in jobs:
                    job = tool_.new_job()
                    wm.add_job(job, **_job_args)
                try:
                    wm.run()

                except RuntimeError as e:
                    QtWidgets.QMessageBox.warning(self, "Process failed", str(e))
                # except TypeError as e:
                #     QtWidgets.QMessageBox.critical(self, "Process failed", str(e))
                #     raise

            except ValueError as e:
                wm.cancel(quiet=True)
                QtWidgets.QMessageBox.warning(self, "Invalid setting", str(e))
            except Exception as e:
                wm.cancel(quiet=True)
                exception_message = traceback.format_exception(type(e), e, tb=e.__traceback__)
                msg = QtWidgets.QMessageBox(self)
                msg.setIcon(QtWidgets.QMessageBox.Critical)
                msg.setWindowTitle(str(type(e).__name__))
                msg.setText(str(e))
                msg.setDetailedText("".join(exception_message))
                msg.exec_()
                sys.exit(1)
                # QtWidgets.QMessageBox.critical(self,
                #                                f"Unhandled Exception: {type(e).__name__}",
                #                                f"Unable to continue due to an unhandled exception.\n{e}")
                # raise
        else:
            QtWidgets.QMessageBox.warning(self, "No op", "No tool selected.")

    def on_success(self, results, callback):

        user_args = self._options_model.get()
        callback(results=results, user_args=user_args)
        report = self._tool.generate_report(results=results, user_args=user_args)
        if report:
            self.log_manager.notify(report)

        # self._tool.on_completion(results=results,user_args=user_args)

        QtWidgets.QMessageBox.about(self, "Finished", "Finished")

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
        # self.tool_workspace = self.create_tool_workspace()

        ###########################################################
        #
        self.tool_workspace2 = QtWidgets.QGroupBox()
        self.tool_workspace2.setTitle("Tool")
        self._selected_tool_name_line2 = QtWidgets.QLineEdit()
        self._selected_tool_name_line2.setReadOnly(True)
        self._description_information2 = QtWidgets.QTextBrowser()
        # self._description_information2 = QtWidgets.QLabel()
        # self._description_information2 = QtWidgets.QTextEdit()
        # self._description_information2.setText()
        # self._description_information2.setReadOnly(True)

        # Add the configuration and metadata widgets
        self.tool_config_layout = QtWidgets.QFormLayout()
        # self.tool_config_layout.
        self.tool_settings = QtWidgets.QTableView(self)
        self.tool_settings.setItemDelegate(MyDelegate(self))
        self.tool_settings.horizontalHeader().setVisible(False)
        self.tool_settings.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tool_settings.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.tool_settings.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.tool_settings.verticalHeader().setSectionsClickable(False)

        self.tool_config_layout.addRow(QtWidgets.QLabel("Tool Selected"), self._selected_tool_name_line2)
        self.tool_config_layout.addRow(QtWidgets.QLabel("Description"), self._description_information2)
        self.tool_config_layout.addRow(QtWidgets.QLabel("Tool Settings"), self.tool_settings)

        # Add the actions, aka Buttons
        self.tool_actions_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton()
        self.start_button.setText("Start")
        self.start_button.clicked.connect(self.start)

        self.tool_actions_layout.addSpacerItem(QtWidgets.QSpacerItem(0, 40, QtWidgets.QSizePolicy.Expanding))
        self.tool_actions_layout.addWidget(self.start_button)

        # Add the sublayouts to master layout
        self.tool_workspace2_layout = QtWidgets.QVBoxLayout()
        self.tool_workspace2_layout.addLayout(self.tool_config_layout)
        self.tool_workspace2_layout.addLayout(self.tool_actions_layout)
        self.tool_workspace2.setLayout(self.tool_workspace2_layout)

        self.splitter.addWidget(self.tool_workspace2)
        ###########################################################
        self.log_manager = worker.LogManager()
        self.console = self.create_console()
        self._reporter = worker.SimpleCallbackReporter(self.console.add_message)
        self._reporter.update("Ready!")

        self.tab_tools_layout.addWidget(self.tool_selector_view)

        # self.tab_tools_layout.addWidget(self.tool_selector)
        self.tab_tools_layout.addWidget(self.splitter)

        # self.tool_workspace._reporter = self._reporter
        self.load_tools()
        self.tool_list = t.ToolsListModel(t.available_tools())
        self.tool_selector_view.setModel(self.tool_list)
        self.tool_selector_view.selectionModel().currentChanged.connect(self.tool_selected)

        self.mapper = QtWidgets.QDataWidgetMapper(self)
        self.mapper.setModel(self.tool_list)
        self.mapper.addMapping(self._selected_tool_name_line2, 0)

        # This needs custom mapping because without it, new line characters are removed
        self.mapper.addMapping(self._description_information2, 1, b"plainText")

        self.tool_selector_view.selectionModel().currentChanged.connect(self.mapper.setCurrentModelIndex)
        self.tool_selector_view.selectionModel().currentChanged.connect(
            lambda: self.tool_settings.resizeRowsToContents())

        self.show()

    #
    # def get(self):
    #     options = dict()
    #     for data in self._data:
    #         options[data.name] = data.data
    #     return options
    def on_success(self, results, callback):
        print("Success")
        user_args = self._options_model.get()
        callback(results=results, user_args=user_args)
        report = self._tool.generate_report(results=results, user_args=user_args)
        if report:
            self.log_manager.notify(report)

        # self._tool.on_completion(results=results,user_args=user_args)

        QtWidgets.QMessageBox.about(self, "Finished", "Finished")

    def on_failed(self, exc):
        print("************** {}".format(exc))
        if exc:
            self.log_manager.notify(str(exc))
            exception_message = traceback.format_exception(type(exc), exc, tb=exc.__traceback__)
            msg = QtWidgets.QMessageBox(self)
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle(str(type(exc).__name__))
            msg.setText(str(exc))
            msg.setDetailedText("".join(exception_message))
            msg.exec_()
        # raise exc
        # sys.exit(1)

    def start(self):

        if len(self.tool_selector_view.selectedIndexes()) != 1:
            print("Invalid number of selected Indexes. Expected 1. Found {}".format(
                len(self.tool_selector_view.selectedIndexes())))
            return
        tool = self.tool_list.data(self.tool_selector_view.selectedIndexes()[0], QtCore.Qt.UserRole)
        ###########################

        if issubclass(tool, forseti.tools.abstool.AbsTool):
            # options = self.tool_config_layout.get(
            options = self._options_model.get()
            # print("options are {}".format(options))

            # TODO, shouldn't be setting this here, However, the worker needs
            self._tool = tool
            wm = worker.WorkManager2(self)
            wm.finished.connect(self.on_success)
            wm.failed.connect(self.on_failed)
            wm.completion_callback = tool.on_completion
            # wm.finished.connect(self._tool.on_completion)
            # wm.finished.connect(lambda: self._tool.on_completion())
            if self._reporter:
                self.log_manager.add_reporter(self._reporter)
                wm.log_manager.add_reporter(self._reporter)
            # options = self._tool.get_configuration()
            # print(options)
            active_tool = tool()
            try:
                tool.validate_args(**options)
                # wm.completion_callback = lambda: self._tool.on_completion()
                jobs = tool.discover_jobs(**options)
                wm.progress_window.setWindowTitle(str(tool.name))
                for _job_args in jobs:
                    job = active_tool.new_job()
                    wm.add_job(job, **_job_args)
                try:
                    wm.run()

                except RuntimeError as e:
                    QtWidgets.QMessageBox.warning(self, "Process failed", str(e))
                # except TypeError as e:
                #     QtWidgets.QMessageBox.critical(self, "Process failed", str(e))
                #     raise

            except ValueError as e:
                wm.cancel(quiet=True)
                QtWidgets.QMessageBox.warning(self, "Invalid setting", str(e))

            except Exception as e:
                wm.cancel(quiet=True)
                exception_message = traceback.format_exception(type(e), e, tb=e.__traceback__)
                msg = QtWidgets.QMessageBox(self)
                msg.setIcon(QtWidgets.QMessageBox.Critical)
                msg.setWindowTitle(str(type(e).__name__))
                msg.setText(str(e))
                msg.setDetailedText("".join(exception_message))
                msg.exec_()
                sys.exit(1)
                # QtWidgets.QMessageBox.critical(self,
                #                                f"Unhandled Exception: {type(e).__name__}",
                #                                f"Unable to continue due to an unhandled exception.\n{e}")
                # raise
            print("Out")
        else:
            QtWidgets.QMessageBox.warning(self, "No op", "No tool selected.")


    def tool_selected(self, index: QtCore.QModelIndex):
        tool = self.tool_list.data(index, QtCore.Qt.UserRole)
        # model.
        # self.tool_workspace.set_tool(tool)
        #################
        self._options_model = t.ToolOptionsModel3(tool.get_user_options())
        self.tool_settings.setModel(self._options_model)
        ##################
        # self.tool_settings.set
        # self._selected_tool_name_line.setText(tool.name)
        # self._selected_tool_description_line.setText(tool.description)
        # print(tool)
        # print(index)

    # def create_tool_workspace(self):
    #     warnings.warn("To be removed", DeprecationWarning)
    #     new_workspace = ToolWorkspace(self.splitter)
    #     new_workspace.setVisible(False)
    #     # new_workspace.setMinimumSize(QtCore.QSize(0, 300))
    #
    #     return new_workspace

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


class YesNoBoxDelegate(QtWidgets.QItemDelegate):

    def __init__(self, parent=None):
        warnings.warn("Don't use", DeprecationWarning)
        super().__init__(parent)

    def createEditor(self, parent, QStyleOptionViewItem, QModelIndex):
        checkbox = QtWidgets.QComboBox(parent)
        return checkbox

    def setEditorData(self, editor: QtWidgets.QComboBox, QModelIndex):
        editor.addItem("Yes")
        editor.addItem("No")
        super().setEditorData(editor, QModelIndex)


class MyDelegate(QtWidgets.QStyledItemDelegate):

    #
    # def __init__(self, parent=None):
    #     print("Using my delegate")
    #     super().__init__(parent)

    # def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem,
    #           index: QtCore.QModelIndex):
    #     # print("HERe")
    #     # button = QtWidgets.QPushButton()
    #     # painter.drawRect(option.rect)
    #     if index.isValid():
    #         painter.setBrush(QtGui.QBrush(QtCore.Qt.black))
    #         value = index.data(QtCore.Qt.DisplayRole)
    #         painter.drawText(option.rect, QtCore.Qt.AlignVCenter, value)
    #     painter.restore()



    def createEditor(self, parent, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
        if index.isValid():
            tool_settings = index.data(QtCore.Qt.UserRole)
            browser_widget = tool_settings.edit_widget()
            if browser_widget:
                assert isinstance(browser_widget, tool_options.CustomItemWidget)
                browser_widget.editingFinished.connect(self.update_custom_item)

                # browser_widget.editingFinished.connect(lambda : self.commitData(browser_widget))
                browser_widget.setParent(parent)


                return browser_widget
        return super().createEditor(parent, option, index)

    def update_custom_item(self):
        self.commitData.emit(self.sender())


    def setEditorData(self, editor: QtWidgets.QPushButton, index: QtCore.QModelIndex):

        if index.isValid():
            i = index.data(QtCore.Qt.UserRole)
            if isinstance(editor, tool_options.CustomItemWidget):
                editor.data = i.data
            # i.browse()
        super().setEditorData(editor, index)

    def setModelData(self, widget: QtWidgets.QWidget, model: QtCore.QAbstractItemModel, index):
        if isinstance(widget, tool_options.CustomItemWidget):
            model.setData(index, widget.data)
            return
        #     files = widget.selectedFiles()
        #     if len(files) == 1:
        #         model.setData(index, files[0])
        #     return
        super().setModelData(widget, model, index)

    def destroyEditor(self, QWidget, QModelIndex):
        print("Destroy editor")
        super().destroyEditor(QWidget, QModelIndex)


class CheckBoxDelegate(QtWidgets.QItemDelegate):

    def __init__(self, parent=None):
        warnings.warn("Dont use this", DeprecationWarning)
        super().__init__(parent)

    def createEditor(self, parent, QStyleOptionViewItem, QModelIndex):
        checkbox = QtWidgets.QCheckBox(parent)
        return checkbox
        # return super().createEditor(parent, QStyleOptionViewItem, QModelIndex)

    def setEditorData(self, editor: QtWidgets.QCheckBox, QModelIndex):
        print(editor)
        # q_widget = QWidget
        super().setEditorData(editor, QModelIndex)


def main():
    app = QtWidgets.QApplication(sys.argv)
    windows = MainWindow()
    windows.setWindowTitle(PROJECT_NAME)
    rc = app.exec_()
    sys.exit(rc)


if __name__ == '__main__':
    main()
