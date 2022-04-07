import typing

from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QMetaObject
from PySide6 import QtWidgets

__all__ = ['load_ui']


class UiLoader(QUiLoader):  # pylint: disable=too-few-public-methods
    def __init__(
            self,
            base_instance: typing.Optional[QtWidgets.QWidget]
    ) -> None:
        QUiLoader.__init__(self, base_instance)
        self.base_instance = base_instance

    def createWidget(  # pylint: disable=invalid-name
            self,
            class_name: str,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            name: str = ''
    ) -> QtWidgets.QWidget:
        if parent is None and self.base_instance:
            return self.base_instance
        # create a new widget for child widgets
        widget = QUiLoader.createWidget(self, class_name, parent, name)
        if self.base_instance:
            setattr(self.base_instance, name, widget)
        return widget


def load_ui(
        ui_file: str,
        base_instance: typing.Optional[QtWidgets.QWidget] = None
) -> QtWidgets.QWidget:
    loader = UiLoader(base_instance)
    widget = loader.load(ui_file)
    QMetaObject.connectSlotsByName(widget)
    return widget