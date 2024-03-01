import pytest

QtCore = pytest.importorskip("PySide6.QtCore")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from speedwagon.frontend.qtwidgets.dialog.dialogs import TableEditDialog
from uiucprescon.packager.packages import collection
from speedwagon.frontend.qtwidgets import user_interaction
from uiucprescon.packager.common import Metadata as PackageMetadata
from speedwagon.workflows import workflow_batch_to_HathiTrust_TIFF as wf

from unittest.mock import Mock
import os


def test_get_additional_info_qt(qtbot, monkeypatch):

    factory = user_interaction.QtWidgetFactory(None)

    workflow = wf.CaptureOneBatchToHathiComplete()
    options = {}

    object_record_1 = collection.Package()
    object_record_1.component_metadata[PackageMetadata.ID] = "1234"
    object_record_1.component_metadata[PackageMetadata.TITLE_PAGE] = (
        "1234_1.jp2"
    )
    object_record_1.component_metadata[PackageMetadata.PATH] = os.path.join(
        ".", "1234"
    )

    item_1a = collection.Item(object_record_1)
    item_1a.component_metadata[PackageMetadata.ID] = "1234_1"

    collection.Instantiation(parent=item_1a, files=["1234_1.jp2"])

    item_1b = collection.Item(object_record_1)
    item_1b.component_metadata[PackageMetadata.ID] = "1234_2"
    collection.Instantiation(parent=item_1b, files=["1234_2.jp2"])

    object_record_2 = collection.Package()
    object_record_2.component_metadata[PackageMetadata.ID] = "1235"
    object_record_2.component_metadata[PackageMetadata.PATH] = os.path.join(
        ".", "1235"
    )
    object_record_2.component_metadata[PackageMetadata.TITLE_PAGE] = (
        "1235_1.jp2"
    )

    item_2a = collection.Item(object_record_2)
    item_2a.component_metadata[PackageMetadata.ID] = "1235_1"
    collection.Instantiation(parent=item_2a, files=["1235_1.jp2"])

    pretask_results = [
        Mock(name="pretask_result", data=[object_record_1, object_record_2])
    ]

    def exec_table(_self: TableEditDialog):
        qtbot.addWidget(_self)

        _self.view.show()
        index_1 = _self.view.model().index(0, 1)
        _self.view.setCurrentIndex(index_1)
        _self.view.openPersistentEditor(index_1)
        qtbot.wait_until(
            lambda: _self.view.indexWidget(_self.view.currentIndex())
            is not None
        )
        combo_widget: QtWidgets.QComboBox = _self.view.indexWidget(
            _self.view.currentIndex()
        )
        combo_widget.setCurrentIndex(1)
        _self.ok_button.click()

    monkeypatch.setattr(TableEditDialog, "exec", exec_table)
    results = workflow.get_additional_info(factory, options, pretask_results)
    assert (
        results["title_pages"]["1234"] == "1234_2.jp2"
    ), f"all results are {results}"
