import abc

from PyQt5 import QtWidgets, QtCore  # type: ignore


class WidgetMeta(abc.ABCMeta, type(QtCore.QObject)):  # type: ignore
    pass


class CustomItemWidget(QtWidgets.QWidget):
    editingFinished = QtCore.pyqtSignal()

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._data = ""
        self.inner_layout = QtWidgets.QHBoxLayout(parent)
        self.inner_layout.setSpacing(3)
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.inner_layout)
        self.setAutoFillBackground(True)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        self.editingFinished.emit()


class AbsBrowseableWidget(CustomItemWidget, metaclass=WidgetMeta):
    # class AbsBrowseableWidget(metaclass=WidgetMeta):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self.text_line = QtWidgets.QLineEdit(self)
        size_p = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                       QtWidgets.QSizePolicy.MinimumExpanding)
        self.text_line.setSizePolicy(size_p)
        self.browse_button = QtWidgets.QPushButton("Browse", parent=self)
        # self.browse_button.setSizePolicy(size_p)
        self.inner_layout.addWidget(self.text_line)
        self.inner_layout.addWidget(self.browse_button)
        self.text_line.textEdited.connect(self._change_data)
        self.text_line.editingFinished.connect(self.editingFinished)
        # self.text_line.focus
        # self.text_line.
        self.browse_button.clicked.connect(self.browse_clicked)
        # self.browse_button.clicked.connect(self.editingFinished)

        # self.setFocusPolicy(QtCore.Qt.StrongFocus)
        # self.text_line.setFocusPolicy(QtCore.Qt.StrongFocus)

    @abc.abstractmethod
    def browse_clicked(self):
        pass

    @property
    def data(self):
        return super().data

    @data.setter
    def data(self, value):
        self._data = value
        self.text_line.setText(value)

    def _change_data(self, value):
        self.data = value
