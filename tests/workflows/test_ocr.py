import pytest

from speedwagon.workflows import workflow_ocr
from speedwagon.exceptions import MissingConfiguration


def test_no_config():
    with pytest.raises(MissingConfiguration):
        workflow_ocr.OCRWorkflow()