from typing import List, Type, Optional, Dict

from PySide6 import QtWidgets, QtCore
import speedwagon

from speedwagon.frontend.qtwidgets.widgets import UserDataType, Workspace
from speedwagon.config import AbsConfigSettings

class ItemTabsUI(QtWidgets.QWidget):
    def layout(self) -> QtWidgets.QVBoxLayout: ...

class WorkflowsTab3UI(QtWidgets.QWidget):
    workspace: Workspace

class WorkflowsTab3(WorkflowsTab3UI):
    def set_current_workflow_settings(
            self, data: Dict[str, UserDataType]
    ) -> None:
        ...

    def set_current_workflow(self, workflow_name: str) -> None:
        ...

class ItemTabsWidget(ItemTabsUI):
    submit_job: QtCore.Signal
    tabs: QtWidgets.QTabWidget
    session_config: AbsConfigSettings

    def add_workflows_tab(
        self, name: str, workflows: List[Type[speedwagon.Workflow]]
    ) -> None:
        ...

    @property
    def current_tab(self) -> Optional[WorkflowsTab3]:
        ...

    def clear_tabs(self) -> None:
        ...
