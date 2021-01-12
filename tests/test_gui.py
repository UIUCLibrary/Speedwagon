# from speedwagon import
from unittest.mock import Mock
import webbrowser
import speedwagon.startup
import speedwagon.gui


def test_show_help_open_web(qtbot, monkeypatch):
    mock_work_manager = Mock()
    main_window = speedwagon.gui.MainWindow(mock_work_manager)

    def mock_open_new(url, *args, **kwargs):
        assert "http" in url

    with monkeypatch.context() as e:
        e.setattr(webbrowser, "open_new", mock_open_new)
        main_window.show_help()
