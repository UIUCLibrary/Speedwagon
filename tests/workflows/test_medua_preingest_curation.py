import pytest

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

