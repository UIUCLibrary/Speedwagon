import typing
from typing import Any, List, Dict
from unittest.mock import Mock, MagicMock, patch, mock_open
import webbrowser

import pytest

import speedwagon.startup


import speedwagon.workflow
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QtGui = pytest.importorskip("PySide6.QtGui")
import speedwagon.config
from speedwagon.frontend.qtwidgets.tabs import WorkflowsTab3, ItemTabsWidget
from speedwagon.frontend.qtwidgets.models.options import load_job_settings_model


class TestMainWindow3:
    def test_updated_settings_uses_config_strategy(self, qtbot):
        window = speedwagon.frontend.qtwidgets.gui.MainWindow3()
        window.config_strategy = \
            Mock(speedwagon.config.config.AbsConfigSettings)

        window.update_settings()
        assert window.config_strategy.settings.called is True

    def test_debug_mode_reflected_in_window_title(self, qtbot):
        class DummyConfigSettings(speedwagon.config.config.AbsConfigSettings):
            def settings(self):
                return {"GLOBAL": {"debug": True}}
        window = speedwagon.frontend.qtwidgets.gui.MainWindow3()
        window.config_strategy = DummyConfigSettings()
        window.update_settings()
        assert "DEBUG" in window.windowTitle()
#
    def test_normal_mode_dose_not_have_debug_in_window_title_text(self, qtbot):
        window = speedwagon.frontend.qtwidgets.gui.MainWindow3()
        window.config_strategy = \
            Mock(
                speedwagon.config.config.AbsConfigSettings,
                settings=Mock(return_value={"debug": False})
            )
        window.update_settings()
        assert "DEBUG" not in window.windowTitle()

    def test_export_job_config_triggered_by_action_export_job(self, qtbot):
        window = speedwagon.frontend.qtwidgets.gui.MainWindow3()
        tab = WorkflowsTab3()
        window.tab_widget.add_tab(tab, "dummy")
        with qtbot.waitSignal(window.export_job_config):
            window.action_export_job.trigger()


def test_load_job_settings_model(qtbot):
    data = {
        'Source': '/Volumes/G-RAID with Thunderbolt/hathi_test/access/',
        'Check for page_data in meta.yml': True,
        'Check ALTO OCR xml files': True,
        'Check OCR xml files are utf-8': False
    }
    source = speedwagon.workflow.DirectorySelect("Source")

    check_page_data_option = \
        speedwagon.workflow.BooleanSelect("Check for page_data in meta.yml")
    check_page_data_option.value = False

    check_ocr_option = speedwagon.workflow.BooleanSelect("Check ALTO OCR xml files")
    check_ocr_option.value = True

    check_ocr_utf8_option = \
        speedwagon.workflow.BooleanSelect('Check OCR xml files are utf-8')
    check_ocr_utf8_option.value = False

    workflow_options = [
        source,
        check_page_data_option,
        check_ocr_option,
        check_ocr_utf8_option

    ]
    form = speedwagon.frontend.qtwidgets.widgets.DynamicForm()
    load_job_settings_model(data, form, workflow_options)
    assert form._background.widgets['Source'].data == '/Volumes/G-RAID with Thunderbolt/hathi_test/access/'


def test_load_items_with_choice(qtbot):
    data = {
        'Image File Type': 'JPEG 2000',
        'Language': 'English',
        'Path': None
    }
    form = speedwagon.frontend.qtwidgets.widgets.DynamicForm()

    package_type = speedwagon.workflow.ChoiceSelection("Image File Type")
    package_type.placeholder_text = "Select Image Format"
    package_type.add_selection("JPEG 2000")
    package_type.add_selection("TIFF")

    language_type = speedwagon.workflow.ChoiceSelection("Language")
    language_type.placeholder_text = "Select Language"
    language_type.add_selection("Dutch")
    language_type.add_selection("English")
    language_type.add_selection("French")
    language_type.add_selection("German")
    language_type.add_selection("Spanish")

    package_root_option = speedwagon.workflow.DirectorySelect("Path")

    workflow_options = [
        package_type,
        language_type,
        package_root_option
    ]

    load_job_settings_model(data, form, workflow_options)
    language_widget = form._background.widgets['Language']
    assert language_widget.data == 'English'
    assert language_widget.get_selections() == [
        'Dutch',
        'English',
        'French',
        'German',
        'Spanish'
    ]


class TestItemTabsWidget:
    def test_add_tab(self, qtbot):

        tabs_widget = ItemTabsWidget()
        dummy = QtWidgets.QWidget()
        assert tabs_widget.count() == 0
        tabs_widget.add_tab(dummy, "hello")

        text = [tabs_widget.tabs.tabText(r) for r in range(tabs_widget.count())]
        assert tabs_widget.count() == 1, f"Tabs found: {*text, }"

    def test_add_tab_to_model_adds_to_widget(self, qtbot):
        tabs_widget = ItemTabsWidget()
        model = tabs_widget.model()
        assert tabs_widget.count() == 0
        model.append_workflow_tab("Spam", [])
        assert tabs_widget.count() == 1

    def test_add_tab_widget(self, qtbot):
        tabs_widget = ItemTabsWidget()
        tabs_widget.add_workflows_tab("hello", [])
        assert tabs_widget.count() == 1

    def test_add_tab_widget_and_clear(self, qtbot):
        tabs_widget = ItemTabsWidget()
        tabs_widget.add_workflows_tab("hello", [])
        tabs_widget.clear_tabs()
        names = [tabs_widget.model().data(tabs_widget.model().index(row_id)) for row_id in range(tabs_widget.model().rowCount())]
        assert tabs_widget.count() == 0, f"Found tabs {*names, }"

    def test_append_workflow_to_model_and_clear_from_widget(self, qtbot):
        tabs_widget = ItemTabsWidget()
        model = tabs_widget.model()
        model.append_workflow_tab("Spam", [])
        assert tabs_widget.count() == 1
        tabs_widget.clear_tabs()
        assert tabs_widget.count() == 0

    def test_clear(self, qtbot):
        tabs_widget = ItemTabsWidget()
        dummy = QtWidgets.QWidget()
        tabs_widget.add_tab(dummy, "hello")
        assert tabs_widget.count() == 1
        tabs_widget.clear_tabs()
        assert tabs_widget.count() == 0

    def test_empty_current_tab_is_none(self, qtbot):
        tabs_widget = ItemTabsWidget()
        assert tabs_widget.current_tab is None
