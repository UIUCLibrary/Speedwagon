from unittest.mock import Mock
import pytest
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from typing import List, Any
from speedwagon.job import AbsWorkflow
from speedwagon.frontend.qtwidgets import shared_custom_widgets


@pytest.mark.filterwarnings(
    "ignore:Use workflow.AbsOutputOptionDataType instead:DeprecationWarning")
def test_folder_browse_widget(qtbot, monkeypatch):
    widget = shared_custom_widgets.FolderBrowseWidget()

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getExistingDirectory",
        lambda *args, **kwargs: "/sample/path"
    )

    qtbot.addWidget(widget)
    assert len(widget.text_line.actions()) == 1
    x = widget.text_line.actions()[0]
    x.triggered.emit()
    assert widget.data == "/sample/path"
    assert widget.text_line.text() == "/sample/path"


@pytest.mark.filterwarnings(
    "ignore:Use workflow.AbsOutputOptionDataType instead:DeprecationWarning")
def test_browse_checksumfile(qtbot, monkeypatch):
    widget = shared_custom_widgets.ChecksumFile()

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (
            "/sample/path/sample.md5", 'Checksum files (*.md5)'
        )
    )
    qtbot.addWidget(widget)
    assert len(widget.text_line.actions()) == 1
    x = widget.text_line.actions()[0]
    x.triggered.emit()
    assert widget.data == "/sample/path/sample.md5"
    assert widget.text_line.text() == "/sample/path/sample.md5"


class Spam(AbsWorkflow):
    name = "Bacon"

    def discover_task_metadata(self, initial_results: List[Any],
                               additional_data, **user_args) -> List[dict]:
        return []


class MyWidget(QtWidgets.QDialog):
    user_settings = {}

    def __init__(self, parent= None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.my_layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.my_layout)
        self.tabs = QtWidgets.QTabWidget()
        self.layout().addWidget(self.tabs)

#
# @pytest.mark.filterwarnings(
#     "ignore:use ToolOptionsModel4 instead:DeprecationWarning")
# def test_boolean_delegate_is_combobox(qtbot, monkeypatch):
#     widget = MyWidget()
#
#     def user_options(self):
#         sample_boolean = shared_custom_widgets.BooleanSelect(
#             "sample question", bool)
#         sample_boolean.data = False
#         return [
#             sample_boolean
#         ]
#     # Patch the user options of Dummy with my own
#     Spam.user_options = user_options
#     mock_work_manager = Mock()
#     mock_work_manager.user_settings = {}
#
#     def get_item_options_model(self, workflow):
#         new_workflow = workflow(
#             global_settings=dict(self.work_manager.user_settings)
#         )
#         return speedwagon.frontend.qtwidgets.models.ToolOptionsModel4(
#             new_workflow.user_options()
#         )
#
#     monkeypatch.setattr(
#         WorkflowsTab,
#         "get_item_options_model",
#         get_item_options_model
#     )
#
#
#     workflow_tab = WorkflowsTab(parent=None, workflows={"spam": Spam},
#                                 work_manager=mock_work_manager)
#     widget.tabs.addTab(workflow_tab.tab_widget, "Eggs")
#     widget.update()
#     qtbot.addWidget(widget)
#
#     # Make sure the first item is selected
#     basic_index = workflow_tab.item_selection_model.index(0, 0)
#     workflow_tab.item_selector_view.setCurrentIndex(basic_index)
#
#     table = workflow_tab.workspace.findChild(QtWidgets.QTableView)
#     table.setItemDelegate(MyDelegate(table))
#     index = table.model().index(0, 0)
#     table.edit(index)
#     assert isinstance(table.indexWidget(index), QtWidgets.QComboBox)
