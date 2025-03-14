import platform
import logging
from unittest.mock import Mock, patch, mock_open, MagicMock, ANY
import pytest
import speedwagon
import speedwagon.config
import sys
import typing
import warnings
QtCore = pytest.importorskip("PySide6.QtCore")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from speedwagon.frontend.qtwidgets.dialog import settings, dialogs
from speedwagon.frontend.qtwidgets import models
from speedwagon.frontend.qtwidgets.models.tabs import (
    AbsLoadTabDataModelStrategy,
    TabDataModelYAMLFileLoader,
)
if sys.version_info < (3, 10):
    import importlib_metadata as metadata
else:
    from importlib import metadata


class TestOpenSettings:
    def test_open_darwin_settings(self, monkeypatch):
        settings_directory = "some/settings/path"
        opening_strategy = settings.DarwinOpenSettings(settings_directory)
        import subprocess
        call = Mock()
        monkeypatch.setattr(subprocess, "call", call)
        opening_strategy.open()
        assert call.called is True and \
               settings_directory in call.call_args_list[0][0][0]

    def test_open_unsupported_settings(self, qtbot, monkeypatch):
        from PySide6 import QtWidgets
        settings_directory = "some/settings/path"
        opening_strategy = settings.UnsupportedOpenSettings(settings_directory)
        show = Mock()
        monkeypatch.setattr(QtWidgets.QMessageBox, "show", show)
        opening_strategy.open()
        assert show.called is True

    def test_open_windows_settings(self, monkeypatch):
        settings_directory = "some\\settings\\path"
        opening_strategy = settings.WindowsOpenSettings(settings_directory)
        import os
        startfile = Mock()
        if platform.system() != "Windows":
            setattr(os, "startfile", startfile)
        else:
            monkeypatch.setattr(os, "startfile", startfile)
        opening_strategy.open()
        assert startfile.called is True


class TestGlobalSettingsTab:
    def test_on_okay_not_modified(self, qtbot, monkeypatch):
        from PySide6 import QtWidgets
        mock_exec = Mock()
        monkeypatch.setattr(QtWidgets.QMessageBox, "exec", mock_exec)
        settings_tab = settings.GlobalSettingsTab()
        qtbot.addWidget(settings_tab)
        assert mock_exec.called is False

    def test_not_modified_from_init(self, qtbot):
        tab = settings.GlobalSettingsTab()
        assert tab.data_is_modified() is False

    def test_read_config_data_raises_if_no_config_file(self, qtbot):
        tab = settings.GlobalSettingsTab()
        tab.config_file = None
        with pytest.raises(FileNotFoundError):
            tab.read_config_data()

    def test_read_config_data_raises_if_config_file_is_invalid(self, monkeypatch, qtbot):
        tab = settings.GlobalSettingsTab()
        tab.config_file = "some invalid file"
        monkeypatch.setattr(settings.os.path, "exists", lambda path: False)
        with pytest.raises(FileNotFoundError):
            tab.read_config_data()


    def test_read_config_data(self, monkeypatch, mocker, qtbot):
        tab = settings.GlobalSettingsTab()
        tab.config_file = "some valid file"
        monkeypatch.setattr(
            settings.os.path,
            "exists",
            lambda path: path == "some valid file"
        )
        settings_model = models.SettingsModel()
        monkeypatch.setattr(
            settings,
            "build_setting_qt_model",
            lambda config_file: settings_model
        )
        table_set_model = mocker.spy(tab.settings_table, "setModel")
        tab.read_config_data()
        table_set_model.assert_called_once_with(settings_model)


    # @pytest.mark.parametrize("config_file, expect_file_written",
    #                          [
    #                              (None, False),
    #                              ("dummy.yml", True)
    #                          ])
    # def test_on_okay_modified(self, qtbot, monkeypatch, config_file,
    #                           expect_file_written):
    #     from PySide6 import QtWidgets
    #     from speedwagon.frontend.qtwidgets import models
    #     mock_exec = Mock()
    #     monkeypatch.setattr(QtWidgets.QMessageBox, "exec", mock_exec)
    #     monkeypatch.setattr(models, "serialize_settings_model", Mock())
    #     settings_tab = settings.GlobalSettingsTab()
    #     qtbot.addWidget(settings_tab)
    #     settings_tab.on_modified()
    #     settings_tab.config_file = config_file
    #     m = mock_open()
    #     with patch('builtins.open', m):
    #         settings_tab.on_okay()
    #     assert m.called is expect_file_written


class TestTabsConfigurationTab:
    @pytest.fixture()
    def config_tab(self, monkeypatch):
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            'get_tabs_file',
            lambda *_: 'dummy.yml'
        )
        return settings.TabsConfigurationTab()

    # @pytest.mark.parametrize("settings_location, writes_to_file", [
    #     ("setting_location", True),
    #     (None, False)
    # ])
    # def test_on_okay_modified(self, qtbot, monkeypatch, settings_location,
    #                           writes_to_file, config_tab):
    #
    #     from PySide6 import QtWidgets
    #
    #
    #     config_tab.settings_location = settings_location
    #     # from speedwagon.frontend.qtwidgets import tabs
    #     from speedwagon import config
    #     config_management_strategy = Mock(
    #         config.tabs.AbsTabsConfigDataManagement, name="AbsTabsConfigDataManagement")
    #     # write_tabs_yaml = Mock()
    #     mock_exec = Mock(name="message box exec")
    #     with monkeypatch.context() as mp:
    #
    #         mp.setattr(
    #             config_tab,
    #             "tab_config_management_strategy",
    #             Mock(return_value=config_management_strategy)
    #         )
    #         # mp.setattr(tabs, "write_tabs_yaml", write_tabs_yaml)
    #         mp.setattr(QtWidgets.QMessageBox, "exec", mock_exec)
    #         config_tab.on_okay()
    #
    #     assert \
    #         mock_exec.called is True and \
    #         config_management_strategy.save.called is writes_to_file, \
    #         f"mock_exec.called is {mock_exec.called}"

    def test_create_new_tab_set_modified_true(self, qtbot, monkeypatch, config_tab):
        with qtbot.wait_signal(config_tab.changes_made):
            with monkeypatch.context() as mp:
                mp.setattr(
                    settings.QtWidgets.QInputDialog,
                    "getText",
                    lambda *args, **kwargs: ("new tab", True)
                )
                qtbot.mouseClick(
                    config_tab.editor.new_tab_button,
                    QtCore.Qt.LeftButton
                )
        assert config_tab.data_is_modified() is True
    def test_revert_changes(self, qtbot, monkeypatch, config_tab):
        # Test if the changes made reverted to original start shows data not
        # modified
        with qtbot.wait_signal(config_tab.changes_made):
            with monkeypatch.context() as mp:
                mp.setattr(
                    settings.QtWidgets.QInputDialog,
                    "getText",
                    lambda *args, **kwargs: ("new tab", True)
                )
                qtbot.mouseClick(
                    config_tab.editor.new_tab_button,
                    QtCore.Qt.LeftButton
                )
        assert config_tab.data_is_modified() is True
        config_tab.editor.set_current_tab("new tab")
        with qtbot.wait_signal(config_tab.changes_made):
            qtbot.mouseClick(
                config_tab.editor.delete_current_tab_button,
                QtCore.Qt.LeftButton
            )
        assert config_tab.data_is_modified() is False

    # def test_tab_config_management_strategy_no_settings_location_raises(
    #     self,
    #     qtbot,
    #     config_tab
    # ):
    #     with pytest.raises(RuntimeError):
    #         config_tab.tab_config_management_strategy()

    def test_tab_config_management_strategy(self, qtbot, config_tab):
        config_tab.settings_location = "dummy.yml"
        assert isinstance(
            config_tab.tab_config_management_strategy(),
            speedwagon.config.tabs.AbsTabsConfigDataManagement
        )

    def test_load(self, qtbot, config_tab):
        strategy = Mock(AbsLoadTabDataModelStrategy)

        config_tab.load(strategy)
        assert strategy.load.called is True

    def test_load_tab_data_model_strategy_sets_editor(self, qtbot):
        tab = settings.TabsConfigurationTab()
        qtbot.addWidget(tab)
        mock_load_tab_data_model_strategy = Mock(name="load_tab_data_model_strategy")
        tab.load_tab_data_model_strategy = mock_load_tab_data_model_strategy
        assert tab.editor.load_tab_data_model_strategy == mock_load_tab_data_model_strategy

    def test_load_tab_data_model_strategy_get_from_editor(self, qtbot):
        tab = settings.TabsConfigurationTab()
        qtbot.addWidget(tab)
        mock_load_tab_data_model_strategy = Mock(name="load_tab_data_model_strategy")
        tab.editor.load_tab_data_model_strategy = mock_load_tab_data_model_strategy
        assert tab.load_tab_data_model_strategy == mock_load_tab_data_model_strategy

    # def test_on_okay_calls_save(self, qtbot, monkeypatch):
    #     tab = settings.TabsConfigurationTab()
    #     qtbot.addWidget(tab)
    #     tabs_config_data_management = Mock(
    #         spec_set=speedwagon.config.tabs.AbsTabsConfigDataManagement,
    #     )
    #     tab.tab_config_management_strategy = Mock(
    #         name="tab_config_management_strategy",
    #         return_value=tabs_config_data_management,
    #     )
    #     monkeypatch.setattr(settings.QtWidgets.QMessageBox, "exec", Mock(name="exec"))
    #     tab.on_okay()
    #     tabs_config_data_management.save.assert_called_once()

    # def test_on_okay_opens_dialog_box(
    #         self,
    #         qtbot,
    #         monkeypatch
    # ):
    #     tab = settings.TabsConfigurationTab()
    #     qtbot.addWidget(tab)
    #     tabs_config_data_management = Mock(
    #         spec_set=speedwagon.config.tabs.AbsTabsConfigDataManagement,
    #     )
    #     tab.tab_config_management_strategy = Mock(
    #         name="tab_config_management_strategy",
    #         return_value=tabs_config_data_management,
    #     )
    #     message_box_exec = Mock(name="QMessageBox.exec")
    #     monkeypatch.setattr(settings.QtWidgets.QMessageBox, "exec", message_box_exec)
    #     tab.on_okay()
    #     message_box_exec.assert_called_once()


class TestTabEditor:
    @pytest.fixture()
    def editor(self, monkeypatch):
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            'get_tabs_file',
            lambda *_: 'dummy.yml'
        )
        new_editor = settings.TabEditor()
        return new_editor

    def test_set_all_workflows_set_model(self, qtbot, editor):
        qtbot.addWidget(editor)
        mock_workflow = Mock()
        from speedwagon import job
        mock_workflow.__type__ = job.Workflow
        workflows = {
            '': mock_workflow
        }
        editor.all_workflows_list_view.setModel = Mock()
        editor.set_all_workflows()
        assert editor.all_workflows_list_view.setModel.called is True

    def test_create_new_tab(self, qtbot, monkeypatch, editor):
        qtbot.addWidget(editor)
        assert editor.selected_tab_combo_box.model().rowCount() == 0
        with monkeypatch.context() as mp:
            mp.setattr(
                settings.QtWidgets.QInputDialog,
                "getText",
                lambda *args, **kwargs: ("new tab", True)
            )
            qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)
        assert editor.selected_tab_combo_box.model().rowCount() == 1

    def test_create_new_tab_can_cancel(self, qtbot, monkeypatch, editor):
        qtbot.addWidget(editor)
        assert editor.selected_tab_combo_box.model().rowCount() == 0
        with monkeypatch.context() as mp:
            mp.setattr(
                settings.QtWidgets.QInputDialog,
                "getText",
                lambda *args, **kwargs: ("new tab", False)
            )
            qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)
        assert editor.selected_tab_combo_box.model().rowCount() == 0

    def test_create_new_tab_cannot_create_same_name_tabs(
            self,
            qtbot,
            monkeypatch,
            editor
    ):
        qtbot.addWidget(editor)
        with monkeypatch.context() as mp:

            mp.setattr(
                settings.QtWidgets.QInputDialog,
                "getText",
                lambda *args, **kwargs: ("my tab", True)
            )

            # Make sure that this can exit
            QMessageBox = Mock()
            QMessageBox.exec = \
                Mock(side_effect=lambda context=mp: context.setattr(
                         settings.QtWidgets.QInputDialog,
                         "getText",
                         lambda *args, **kwargs: ("new tab", False)
                     ))

            QMessageBox.name = 'QMessageBox'

            mp.setattr(
                settings.QtWidgets,
                "QMessageBox",
                Mock(return_value=QMessageBox)
            )

            # Add "my tab" the first time
            qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)

            # try to add "my tab" a second time
            qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)

            # Should bring up an error window
            assert QMessageBox.setWindowTitle.called is True

    def test_add_tab_changes_selection(self, qtbot, monkeypatch, editor):
        qtbot.addWidget(editor)
        with monkeypatch.context() as mp:
            mp.setattr(
                settings.QtWidgets.QInputDialog,
                "getText",
                lambda *args, **kwargs: ("new tab", True)
            )
            with qtbot.wait_signal(editor.changes_made):
                qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)
        assert editor.selected_tab_combo_box.currentText() == "new tab"

    def test_delete_tab(self, qtbot, monkeypatch, editor):
        qtbot.addWidget(editor)
        with monkeypatch.context() as mp:
            mp.setattr(
                settings.QtWidgets.QInputDialog,
                "getText",
                lambda *args, **kwargs: ("new tab", True)
            )
            qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)
        assert editor.selected_tab_combo_box.model().rowCount() == 1
        with qtbot.wait_signal(editor.changes_made):
            qtbot.mouseClick(
                editor.delete_current_tab_button,
                QtCore.Qt.LeftButton
            )

        assert editor.selected_tab_combo_box.model().rowCount() == 0

    def test_delete_everything(self, qtbot, monkeypatch, editor):
        qtbot.addWidget(editor)
        with monkeypatch.context() as mp:
            mp.setattr(
                settings.QtWidgets.QInputDialog,
                "getText",
                lambda *args, **kwargs: ("new tab", True)
            )
            qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)
        assert editor.selected_tab_combo_box.model().rowCount() == 1
        with qtbot.wait_signal(editor.changes_made):
            qtbot.mouseClick(
                editor.delete_current_tab_button,
                QtCore.Qt.LeftButton
            )

        assert editor.selected_tab_combo_box.model().rowCount() == 0
        with qtbot.wait_signal(editor.changes_made):
            qtbot.mouseClick(
                editor.delete_current_tab_button,
                QtCore.Qt.LeftButton
            )
        a = editor.tab_workflows_list_view.model()
        print(a.rowCount())
    def test_modified_by_add(self, qtbot, monkeypatch, editor):
        qtbot.addWidget(editor)
        def getText(*args, **kwargs):
            return "new name", True
        with qtbot.wait_signal(editor.changes_made):
            with monkeypatch.context() as ctx:
                ctx.setattr(settings.QtWidgets.QInputDialog, "getText", getText)
                qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)
        assert editor.modified is True

    def test_not_modified_if_deleted_newly_added_tab(
            self,
            qtbot,
            monkeypatch,
            editor
    ):
        qtbot.addWidget(editor)
        def getText(*args, **kwargs):
            return "new name", True

        with qtbot.wait_signal(editor.changes_made):
            with monkeypatch.context() as ctx:
                ctx.setattr(settings.QtWidgets.QInputDialog, "getText", getText)
                qtbot.mouseClick(editor.new_tab_button, QtCore.Qt.LeftButton)
        editor.set_current_tab("new name")
        with qtbot.wait_signal(editor.changes_made):
            assert editor.modified is True
            qtbot.mouseClick(editor.delete_current_tab_button, QtCore.Qt.LeftButton)
        assert editor.modified is False

    def test_workflow_switch_index(self, qtbot, editor):
        # Check what index is being called when selected tab combobox widget
        # value for is changed
        dialog_box = QtWidgets.QDialog()
        class DummyLoader(AbsLoadTabDataModelStrategy):
            def load(self, model: models.TabsTreeModel) -> None:
                class Spam1(speedwagon.Workflow):
                    name = "spam 1"

                class Spam2(speedwagon.Workflow):
                    name = "spam 2"

                class Spam3(speedwagon.Workflow):
                    name = "spam 3"

                model.append_workflow_tab("All", [Spam1, Spam2, Spam3])
                model.append_workflow_tab("Bacon", [Spam2])
                model.append_workflow_tab("Eggs", [Spam1])

        loader = DummyLoader()
        editor.all_workflows_list_view.setModel(editor._all_workflows_model)
        loader.load(editor.model)
        # editor._user_tabs_model.set_active("Bacon", True)
        # editor._user_tabs_model.set_active("Eggs", True)
        editor.selected_tab_combo_box.setCurrentIndex(0)
        with qtbot.wait_signal(editor.current_tab_index_changed) as e:
            editor.set_current_tab("Eggs")
        assert editor.model.data(editor.model.index(e.args[0].row())) == "Eggs"

    def test_add_workflow(self, qtbot, editor):
        class DummyLoader(AbsLoadTabDataModelStrategy):
            def load(self, model: models.TabsTreeModel) -> None:
                class Spam1(speedwagon.Workflow):
                    name = "spam 1"

                class Spam2(speedwagon.Workflow):
                    name = "spam 2"

                class Spam3(speedwagon.Workflow):
                    name = "spam 3"

                class Spam4(speedwagon.Workflow):
                    name = "spam 4"

                model.append_workflow_tab("All", [Spam1, Spam2, Spam3, Spam4])
                model.append_workflow_tab("Bacon", [Spam2])
                model.append_workflow_tab("Eggs", [Spam1])

        loader = DummyLoader()
        loader.load(editor.model)
        assert editor.model.rowCount() == 3
        assert editor.model.rowCount(parent=editor.model.index(0)) == 4
        editor.set_current_tab("Eggs")

        mo = editor.all_workflows_list_view.model()
        qtbot.mouseClick(
            editor.all_workflows_list_view.viewport(),
            QtCore.Qt.LeftButton,
            pos=editor.all_workflows_list_view.visualRect(mo.index(1,0)).center()
        )
        assert len(editor.all_workflows_list_view.selectedIndexes()) == 1
        assert editor.tab_workflows_list_view.model().rowCount() == 1
        qtbot.mouseClick(
            editor.add_items_button,
            QtCore.Qt.LeftButton,
        )
        assert editor.tab_workflows_list_view.model().rowCount() == 2

    def test_workflow_emits_changes(self, qtbot, editor):

        class DummyLoader(AbsLoadTabDataModelStrategy):
            def load(self, model: models.TabsTreeModel) -> None:
                class Spam1(speedwagon.Workflow):
                    name = "spam 1"

                class Spam2(speedwagon.Workflow):
                    name = "spam 2"

                class Spam3(speedwagon.Workflow):
                    name = "spam 3"

                class Spam4(speedwagon.Workflow):
                    name = "spam 4"

                model.append_workflow_tab("All", [Spam1, Spam2, Spam3, Spam4])
                model.append_workflow_tab("Bacon", [Spam2])
                model.append_workflow_tab("Eggs", [Spam1])

        loader = DummyLoader()
        loader.load(editor.model)
        assert editor.model.rowCount() == 3
        assert editor.model.rowCount(parent=editor.model.index(0)) == 4
        # editor.set_tab_visibility("Bacon", True)
        # editor.set_tab_visibility("Eggs", True)
        editor.set_current_tab("Eggs")

        qtbot.mouseClick(
            editor.all_workflows_list_view.viewport(),
            QtCore.Qt.LeftButton,
            pos=editor.all_workflows_list_view.visualRect(
                editor.all_workflows_list_view.model().index(1,0)
            ).center()
        )
        with qtbot.wait_signal(editor.changes_made):
            qtbot.mouseClick(
                editor.add_items_button,
                QtCore.Qt.LeftButton,
            )
        editor.model.reset_modified()
        assert editor.modified is False

        qtbot.mouseClick(
            editor.tab_workflows_list_view.viewport(),
            QtCore.Qt.LeftButton,
            pos=editor.tab_workflows_list_view.visualRect(
                editor.tab_workflows_list_view.model().index(1,0)
            ).center()
        )
        with qtbot.wait_signal(editor.changes_made):
            qtbot.mouseClick(
                editor.remove_items_button,
                QtCore.Qt.LeftButton,
            )
        assert editor.modified is True

    def test_workflow_revert_no_modified(self, qtbot, editor):
        dialog = QtWidgets.QDialog()
        editor.setParent(dialog)
        class DummyLoader(AbsLoadTabDataModelStrategy):
            def load(self, model: models.TabsTreeModel) -> None:
                class Spam1(speedwagon.Workflow):
                    name = "spam 1"

                class Spam2(speedwagon.Workflow):
                    name = "spam 2"

                class Spam3(speedwagon.Workflow):
                    name = "spam 3"

                class Spam4(speedwagon.Workflow):
                    name = "spam 4"

                model.append_workflow_tab("All", [Spam1, Spam2, Spam3, Spam4])
                model.append_workflow_tab("Bacon", [Spam2])
                model.append_workflow_tab("Eggs", [Spam1])
                model.reset_modified()

        loader = DummyLoader()
        loader.load(editor.model)
        assert editor.model.rowCount() == 3
        assert editor.model.rowCount(parent=editor.model.index(0)) == 4
        # editor.set_tab_visibility("Bacon", True)
        # editor.set_tab_visibility("Eggs", True)
        editor.set_current_tab("Eggs")

        qtbot.mouseClick(
            editor.all_workflows_list_view.viewport(),
            QtCore.Qt.LeftButton,
            pos=editor.all_workflows_list_view.visualRect(
                editor.all_workflows_list_view.model().index(1,0)
            ).center()
        )
        with qtbot.wait_signal(editor.changes_made):
            qtbot.mouseClick(
                editor.add_items_button,
                QtCore.Qt.LeftButton,
            )
        assert editor.modified is True

        qtbot.mouseClick(
            editor.tab_workflows_list_view.viewport(),
            QtCore.Qt.LeftButton,
            pos=editor.tab_workflows_list_view.visualRect(
                editor.tab_workflows_list_view.model().index(1,0)
            ).center()
        )
        with qtbot.wait_signal(editor.changes_made):
            qtbot.mouseClick(
                editor.remove_items_button,
                QtCore.Qt.LeftButton,
            )
        assert editor.modified is False


class TestSettingsBuilder2:

    @pytest.fixture()
    def builder(self, monkeypatch):
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            'get_tabs_file',
            lambda *_: 'dummy.yml'
        )
        return settings.SettingsBuilder()

    def test_accepted(self, qtbot):
        builder = settings.SettingsBuilder()
        dialog = builder.build()
        ok = dialog.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        ok.setEnabled(True)
        qtbot.add_widget(dialog)
        with qtbot.wait_signal(dialog.accepted):
            qtbot.mouseClick(ok, QtCore.Qt.LeftButton)

    def test_rejected(self, qtbot):
        builder = settings.SettingsBuilder()
        dialog = builder.build()
        cancel_button = dialog.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        qtbot.add_widget(dialog)
        with qtbot.wait_signal(dialog.rejected):
            qtbot.mouseClick(cancel_button, QtCore.Qt.LeftButton)

    def test_add_tab_increases_tabs(self, qtbot, builder):
        item = settings.TabsConfigurationTab()
        builder.add_tab("spam", item)
        dialog = builder.build()
        assert dialog.tabs_widget.count() == 1

    def test_save_callback_called(self, qtbot, builder):
        on_save_callback = Mock()
        builder.add_on_save_callback(on_save_callback)
        item = settings.TabsConfigurationTab()
        builder.add_tab("spam", item)
        dialog = builder.build()
        ok = dialog.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        ok.setEnabled(True)
        qtbot.add_widget(dialog)
        with qtbot.wait_signal(dialog.accepted):
            qtbot.mouseClick(ok, QtCore.Qt.LeftButton)
        assert on_save_callback.called is True

    # def test_add_on_save_callback_returns_same_widgets(self, qtbot, builder):
    #     item = settings.TabsConfigurationTab()
    #     builder.add_tab("spam", item)
    #
    #     # def my_callback(parent, tab_widgets: typing.Dict[str, settings.SettingsTab]):
    #     #     assert tab_widgets['spam'] == item
    #     my_callback = Mock()
    #     builder.add_on_save_callback(my_callback)
    #     dialog = builder.build()
    #     ok = dialog.button_box.button(
    #         QtWidgets.QDialogButtonBox.StandardButton.Ok
    #     )
    #     ok.setEnabled(True)
    #     qtbot.add_widget(dialog)
    #     with qtbot.wait_signal(dialog.accepted):
    #         qtbot.mouseClick(ok, QtCore.Qt.LeftButton)

    # @pytest.mark.parametrize(
    #     "settings_widget",
    #     [
    #         settings.TabsConfigurationTab,
    #         settings.GlobalSettingsTab,
    #         settings.PluginsTab
    #     ]
    # )
    # def test_get_data(self, qtbot, settings_widget, builder):
    #     item = settings_widget()
    #     builder.add_tab("spam", item)
    #     #
    #     # def my_callback(parent, tab_widgets: typing.Dict[str, settings.SettingsTab]):
    #     #     assert isinstance(tab_widgets['spam'].get_data(), dict)
    #     my_callback = Mock()
    #     builder.add_on_save_callback(my_callback)
    #     dialog = builder.build()
    #     ok = dialog.button_box.button(
    #         QtWidgets.QDialogButtonBox.StandardButton.Ok
    #     )
    #     ok.setEnabled(True)
    #     qtbot.add_widget(dialog)
    #     with qtbot.wait_signal(dialog.accepted):
    #         qtbot.mouseClick(ok, QtCore.Qt.LeftButton)
    #     my_callback.assert_called_once()

class TestWorkflowProgress:
    @pytest.mark.parametrize(
        "button_type, expected_active",
        [
            (QtWidgets.QDialogButtonBox.Cancel, False),
            (QtWidgets.QDialogButtonBox.Close, True)
        ]
    )
    def test_default_buttons(self, qtbot, button_type, expected_active):
        progress_dialog = dialogs.WorkflowProgress()
        qtbot.addWidget(progress_dialog)
        assert progress_dialog.button_box.button(button_type).isEnabled() is \
               expected_active

    def test_get_console(self, qtbot):
        progress_dialog = dialogs.WorkflowProgress()
        progress_dialog.write_to_console("spam")
        assert "spam" in progress_dialog.get_console_content()

    def test_start_changes_state_to_working(self, qtbot):
        progress_dialog = dialogs.WorkflowProgress()
        assert progress_dialog.current_state == "idle"
        progress_dialog.start()
        assert progress_dialog.current_state == "working"

    def test_stop_changes_working_state_to_stopping(self, qtbot):
        progress_dialog = dialogs.WorkflowProgress()
        progress_dialog.start()
        assert progress_dialog.current_state == "working"
        progress_dialog.stop()
        assert progress_dialog.current_state == "stopping"

    def test_failed_changes_working_state_to_failed(self, qtbot):
        progress_dialog = dialogs.WorkflowProgress()
        progress_dialog.start()
        assert progress_dialog.current_state == "working"
        progress_dialog.failed()
        assert progress_dialog.current_state == "failed"

    def test_cancel_completed_changes_stopping_state_to_aborted(self, qtbot):
        progress_dialog = dialogs.WorkflowProgress()
        progress_dialog.start()
        assert progress_dialog.current_state == "working"
        progress_dialog.stop()
        progress_dialog.cancel_completed()
        assert progress_dialog.current_state == "aborted"

    def test_success_completed_chances_status_to_done(self, qtbot):
        progress_dialog = dialogs.WorkflowProgress()
        progress_dialog.start()
        progress_dialog.success_completed()
        assert progress_dialog.current_state == "done"


class TestWorkflowProgressGui:
    def test_remove_log_handles(self, qtbot):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        progress_dialog = dialogs.WorkflowProgressGui()
        qtbot.add_widget(progress_dialog)
        progress_dialog.attach_logger(logger)
        progress_dialog.remove_log_handles()
        logger.info("Some message")
        progress_dialog.flush()
        assert "Some message" not in progress_dialog.get_console_content()

    def test_attach_logger(self, qtbot):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        progress_dialog = dialogs.WorkflowProgressGui()
        qtbot.add_widget(progress_dialog)
        progress_dialog.attach_logger(logger)
        try:
            logger.info("Some message")
            progress_dialog.flush()
            assert "Some message" in progress_dialog.get_console_content()
        finally:
            progress_dialog.remove_log_handles()

    def test_write_html_block_to_console(self, qtbot):
        progress_dialog = dialogs.WorkflowProgressGui()
        qtbot.add_widget(progress_dialog)
        progress_dialog.write_html_block_to_console("<h1>hello</h1>")
        assert "hello" in progress_dialog.get_console_content()


class TestWorkflowProgressState:
    @pytest.mark.parametrize(
        "button_clicked, event_called",
        [
            (dialogs.QtWidgets.QMessageBox.Yes, "accept"),
            (dialogs.QtWidgets.QMessageBox.No, "ignore"),
        ]
    )
    def test_event_called_based_on_button_press(
            self,
            qtbot,
            monkeypatch,
            button_clicked,
            event_called
    ):
        context = Mock()
        state = dialogs.WorkflowProgressStateWorking(context)
        event = Mock()
        exec_ = Mock(return_value=button_clicked)
        monkeypatch.setattr(dialogs.QtWidgets.QMessageBox, "exec", exec_)
        state.close_dialog(event)
        assert getattr(event, event_called).called is True

    @pytest.mark.parametrize(
        "state_class,command",
        [
            (dialogs.WorkflowProgressStateWorking, "start"),
            (dialogs.WorkflowProgressStateStopping, "start"),
            (dialogs.WorkflowProgressStateAborted, "stop"),
            (dialogs.WorkflowProgressStateFailed, "stop"),
            (dialogs.WorkflowProgressStateDone, "stop"),
        ]
    )
    def test_warnings(self, state_class, command):
        with pytest.warns(Warning) as record:
            state = state_class(context=Mock())
            getattr(state, command)()
        assert len(record) > 0

class TestWorkflowProgressStateStopping:
    def test_stopping_produces_a_warning(self, qtbot, monkeypatch):
        context = dialogs.WorkflowProgress()
        mock_dialog = Mock(
            Icon = Mock(name="Icon", Information = ""),
            StandardButton=Mock(name="StandardButton", Yes=1, No=0)
        )
        state = dialogs.WorkflowProgressStateStopping(context)
        monkeypatch.setattr(QtWidgets, "QMessageBox", mock_dialog)
        with pytest.warns(UserWarning):
            state.stop()


class TestWorkflowProgressStateIdle:
    def test_stopping_produces_a_warning(self, qtbot):
        context = dialogs.WorkflowProgress()
        state = dialogs.WorkflowProgressStateIdle(context)
        with pytest.warns(UserWarning):
            state.stop()


# class TestConfigFileSave:
#     def test_uses_AbsSaveStrategy(self, qtbot):
#         save_strategy = Mock(
#             settings.AbsSaveStrategy,
#             serialize_data=Mock(return_value="some data")
#         )
#         save_strategy.write_file = Mock()
#         saver = settings.ConfigFileSaver(save_strategy, "some_file.txt")
#         saver.save()
#         save_strategy.write_file.assert_called_once_with(
#             "some data",
#             "some_file.txt"
#         )


# def test_multisaver_child_save_methods_called():
#     saver = settings.MultiSaver()
#     dummy_saver = Mock(settings.AbsConfigSaver2)
#     saver.config_savers.append(dummy_saver)
#     saver.save()
#     dummy_saver.save.assert_called_once()


# class TestCallbackSaver:
#     def test_save(self):
#         save_data_callback_func = Mock()
#         saver = settings.CallbackSaver(save_data_callback_func=save_data_callback_func)
#         saver.save()
#         save_data_callback_func.assert_called_once_with()


@pytest.mark.parametrize(
    'func_name', [
        'data_is_modified',
        'get_data'
    ]
)
def test_data_unimplemented_functions_raises_not_implemented(
        func_name,
        qtbot
):
    new_tab = settings.SettingsTab()
    with pytest.raises(NotImplementedError):
        getattr(new_tab, func_name)()

class TestPluginsTab:
    def test_not_modified_from_init(self, qtbot):
        tab = settings.PluginsTab()
        assert tab.data_is_modified() is False

    def test_load(self, qtbot, mocker, monkeypatch):
        data = """
[PLUGINS.mysampleplugin]
myworkflow = True
"""
        with patch(
                'configparser.open',
                mock_open(read_data=data)
        ):
            config_file = "config.ini"
            tab = settings.PluginsTab()
            entry_point = Mock(
                metadata.EntryPoint,
                name="EntryPoint",
                module="mysampleplugin"
            )
            entry_point.name = "myworkflow"
            add_entry_point = mocker.spy(
                tab.plugins_activation.model,
                "add_entry_point"
            )
            with monkeypatch.context() as mp:
                mp.setattr(
                    settings.metadata,
                    "entry_points",
                    lambda *_, **__: [entry_point]
                )
                tab.load(config_file)
            add_entry_point.assert_called_once_with(entry_point, True)


class TestSettingsDialog:
    @pytest.fixture()
    def plugin_tab(self, monkeypatch):
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            'get_tabs_file',
            lambda *_: 'dummy.yml'
        )
        return settings.TabsConfigurationTab()
    def test_okay_button_active_only_when_modified(self, qtbot):
        dialog_box = settings.SettingsDialog()

        dialog_tab = settings.GlobalSettingsTab()
        dialog_tab.model.add_setting("spam", "yes")

        dialog_box.add_tab(dialog_tab, "dummy")

        ok_enabled_before_modified = dialog_box.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).isEnabled()

        with qtbot.wait_signal(dialog_tab.changes_made):
            dialog_tab.model.setData(dialog_tab.model.index(0, 1), "no")

        ok_enabled_after_modified = dialog_box.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).isEnabled()

        assert all(
            (
                ok_enabled_before_modified is False,
                ok_enabled_after_modified is True,
            )
        )

    def test_revert_new_tab_plugins_state_buttons(self, qtbot, monkeypatch, plugin_tab):
        dialog_box = settings.SettingsDialog()

        dialog_box.add_tab(plugin_tab, "Plugins")
        ok_enabled_before_modified = dialog_box.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).isEnabled()
        with qtbot.wait_signal(dialog_box.changes_made):
            with monkeypatch.context() as mp:
                mp.setattr(
                    settings.QtWidgets.QInputDialog,
                    "getText",
                    lambda *args, **kwargs: ("new tab", True)
                )
                qtbot.mouseClick(
                    plugin_tab.editor.new_tab_button,
                    QtCore.Qt.LeftButton
                )
        ok_enabled_after_modified = dialog_box.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).isEnabled()
        with qtbot.wait_signal(dialog_box.changes_made):
            qtbot.mouseClick(
                plugin_tab.editor.delete_current_tab_button,
                QtCore.Qt.LeftButton
            )
        ok_enabled_after_reverted = dialog_box.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).isEnabled()

        expected = {
            "Ok button enabled initially": False,
            "Ok button enabled after modifying": True,
            "Ok button enabled after reverting": False
        }

        actual = {
            "Ok button enabled initially": ok_enabled_before_modified,
            "Ok button enabled after modifying": ok_enabled_after_modified,
            "Ok button enabled after reverting": ok_enabled_after_reverted
        }
        assert expected == actual
    def test_revert_add_workflows_plugins_state_buttons(self, qtbot, monkeypatch, plugin_tab):
        dialog_box = settings.SettingsDialog()
        dialog_box.add_tab(plugin_tab, "Plugins")
        with qtbot.wait_signal(dialog_box.changes_made):
            with monkeypatch.context() as mp:
                mp.setattr(
                    settings.QtWidgets.QInputDialog,
                    "getText",
                    lambda *args, **kwargs: ("new tab", True)
                )
                qtbot.mouseClick(
                    plugin_tab.editor.new_tab_button,
                    QtCore.Qt.LeftButton
                )
        with qtbot.wait_signal(plugin_tab.editor.model.dataChanged):
            plugin_tab.editor.model.reset_modified()
        ok_enabled_before_modified = dialog_box.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).isEnabled()
        # ok_enabled_after_modified = dialog_box.button_box.button(
        #     QtWidgets.QDialogButtonBox.StandardButton.Ok
        # ).isEnabled()
        # with qtbot.wait_signal(dialog_box.changes_made):
        #     qtbot.mouseClick(
        #         plugin_tab.editor.delete_current_tab_button,
        #         QtCore.Qt.LeftButton
        #     )
        # ok_enabled_after_reverted = dialog_box.button_box.button(
        #     QtWidgets.QDialogButtonBox.StandardButton.Ok
        # ).isEnabled()

        assert all(
            (
                ok_enabled_before_modified is False,
                # ok_enabled_after_modified is True,
                # ok_enabled_after_reverted is False,
            )
        )
    # dialog_box.exec()

class TestTabDataModelYAMLFileLoader:
    @pytest.fixture()
    def tab_widget(self, monkeypatch):
        monkeypatch.setattr(
            speedwagon.config.StandardConfigFileLocator,
            'get_tabs_file',
            lambda *_: 'dummy.yml'
        )
        return settings.TabEditor()
    def test_prep_data(self, monkeypatch):
        def available_workflows():
            return {}
        monkeypatch.setattr(speedwagon.job, "available_workflows", available_workflows)
        loader = TabDataModelYAMLFileLoader()
        class DummyStrategy(speedwagon.config.tabs.AbsTabsConfigDataManagement):
            def data(self):
                return [
                    Mock(workflow_names=["spam"])
                ]
            def save(self, tabs):
                pass

        assert "All" in loader.prep_data(DummyStrategy())

    def test_with_no_file_is_no_op(self, qtbot, tab_widget):
        loader = TabDataModelYAMLFileLoader()

        loader.load(tab_widget)
        loader.yml_file = None

        before_row_count = tab_widget.model.rowCount()
        loader.load(tab_widget)
        after_load_row_count = tab_widget.model.rowCount()
        expected = {
            "before loading model row count": 0,
            "after loading model row count": 0
        }
        actual = {
            "before loading model row count": before_row_count,
            "after loading model row count": after_load_row_count
        }
        assert expected == actual

    def test_load(self, qtbot):
        class BaconWorkflow(speedwagon.Workflow):
            name = "Bacon"
        loader = TabDataModelYAMLFileLoader()
        loader.prep_data = Mock(return_value={'Spam': [BaconWorkflow]})
        model = models.TabsTreeModel()
        loader.yml_file = "dummy.yml"

        before_row_count = model.rowCount()
        loader.load(model)
        after_load_row_count = model.rowCount()
        expected = {
            "before loading model row count": 0,
            "after loading model row count": 1
        }
        actual = {
            "before loading model row count": before_row_count,
            "after loading model row count": after_load_row_count
        }
        assert actual == expected


