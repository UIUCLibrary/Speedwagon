from unittest import mock
from unittest.mock import Mock, MagicMock, patch, call
import yaml
import pytest

QtCore = pytest.importorskip("PySide6.QtCore")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from speedwagon.frontend.qtwidgets import tabs

class TestTabsYaml:
    @pytest.mark.parametrize("exception_type", [
        FileNotFoundError,
        AttributeError,
        yaml.YAMLError,
    ])
    def test_read_tabs_yaml_errors(self, monkeypatch, exception_type):
        import os.path
        with patch(
                'speedwagon.frontend.qtwidgets.tabs.open',
                mock.mock_open()
        ):
            monkeypatch.setattr(os.path, "getsize", lambda x: 1)
            monkeypatch.setattr(yaml, "load", Mock(side_effect=exception_type))
            with pytest.raises(exception_type) as e:
                list(tabs.read_tabs_yaml('tabs.yml'))
            assert e.type == exception_type

    def test_read_tabs_yaml(self, monkeypatch):
        sample_text = """my stuff:
- Convert CaptureOne Preservation TIFF to Digital Library Access JP2
- Convert CaptureOne TIFF to Digital Library Compound Object
- Convert CaptureOne TIFF to Digital Library Compound Object and HathiTrust
- Convert CaptureOne TIFF to Hathi TIFF package
        """
        import os
        monkeypatch.setattr(os.path, 'getsize', lambda x: 1)
        with patch('speedwagon.frontend.qtwidgets.tabs.open',
                   mock.mock_open(read_data=sample_text)):
            tab_data = list(tabs.read_tabs_yaml('tabs.yml'))
            assert len(tab_data) == 1 and \
                   len(tab_data[0][1].workflows) == 4

    def test_write_tabs_yaml(self):
        sample_tab_data = [tabs.TabData("dummy_tab", MagicMock())]
        with patch(
                'speedwagon.frontend.qtwidgets.tabs.open',
                mock.mock_open()
        ) as m:
            tabs.write_tabs_yaml("tabs.yml", sample_tab_data)
            assert m.called is True
        handle = m()
        handle.write.assert_has_calls([call('dummy_tab: []\n')])

