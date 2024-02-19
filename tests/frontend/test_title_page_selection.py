# from unittest.mock import Mock, MagicMock
#
# import pytest
# from uiucprescon.packager.packages import collection
#
# QtCore = pytest.importorskip("PySide6.QtCore")
# QtWidgets = pytest.importorskip("PySide6.QtWidgets")
#
# from speedwagon.frontend.qtwidgets.dialog import title_page_selection
#
#
# class TestFileSelectDelegate:
#     @pytest.fixture
#     def delegate(self, qtbot):
#         return title_page_selection.FileSelectDelegate(parent=None)
#
#     def test_editor_is_combobox(self, delegate):
#
#         assert isinstance(
#             delegate.createEditor(None, None, None),
#             QtWidgets.QComboBox
#         )
#
#     @pytest.mark.filterwarnings(
#         "ignore:Use get_files instead:DeprecationWarning")
#     def test_set_data_to_title_page_if_already_set(self, delegate):
#         combo_box = QtWidgets.QComboBox()
#
#         def get_data(role):
#             if role == QtCore.Qt.UserRole:
#                 object_record = collection.PackageObject()
#                 object_record.component_metadata[
#                     collection.Metadata.TITLE_PAGE
#                 ] = "file2.jp2"
#                 item = collection.Item(object_record)
#                 instance = collection.Instantiation(
#                     parent=item,
#                     files=[
#                         "file1.jp2",
#                         "file2.jp2",
#                         "file3.jp2",
#                     ]
#                 )
#                 return object_record
#
#         index = MagicMock()
#         index.data = get_data
#         delegate.setEditorData(combo_box, index)
#         assert combo_box.currentText() == "file2.jp2"
#
#     @pytest.mark.filterwarnings(
#         "ignore:Use get_files instead:DeprecationWarning")
#     def test_set_data_to_first_file_if_no_title_page_set(self, delegate):
#         combo_box = QtWidgets.QComboBox()
#
#         def get_data(role):
#             if role == QtCore.Qt.UserRole:
#                 object_record = collection.PackageObject()
#                 item = collection.Item(object_record)
#                 instance = collection.Instantiation(
#                     parent=item,
#                     files=[
#                         "file1.jp2",
#                         "file2.jp2",
#                         "file3.jp2",
#                     ]
#                 )
#                 return object_record
#
#         index = MagicMock()
#         index.data = get_data
#         delegate.setEditorData(combo_box, index)
#         assert combo_box.currentText() == "file1.jp2"
#
#     def test_set_title_page(self, delegate):
#         combo_box = QtWidgets.QComboBox()
#         files = [
#             "file1.jp2",
#             "file2.jp2",
#             "file3.jp2",
#         ]
#         for file_name in files:
#             combo_box.addItem(file_name)
#
#         combo_box.setCurrentText("file2.jp2")
#         model = Mock()
#
#         object_record = collection.PackageObject()
#         item = collection.Item(object_record)
#         instance = collection.Instantiation(
#             parent=item,
#             files=files
#         )
#
#         def get_data(index, role):
#             if role == QtCore.Qt.UserRole:
#                 return object_record
#
#         mock_index = MagicMock()
#         model.data = get_data
#         delegate.setModelData(combo_box, model, mock_index)
#         assert \
#             object_record.metadata[collection.Metadata.TITLE_PAGE] == \
#             "file2.jp2"
#
#
# class TestPackagesModel:
#     @pytest.fixture()
#     def model(self, request):
#         marker = request.node.get_closest_marker("model_data")
#         if marker is None:
#             amount = 0
#         else:
#             amount = marker.kwargs.get("amount", 0)
#         packages = []
#         for i in range(amount):
#             object_record = collection.PackageObject()
#             packages.append(object_record)
#
#         model = title_page_selection.PackagesModel(packages)
#         return model
#
#     def test_number_of_columns_match_number_of_fields(self, model):
#         assert model.columnCount() == len(model.fields)
#
#     @pytest.mark.model_data(amount=42)
#     def test_row_count(self, model):
#         assert model.rowCount() == 42
#
#     @pytest.mark.model_data(amount=0)
#     def test_row_count_empty(self, model):
#         assert model.rowCount() == 0
#
#     @pytest.mark.parametrize(
#         "index",
#         [i for i in range(len(title_page_selection.PackagesModel.fields))]
#     )
#     def test_header_data(self, model, index):
#         assert model.fields[index].column_header == \
#                model.headerData(index, orientation=QtCore.Qt.Horizontal)
#
#     def test_header_data_invalid_index_is_empty_string(self, model):
#         invalid_index = len(title_page_selection.PackagesModel.fields) + 1
#
#         assert model.headerData(
#             invalid_index, orientation=QtCore.Qt.Horizontal
#         ) == ""
#
#     def test_data_user_role(self):
#         packages = [
#             collection.PackageObject()
#         ]
#         model = title_page_selection.PackagesModel(packages)
#         index = model.index(0, 0)
#         data = model.data(index, role=QtCore.Qt.UserRole)
#         assert data == packages[0]
#
#     def test_data_display_role(self):
#         package = collection.PackageObject()
#         package.component_metadata[collection.Metadata.ID] = "page1.jpg"
#         packages = [
#             package
#         ]
#         model = title_page_selection.PackagesModel(packages)
#         index = model.index(0, 0)
#         data = model.data(index, role=QtCore.Qt.DisplayRole)
#         assert data == "page1.jpg"
#
#     def test_data_display_role_empty(self):
#         packages = [
#             collection.PackageObject()
#         ]
#         model = title_page_selection.PackagesModel(packages)
#         index = model.index(0, 0)
#         data = model.data(index, role=QtCore.Qt.DisplayRole)
#         assert data == ""
#
#     def test_title_page_flags_editable(self):
#         package = collection.PackageObject()
#         package.component_metadata[collection.Metadata.TITLE_PAGE] = \
#             "page1.jpg"
#
#         packages = [
#             package
#         ]
#
#         model = title_page_selection.PackagesModel(packages)
#         index = model.index(0, 1)
#         res = model.flags(index)
#         assert res == QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled
