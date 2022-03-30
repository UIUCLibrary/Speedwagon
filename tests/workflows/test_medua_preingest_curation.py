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
