from PyQt5 import QtWidgets, QtCore
from speedwagon.workflows import shared_custom_widgets


def test_folder_browse_widget_click(qtbot, monkeypatch):
    widget = shared_custom_widgets.FolderBrowseWidget()
    monkeypatch.setattr(QtWidgets.QFileDialog, "getExistingDirectory", lambda *args, **kwargs: "/sample/path")
    qtbot.addWidget(widget)
    assert len( widget.text_line.actions()) == 1
    x = widget.text_line.actions()[0]
    x.triggered.emit()
    assert widget.data == "/sample/path"
    assert widget.text_line.text() == "/sample/path"