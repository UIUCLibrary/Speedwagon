from unittest.mock import Mock, MagicMock

import pytest
from PySide6 import QtWidgets,  QtCore

from speedwagon.workflows import workflow_medusa_preingest_curation
from speedwagon.models import ToolOptionsModel4


class TestMedusaPreingestCuration:
    @pytest.fixture
    def default_args(self, workflow):
        return ToolOptionsModel4(
            workflow.get_user_options()
        ).get()

    @pytest.fixture
    def workflow(self):
        return workflow_medusa_preingest_curation.MedusaPreingestCuration()

    def test_default_user_args_are_invalidate(self, workflow, default_args):
        with pytest.raises(ValueError):
            workflow.validate_user_options(**default_args)

    def test_valid_user_args_returns_true(self, workflow, default_args):
        workflow_medusa_preingest_curation\
            .MedusaPreingestCuration.validation_checks = []

        assert workflow.validate_user_options(**default_args) is True

    def test_sort_item_data_unknown_throw(self, workflow, monkeypatch):
        data = [
            "somebaddata",
        ]
        with pytest.raises(ValueError):
            workflow.sort_item_data(data)

    def test_sort_item_data(self, workflow, monkeypatch):
        data = [
            "./some/file.txt",
            "./some/directory/",

        ]
        monkeypatch.setattr(
            workflow_medusa_preingest_curation.os.path,
            "isdir",
            lambda path: path == "./some/directory/"
        )
        monkeypatch.setattr(
            workflow_medusa_preingest_curation.os.path,
            "isfile",
            lambda path: path == "./some/file.txt"
        )
        results = workflow.sort_item_data(data)
        assert results == {
            "files": ["./some/file.txt"],
            "directories": ["./some/directory/"],
        }

    def test_get_additional_info_opens_dialog(
            self,
            workflow,
            default_args,
            qtbot
    ):

        dialog_box = Mock()
        dialog_box.data = Mock(return_value=[])

        workflow.dialog_box_type = Mock(return_value=dialog_box)
        workflow.get_additional_info(
            parent=None,
            options=default_args,
            pretask_results=[MagicMock()]
        )
        assert dialog_box.exec.called is True


@pytest.fixture()
def default_user_args():
    workflow = workflow_medusa_preingest_curation.MedusaPreingestCuration()
    return ToolOptionsModel4(
        workflow.get_user_options()
    ).get()


def test_validate_missing_values():
    with pytest.raises(ValueError):
        workflow_medusa_preingest_curation.validate_missing_values({})


def test_validate_no_missing_values(default_user_args):
    values = default_user_args.copy()
    values["Path"] = "something"
    workflow_medusa_preingest_curation.validate_missing_values(values)


def test_validate_path_valid(monkeypatch):
    supposed_to_be_real_path = "./some/valid/path"

    monkeypatch.setattr(
        workflow_medusa_preingest_curation.os.path,
        "exists",
        lambda path: path == supposed_to_be_real_path
    )

    workflow_medusa_preingest_curation.validate_path_valid(
        {
            'Path':  supposed_to_be_real_path
        }
    )


def test_validate_path_invalid(monkeypatch):
    invalid_path = "./some/valid/path"

    monkeypatch.setattr(
        workflow_medusa_preingest_curation.os.path,
        "exists",
        lambda path: False
    )

    with pytest.raises(ValueError):
        workflow_medusa_preingest_curation.validate_path_valid(
            {
                'Path':  invalid_path
            }
        )


class TestConfirmDeleteDialog:
    def test_okay_button_accepts(self, qtbot):
        items = []
        dialog_box = \
            workflow_medusa_preingest_curation.ConfirmDeleteDialog(items)

        okay_button = \
            dialog_box.button_box.button(QtWidgets.QDialogButtonBox.Ok)

        with qtbot.wait_signal(dialog_box.accepted):
            okay_button.click()

    def test_cancel_button_rejects(self, qtbot):
        items = []
        dialog_box = \
            workflow_medusa_preingest_curation.ConfirmDeleteDialog(items)

        cancel_button = \
            dialog_box.button_box.button(QtWidgets.QDialogButtonBox.Cancel)

        with qtbot.wait_signal(dialog_box.rejected):
            cancel_button.click()


class TestConfirmListModel:
    def test_model_check(self, qtmodeltester):
        items = [
            "./file1.txt",
            "/directory/"
        ]
        model = workflow_medusa_preingest_curation.ConfirmListModel(items)
        qtmodeltester.check(model)

    def test_all_data_defaults_to_checked(self):
        items = [
            "./file1.txt",
            "/directory/"
        ]
        model = workflow_medusa_preingest_curation.ConfirmListModel(items)
        assert model.selected() == items

    def test_unchecking_item(self):
        items = [
            "./file1.txt",
            "/directory/"
        ]
        model = workflow_medusa_preingest_curation.ConfirmListModel(items)

        model.setData(
            index=model.index(0),
            value=QtCore.Qt.Unchecked,
            role=QtCore.Qt.CheckStateRole
        )

        assert model.selected() == ["/directory/"]


class TestFindOffendingFiles:
    def test_description(self):
        search_path = "./some/path"
        task = workflow_medusa_preingest_curation.FindOffendingFiles(
            **{
                "Path": search_path,
                "Include Subdirectories": True,
                "Locate and delete dot underscore files": True,
                "Locate and delete .DS_Store files": True,
                "Locate and delete Capture One files": True,
            }
        )
        assert search_path in task.task_description()
