"""Load Qt widget ui assets."""

import typing

from PySide6.QtUiTools import QUiLoader
from PySide6 import QtWidgets
from speedwagon.frontend.qtwidgets.gui import ToolConsole, ItemTabsWidget
from speedwagon.frontend.qtwidgets.widgets import (
    DynamicForm,
    Workspace,
    SelectWorkflow,
)

__all__ = ["load_ui"]


class UiLoader(QUiLoader):  # pylint: disable=too-few-public-methods
    registered_widgets = set()
    def __init__(
        self, base_instance: typing.Optional[QtWidgets.QWidget]
    ) -> None:
        QUiLoader.__init__(self, base_instance)
        self.base_instance = base_instance

    def createWidget(  # pylint: disable=invalid-name
        self,
        class_name: str,
        parent: typing.Optional[QtWidgets.QWidget] = None,
        name: str = "",
    ) -> QtWidgets.QWidget:
        if parent is None and self.base_instance:
            return self.base_instance
        # create a new widget for child widgets
        widget = QUiLoader.createWidget(self, class_name, parent, name)
        if self.base_instance:
            setattr(self.base_instance, name, widget)
        return widget
    def register_custom_widget(
            self,
            custom_widget_type: typing.Type[QtWidgets.QWidget]
    ) -> None:
        """Register custom widget with QUiLoader if not already registered.

        Args:
            custom_widget_type: class of custom widget
        """
        if custom_widget_type in UiLoader.registered_widgets:
            return
        UiLoader.registered_widgets.add(custom_widget_type)
        self.registerCustomWidget(custom_widget_type)

def load_ui(
    ui_file: str, base_instance: typing.Optional[QtWidgets.QWidget] = None
) -> QtWidgets.QWidget:
    loader = UiLoader(base_instance)
    loader.register_custom_widget(ToolConsole)
    loader.register_custom_widget(ItemTabsWidget)
    loader.register_custom_widget(DynamicForm)
    loader.register_custom_widget(SelectWorkflow)
    loader.register_custom_widget(Workspace)
    return loader.load(ui_file)
