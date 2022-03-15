import pytest
from PySide6 import QtWidgets, QtCore

import speedwagon.workflow
import speedwagon.widgets
import speedwagon.models


class TestDelegateSelection:
    @pytest.fixture
    def model(self):
        return speedwagon.models.ToolOptionsModel4(data=[
            speedwagon.workflow.FileSelectData('Spam'),
        ])

    @pytest.fixture
    def index(
            self,
            qtbot,
            model: speedwagon.models.ToolOptionsModel4):
        return model.createIndex(0, 0)

    @pytest.fixture
    def delegate_widget(self):
        return speedwagon.widgets.QtWidgetDelegateSelection()

    @pytest.fixture
    def editor(
            self,
            qtbot,
            index,
            delegate_widget,
            model: speedwagon.models.ToolOptionsModel4
    ) -> speedwagon.widgets.FileSelectWidget:

        parent = QtWidgets.QWidget()
        options = QtWidgets.QStyleOptionViewItem()
        yield delegate_widget.createEditor(parent, options, index)

    def test_returns_a_qt_widget(
            self,
            qtbot,
            index,
    ):
        delegate_widget = speedwagon.widgets.QtWidgetDelegateSelection()
        assert isinstance(
            delegate_widget.createEditor(
                parent=QtWidgets.QWidget(),
                option=QtWidgets.QStyleOptionViewItem(),
                index=index
            ),
            QtWidgets.QWidget
        )

    def test_setting_model_data(
            self,
            qtbot,
            index,
            editor: speedwagon.widgets.FileSelectWidget,
            delegate_widget: speedwagon.widgets.QtWidgetDelegateSelection,
            model: speedwagon.models.ToolOptionsModel4
    ):
        starting_value = model.data(index, role=QtCore.Qt.DisplayRole)

        editor.data = "Dummy"
        delegate_widget.setModelData(editor, model, index)
        ending_value = model.data(index, role=QtCore.Qt.DisplayRole)

        assert starting_value is None and ending_value == "Dummy"

    def test_setting_editor_data(
            self,
            qtbot,
            index,
            delegate_widget: speedwagon.widgets.QtWidgetDelegateSelection,
            model: speedwagon.models.ToolOptionsModel4
    ):
        model.setData(index, "Dummy")
        parent = QtWidgets.QWidget()
        new_editor: speedwagon.widgets.FileSystemItemSelectWidget = \
            delegate_widget.createEditor(
                parent,
                QtWidgets.QStyleOptionViewItem(),
                index,
            )
        delegate_widget.setEditorData(new_editor, index)
        assert new_editor.data == "Dummy"

    def test_warn_on_not_using_right_subclass(
            self,
            index: QtCore.QModelIndex,
            delegate_widget: speedwagon.widgets.QtWidgetDelegateSelection,
            model: speedwagon.models.ToolOptionsModel4
    ):
        model.setData(index, "Dummy")
        with pytest.warns(Warning):
            delegate_widget.setModelData(QtWidgets.QLineEdit(), model, index)


class TestDropDownWidget:
    def test_empty_widget_metadata(self, qtbot):
        widget = speedwagon.widgets.ComboWidget()
        assert isinstance(widget, QtWidgets.QWidget)

    def test_data_updating(self, qtbot):
        widget = speedwagon.widgets.ComboWidget(widget_metadata={
            "selections": ["spam", "bacon", "eggs"]
        })
        starting_data = widget.data
        widget.combo_box.setCurrentIndex(0)
        first_index_data = widget.data
        assert starting_data is None and first_index_data == "spam"

    def test_placeholder_text(self):
        widget = speedwagon.widgets.ComboWidget(widget_metadata={
            "selections": ["spam", "bacon", "eggs"],
            "placeholder_text": "Dummy"
        })
        assert widget.combo_box.placeholderText() == "Dummy"


class TestCheckBoxWidget:
    def test_empty_widget_metadata(self, qtbot):
        widget = speedwagon.widgets.CheckBoxWidget()
        assert isinstance(widget, QtWidgets.QWidget)

    def test_checking_changes_value(self, qtbot):
        widget = speedwagon.widgets.CheckBoxWidget()
        assert widget.data is False
        with qtbot.wait_signal(widget.dataChanged):
            widget.check_box.setCheckState(QtCore.Qt.Checked)
        assert widget.data is True


class TestFileSelectWidget:
    def test_empty_widget_metadata(self, qtbot):
        widget = speedwagon.widgets.FileSelectWidget()
        assert isinstance(widget, QtWidgets.QWidget)

    def test_browse_dir_valid(self, qtbot):
        widget = speedwagon.widgets.FileSelectWidget()
        fake_file_path = "/some/directory/file"
        with qtbot.wait_signal(widget.dataChanged):
            widget.browse_file(get_file_callback=lambda: fake_file_path)
        assert widget.data == fake_file_path

    def test_browse_dir_canceled(self, qtbot):
        widget = speedwagon.widgets.FileSelectWidget()
        widget.browse_file(get_file_callback=lambda: None)
        assert widget.data is None


class TestDirectorySelectWidget:
    def test_empty_widget_metadata(self, qtbot):
        widget = speedwagon.widgets.DirectorySelectWidget()
        assert isinstance(widget, QtWidgets.QWidget)

    def test_browse_dir_valid(self, qtbot):
        widget = speedwagon.widgets.DirectorySelectWidget()
        fake_directory = "/some/directory"
        with qtbot.wait_signal(widget.dataChanged):
            widget.browse_dir(get_file_callback=lambda: fake_directory)
        assert widget.data == fake_directory

    def test_browse_dir_canceled(self, qtbot):
        widget = speedwagon.widgets.DirectorySelectWidget()
        widget.browse_dir(get_file_callback=lambda: None)
        assert widget.data is None



#
# def test_init(qtbot):
#     dialog_box = QtWidgets.QDialog()
#     table = QtWidgets.QTableView(parent=dialog_box)
#     table.setEditTriggers(table.AllEditTriggers)
#     layout = QtWidgets.QVBoxLayout()
#     dialog_box.setLayout(layout)
#     dialog_box.layout().addWidget(table)
#     qtbot.addWidget(table)
#     spam_dir = speedwagon.widgets.FileSelectData('Spam')
#     spam_dir.placeholder_text = "Select a spam"
#
#     # user_args.append(spam_dir)
#
#     drop_down = speedwagon.widgets.DropDownSelection("Dummy")
#     # drop_down.value = "Option 2"
#     drop_down.placeholder_text = "Select an option"
#     drop_down.add_selection("Option 1")
#     drop_down.add_selection("Option 2")
#
#     # user_args.append(drop_down)
#
#     user_args = [
#         spam_dir,
#         drop_down
#
#     ]
#     model = speedwagon.models.ToolOptionsModel4(data=user_args)
#     table.setModel(model)
#     delegate = speedwagon.widgets.QtWidgetDelegateSelection()
#     table.setItemDelegate(delegate)
#     dialog_box.exec()
