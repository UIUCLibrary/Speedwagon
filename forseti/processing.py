import warnings

from PyQt5 import QtWidgets, QtCore
import multiprocessing


class ProcessingDialog(QtWidgets.QProgressDialog):
    completed_successfully = QtCore.pyqtSignal()

    # def worker(self, finished_callback: typing.Callable = None, reporter_callback: typing.Callable = None):
    #     package = self.package_builder.build_package(self.root)
    #     with self.lock:
    #         self.package = package
    #     if finished_callback:
    #         finished_callback()
    #     self.completed_successfully.emit()

    def __init__(self, *__args):
        warnings.warn("Don't use", DeprecationWarning)
        super().__init__(*__args)
        self.completed_successfully.connect(self.all_done)
        # self.lock = threading.Lock()
        # self.package_builder = package_builder
        # self.root = root
        # self.q = queue.Queue()
        self.setRange(0, 0)
        # self.package_builder = package_builder
        self.package = None
        self.setWindowTitle("Processing")
        # self.setCancelButton(None)
        # self.setLabelText("Locating your files."
        #                   "\nThis might take some time depending on the size of the collection.")
        # self.thr = threading.Thread(target=self.worker)

    def all_done(self):
        self.close()

    def close(self):
        # self.thr.join()
        value = super().close()
        print("Closing")
        return value
