"""Creating and managing tabs in the UI display."""
from __future__ import annotations

import io
import os
import sys
import typing
from typing import List, Optional, Iterator, NamedTuple, cast, Type, Dict

import yaml
from PySide6 import QtWidgets, QtCore  # type: ignore
import speedwagon
from speedwagon.config import StandardConfig
from speedwagon.job import NullWorkflow, Workflow
from speedwagon.frontend import qtwidgets
from speedwagon.frontend.qtwidgets.models import WorkflowListModel2
if typing.TYPE_CHECKING:
    from speedwagon.frontend.qtwidgets.widgets import \
        Workspace, \
        SelectWorkflow, \
        UserDataType


try:  # pragma: no cover
    from importlib.resources import as_file
    from importlib import resources
except ImportError:  # pragma: no cover
    import importlib_resources as resources  # type: ignore
    from importlib_resources import as_file


__all__ = [
    "TabData",
    "read_tabs_yaml",
    "write_tabs_yaml",
    "extract_tab_information"
]


class TabsFileError(speedwagon.exceptions.SpeedwagonException):
    """Error with Tabs File."""


class WorkflowsTab3(QtWidgets.QWidget):
    start_workflow = QtCore.Signal(str, dict)
    workflow_selected = QtCore.Signal(object)
    settings_changed = QtCore.Signal()

    start_button: QtWidgets.QPushButton
    workspace: Workspace
    workflow_selector: SelectWorkflow

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._parent = parent
        with as_file(
                resources.files(
                    "speedwagon.frontend.qtwidgets.ui"
                ).joinpath("create_job_tab.ui")
        ) as ui_file:
            qtwidgets.ui_loader.load_ui(str(ui_file), self)

        self.app_settings_lookup_strategy = StandardConfig()
        self.start_button.clicked.connect(self.submit_job)

        self.workflow_selector.workflow_selected.connect(
            self._handle_workflow_changed
        )
        self._workflow_selected: Optional[Type[speedwagon.Workflow]] = None
        self.settings_changed.connect(self._update_okay_button)
        self.settings_changed.emit()

    def set_current_workflow(self, workflow_name: str) -> None:
        self.workflow_selector.set_current_by_name(workflow_name)

    def set_current_workflow_settings(
            self,
            data: Dict[str, UserDataType]
    ) -> None:
        workflow_klass = self.workflow_selector.get_current_workflow_type()
        if workflow_klass is None:
            raise ValueError(
                "Current Workflow not set. Workflow must be set first."
            )
        workflow_inst = workflow_klass(
            self.workspace.app_settings_lookup_strategy.settings()
        )
        qtwidgets.gui.load_job_settings_model(
            data,
            self.workspace.settings_form,
            workflow_inst.get_user_options()
        )

    def _handle_workflow_changed(
            self,
            workflow_klass: typing.Type[Workflow]
    ) -> None:
        self._workflow_selected = workflow_klass
        self.workspace.app_settings_lookup_strategy = \
            self.app_settings_lookup_strategy

        self.workspace.set_workflow(workflow_klass)
        self.settings_changed.emit()

    def get_app_config(self):
        return self.app_settings_lookup_strategy.settings()

    def _update_okay_button(self) -> None:
        if self._workflow_selected is None:
            self.start_button.setEnabled(False)
        else:
            self.start_button.setEnabled(True)

    def submit_job(self) -> None:
        if not self.workspace.is_valid():
            message = "\n".join(self.workspace.settings_form.issues)
            config_error_dialog = QtWidgets.QMessageBox(self)
            config_error_dialog.setWindowTitle("Settings Error")
            config_error_dialog.setDetailedText(f"{message}")
            config_error_dialog.setText(
                "Speedwagon has a problem with current configuration "
                "settings"
            )
            config_error_dialog.exec_()
            return
        self.start_workflow.emit(
            self.workspace.name,
            self.workspace.configuration
        )

    @property
    def workflows(self) -> Dict[str, Type[speedwagon.Workflow]]:
        return self.workflow_selector.workflows

    @workflows.setter
    def workflows(self, value: Dict[str, Type[speedwagon.Workflow]]) -> None:
        for workflow_klass in value.values():
            self.workflow_selector.add_workflow(workflow_klass)


class TabData(NamedTuple):
    """Tab data."""

    tab_name: str
    workflows_model: WorkflowListModel2


def read_tabs_yaml(yaml_file: str) -> Iterator[TabData]:
    """Read a custom tab yaml file."""
    tabs_file_size = os.path.getsize(yaml_file)
    if tabs_file_size > 0:
        try:
            with open(yaml_file, encoding="utf-8") as file:
                tabs_config_data = \
                    yaml.load(file.read(), Loader=yaml.SafeLoader)
            if not isinstance(tabs_config_data, dict):
                raise TabsFileError("Failed to parse file")

            for tab_name in tabs_config_data:
                model = WorkflowListModel2()
                for workflow_name in tabs_config_data.get(tab_name, []):
                    empty_workflow = \
                        cast(
                            Type[Workflow],
                            type(
                                workflow_name,
                                (NullWorkflow,),
                                {
                                    "name": workflow_name
                                }
                            )
                        )
                    model.add_workflow(empty_workflow)
                    model.reset_modified()
                yield TabData(tab_name, model)

        except FileNotFoundError as error:
            print(
                f"Custom tabs file not found. Reason: {error}",
                file=sys.stderr
            )
            raise
        except AttributeError as error:
            print(
                f"Custom tabs file failed to load. Reason: {error}",
                file=sys.stderr
            )
            raise

        except yaml.YAMLError as yaml_error:
            print(
                f"{yaml_file} file failed to load. "
                f"Reason: {yaml_error}",
                file=sys.stderr
            )
            raise


def serialize_tabs_yaml(tabs: List[TabData]) -> str:
    tabs_data = {}
    for tab in tabs:
        tab_model = tab.workflows_model

        tabs_data[tab.tab_name] = \
            [workflow.name for workflow in tab_model.workflows]

    with io.StringIO() as file_handle:
        yaml.dump(tabs_data, file_handle, default_flow_style=False)
        value = file_handle.getvalue()
    return value


def write_tabs_yaml(yaml_file: str, tabs: List[TabData]) -> None:
    """Write out tab custom information to a yaml file."""
    with open(yaml_file, "w", encoding="utf-8") as file_handle:
        data = serialize_tabs_yaml(tabs)
        file_handle.write(data)


def extract_tab_information(
        model: qtwidgets.models.TabsModel
) -> List[TabData]:
    """Get tab information."""
    tabs = []
    for tab in model.tabs:
        new_tab = TabData(tab.tab_name, tab.workflows_model)
        tabs.append(new_tab)
    return tabs
