import logging
import sys
import warnings

import time
from PyQt5 import QtWidgets, QtCore, QtGui
import forseti.tool
import forseti.tools.abstool
from forseti.tools import tool_options
from forseti.ui import main_window_shell_ui
from forseti import tool as t, worker, runner_strategies
from collections import namedtuple
import traceback
import pkg_resources

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


class ConsoleLogger(logging.Handler):
    def __init__(self, console: ToolConsole, level=logging.NOTSET) -> None:
        super().__init__(level)
        self.console = console
        # self.callback = callback

    def emit(self, record):
        self.console.add_message(record.msg)
        # print(record.msg)
        # self.callback(record.msg)


class MainWindow(QtWidgets.QMainWindow, main_window_shell_ui.Ui_MainWindow):
    # noinspection PyUnresolvedReferences
    def __init__(self, parent=None):
        super().__init__(parent)

        # self.log_manager.setLevel(logging.DEBUG)
        # logger = logging.getLogger(__name__)
        # self.log_manager.debug("Setting up ui")
        self.setupUi(self)
        self.tabWidget.setTabEnabled(1, False)
        self.splitter = QtWidgets.QSplitter(self.tab_tools)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self._options_model = None
        self.label_2.setText(PROJECT_NAME)
        try:
            dist = pkg_resources.get_distribution("forseti")
            version = dist.version
        except pkg_resources.DistributionNotFound:
            version = "Development version"
        self.version_label.setText(version)
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
        self.tool_config_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)

        # self.tool_config_layout.
        self.tool_settings = QtWidgets.QTableView(self)
        self.tool_settings.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
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
        self.console = self.create_console()


        ###########################################################
        self.log_manager = logging.getLogger(__name__)
        self.log_manager.setLevel(logging.DEBUG)
        self._handler = ConsoleLogger(self.console)
        self.log_manager.addHandler(self._handler)
        self.log_manager.info("READY!")
        ###########################################################

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

        self.tabWidget.removeTab(1)
        self.show()
    #
    # @property
    # def log_manager(self):
    #     warnings.warn("Remove this", DeprecationWarning)
    #     return self._log_manager
    #
    # @log_manager.setter
    # def log_manager(self, value):
    #     self._log_manager = value
    #
    # @property
    # def _reporter(self):
    #     warnings.warn("Don't use this", DeprecationWarning)
    #     return self._reporter_
    #
    # @_reporter.setter
    # def _reporter(self, value):
    #     self._reporter_ = value

    # def get(self):
    #     options = dict()
    #     for data in self._data:
    #         options[data.name] = data.data
    #     return options
    def on_success(self, results, callback):
        self.log_manager.info("Done!")
        user_args = self._options_model.get()
        callback(results=results, user_args=user_args)
        report = self._tool.generate_report(results=results, user_args=user_args)
        if report:
            line_sep = "\n" + "*" * 60

            fancy_report = f"{line_sep}" \
                           f"\n   Report" \
                           f"{line_sep}" \
                           f"\n" \
                           f"\n{report}" \
                           f"\n" \
                           f"{line_sep}"

            # self.log_manager.notify(fancy_report)
            self.log_manager.info(fancy_report)

        # self._tool.on_completion(results=results,user_args=user_args)

        # QtWidgets.QMessageBox.about(self, "Finished", "Finished")

    def on_failed(self, exc):
        self.log_manager.error("Process failed. Reason: {}".format(exc))
        print("************** {}".format(exc))
        if exc:
            # self.log_manager.notify(str(exc))
            self.log_manager.warning(str(exc))
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
        # logger = logging.getLogger(__name__)
        # logger.debug("Start button pressed")
        if len(self.tool_selector_view.selectedIndexes()) != 1:
            print("Invalid number of selected Indexes. Expected 1. Found {}".format(
                len(self.tool_selector_view.selectedIndexes())))
            return

        tool = self.tool_list.data(self.tool_selector_view.selectedIndexes()[0], QtCore.Qt.UserRole)
        if issubclass(tool, forseti.tools.abstool.AbsTool):
            options = self._options_model.get()
            self._tool = tool

            wrapped_strat = runner_strategies.UsingWorkWrapper()
            runner = runner_strategies.RunRunner(wrapped_strat)
            runner.run(self, tool, options, self.on_success, self.on_failed, self.log_manager)



            # with worker.WorkWrapper(self, tool, log_handler=self._handler) as work_manager:
            #     # TODO, shouldn't be setting this here, However, the worker needs
            #
            #     # wm = worker.WorkDisplay(self)
            #     # wm = w.worker_display
            #     work_manager.worker_display.finished.connect(self.on_success)
            #     work_manager.worker_display.failed.connect(self.on_failed)
            #
            #     try:
            #         self.log_manager.debug("Validating arguments")
            #         work_manager.valid_arguments(options)
            #         # tool.validate_args(**options)
            #         # wm.completion_callback = lambda: self._tool.on_completion()
            #
            #         # Search for jobs
            #         job_searcher = JobSearcher(tool, options)
            #         # print("Job search starting", file=sys.stderr)
            #         job_searcher.start()
            #         while not job_searcher.isFinished():
            #             # self.log_manager.info("Loading")
            #             # print("loading", file=sys.stderr)
            #             QtCore.QCoreApplication.processEvents()
            #             # self.QApplication.processEvents()
            #         # print("Job search Finished", file=sys.stderr)
            #
            #         for _job_args in job_searcher.jobs:
            #             self.log_manager.debug("Adding {} with {} to work manager".format(tool, _job_args))
            #             work_manager.add_job(_job_args)
            #
            #         print("running {} tasks".format(work_manager.worker_display._jobs_queue.qsize()), file=sys.stderr)
            #         try:
            #             work_manager.run()
            #             # print("AFTER")
            #             # work_manager.worker_display.run()
            #
            #         except RuntimeError as e:
            #             QtWidgets.QMessageBox.warning(self, "Process failed", str(e))
            #         # except TypeError as e:
            #         #     QtWidgets.QMessageBox.critical(self, "Process failed", str(e))
            #         #     raise
            #
            #     except ValueError as e:
            #
            #         work_manager.worker_display.cancel(e, quiet=True)
            #         QtWidgets.QMessageBox.warning(self, "Invalid setting", str(e))
            #
            #     except Exception as e:
            #         work_manager.worker_display.cancel(e, quiet=True)
            #         exception_message = traceback.format_exception(type(e), e, tb=e.__traceback__)
            #         msg = QtWidgets.QMessageBox(self)
            #         msg.setIcon(QtWidgets.QMessageBox.Critical)
            #         msg.setWindowTitle(str(type(e).__name__))
            #         msg.setText(str(e))
            #         msg.setDetailedText("".join(exception_message))
            #         self.log_manager.fatal("Terminating application. Reason: {}".format(e))
            #         msg.exec_()
            #         print("Exiting early", file=sys.stderr)
            #         sys.exit(1)
            #     finally:
            #         print("out!", file=sys.stderr)

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


class JobSearcher(QtCore.QThread):
    def __init__(self, tool, options, parent=None):
        super(JobSearcher, self).__init__(parent)
        self._options = options
        self._tool = tool
        self.jobs = []

    def run(self):
        jobs = self._tool.discover_jobs(**self._options)
        self.jobs = jobs

class JobRunner(QtCore.QThread):

    def __init__(self, manager, active_tool, jobs,  parent=None):
        super().__init__(parent)
        self._manager = manager
        self._jobs = jobs
        self._active_tool = active_tool

    def run(self):
        print("This is job runner!")
        for job_args in self._jobs:
            job = self._active_tool.new_job()
            self._manager.add_job(job, **job_args)

        self._manager.run()


# class YesNoBoxDelegate(QtWidgets.QItemDelegate):
#
#     def __init__(self, parent=None):
#         warnings.warn("Don't use", DeprecationWarning)
#         super().__init__(parent)
#
#     def createEditor(self, parent, QStyleOptionViewItem, QModelIndex):
#         checkbox = QtWidgets.QComboBox(parent)
#         return checkbox
#
#     def setEditorData(self, editor: QtWidgets.QComboBox, QModelIndex):
#         editor.addItem("Yes")
#         editor.addItem("No")
#         super().setEditorData(editor, QModelIndex)


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

    # noinspection PyUnresolvedReferences
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
        super().destroyEditor(QWidget, QModelIndex)


# class CheckBoxDelegate(QtWidgets.QItemDelegate):
#
#     def __init__(self, parent=None):
#         warnings.warn("Dont use this", DeprecationWarning)
#         super().__init__(parent)
#
#     def createEditor(self, parent, QStyleOptionViewItem, QModelIndex):
#         checkbox = QtWidgets.QCheckBox(parent)
#         return checkbox
#         # return super().createEditor(parent, QStyleOptionViewItem, QModelIndex)
#
#     def setEditorData(self, editor: QtWidgets.QCheckBox, QModelIndex):
#         print(editor)
#         # q_widget = QWidget
#         super().setEditorData(editor, QModelIndex)

def main():

    # logger = logging.getLogger()
    # logger.setLevel(logging.DEBUG)
    # stdout_handler = logging.StreamHandler(sys.stdout)
    # logger.addHandler(stdout_handler)
    # logger.info("asdfasdfasdf")

    app = QtWidgets.QApplication(sys.argv)
    windows = MainWindow()
    windows.setWindowTitle(PROJECT_NAME)
    rc = app.exec_()
    sys.exit(rc)


if __name__ == '__main__':
    main()
