from unittest.mock import Mock, MagicMock

import pytest
from uiucprescon.packager.packages import collection
from speedwagon.workflows import title_page_selection
from PyQt5 import QtWidgets, QtCore


class TestFileSelectDelegate:
    @pytest.fixture
    def delegate(self, qtbot):
        return title_page_selection.FileSelectDelegate(parent=None)

    def test_editor_is_combobox(self, delegate):

        assert isinstance(
            delegate.createEditor(None, None, None),
            QtWidgets.QComboBox
        )

    def test_set_data_to_title_page_if_already_set(self, delegate):
        combo_box = QtWidgets.QComboBox()

        def get_data(role):
            if role == QtCore.Qt.UserRole:
                object_record = collection.PackageObject()
                object_record.component_metadata[
                    collection.Metadata.TITLE_PAGE
                ] = "file2.jp2"
                item = collection.Item(object_record)
                instance = collection.Instantiation(
                    parent=item,
                    files=[
                        "file1.jp2",
                        "file2.jp2",
                        "file3.jp2",
                    ]
                )
                return object_record

        index = MagicMock()
        index.data = get_data
        delegate.setEditorData(combo_box, index)
        assert combo_box.currentText() == "file2.jp2"

    def test_set_data_to_first_file_if_no_title_page_set(self, delegate):
        combo_box = QtWidgets.QComboBox()

        def get_data(role):
            if role == QtCore.Qt.UserRole:
                object_record = collection.PackageObject()
                item = collection.Item(object_record)
                instance = collection.Instantiation(
                    parent=item,
                    files=[
                        "file1.jp2",
                        "file2.jp2",
                        "file3.jp2",
                    ]
                )
                return object_record

        index = MagicMock()
        index.data = get_data
        delegate.setEditorData(combo_box, index)
        assert combo_box.currentText() == "file1.jp2"
