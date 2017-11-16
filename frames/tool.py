import abc

import os
from PyQt5 import QtWidgets


class AbsTool(metaclass=abc.ABCMeta):
    name = None  # type: str
    description = None  # type: str

    def __init__(self) -> None:
        super().__init__()
        self.options = []  # type: ignore


class AbsToolData(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def widget(self):
        pass

    def __init__(self):
        self.label = ""


class PathSelector(QtWidgets.QWidget):

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self._value = ""
        self.line = QtWidgets.QLineEdit()
        self.line.editingFinished.connect(self._update_value)
        self.button = QtWidgets.QPushButton()
        self.button.setText("Browse")
        self.button.clicked.connect(self.get_path)
        layout.addWidget(self.line)
        layout.addWidget(self.button)
        self.setLayout(layout)


    @property
    def valid(self) -> bool:
        return self._is_valid(self._value)


    def get_path(self):
        print("open dialog box")
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Find path")
        if self._is_valid(path):
            self.value = path

    def _update_value(self):
        print("Value is {}".format(self.line.text()))

    @staticmethod
    def _is_valid(value):
        if os.path.exists(value) and os.path.isdir(value):
            return True

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self.line.setText(value)


class SelectDirectory(AbsToolData):
    @property
    def widget(self):
        return PathSelector()


class MakeChecksumBatch(AbsTool):
    name = "Make Checksum Batch"
    description = "Makes a checksums"

    def __init__(self) -> None:
        super().__init__()
        source = SelectDirectory()
        source.label = "Source"
        self.options.append(source)


class Spam(AbsTool):
    name = "Spam"
    description = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin ac diam id purus pretium " \
                  "venenatis. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia " \
                  "Curae; Fusce laoreet fermentum lorem et pretium. Duis iaculis venenatis sagittis. Nulla tristique " \
                  "tellus at dolor laoreet maximus. Aenean ac posuere augue, quis volutpat felis. Phasellus egestas " \
                  "orci id erat fringilla, in euismod purus luctus. Proin faucibus condimentum imperdiet. Lorem " \
                  "ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque porttitor eu erat at congue. " \
                  "Quisque feugiat pulvinar eleifend. Nulla tincidunt nibh velit, non fermentum lorem pharetra at. " \
                  "Sed eleifend sapien ut faucibus convallis. Orci varius natoque penatibus et magnis dis parturient " \
                  "montes, nascetur ridiculus mus. Nullam lacinia sed augue quis iaculis. Aliquam commodo dictum mi, " \
                  "non semper quam varius ut."

    def __init__(self) -> None:
        super().__init__()

        input_data = SelectDirectory()
        input_data.label = "Input"
        self.options.append(input_data)

        output_data = SelectDirectory()
        output_data.label = "Output"
        self.options.append(output_data)


class Eggs(AbsTool):
    name = "Eggs"
    description = "Sed odio sem, vestibulum a lacus sed, posuere porta neque. Ut urna arcu, dignissim a dolor ac, " \
                  "sollicitudin pellentesque mi. Curabitur feugiat interdum mauris nec venenatis. In arcu elit, " \
                  "scelerisque et bibendum id, faucibus id enim. Proin dui mi, imperdiet eget varius ut, faucibus at " \
                  "lectus. Sed accumsan quis turpis id bibendum. Mauris in ligula nec tortor vulputate vulputate. " \
                  "Nullam tincidunt leo nec odio tincidunt malesuada. Integer ut massa dictum, scelerisque turpis " \
                  "eget, auctor nibh. Vestibulum sollicitudin sem eget enim congue tristique. Cras sed purus ac diam " \
                  "pulvinar scelerisque et efficitur justo. Duis eu nunc arcu"

    def __init__(self) -> None:
        super().__init__()

        input_data = SelectDirectory()
        input_data.label = "Goes In"
        self.options.append(input_data)

        output_data = SelectDirectory()
        output_data.label = "Goes out"
        self.options.append(output_data)
