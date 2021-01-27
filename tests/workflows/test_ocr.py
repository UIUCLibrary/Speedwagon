import logging
from unittest.mock import MagicMock, Mock

import pytest
import os.path
from speedwagon.workflows import workflow_ocr
from speedwagon.exceptions import MissingConfiguration, SpeedwagonException
from speedwagon.tasks import Result
from uiucprescon.ocr import reader, tesseractwrap

def test_no_config():
    with pytest.raises(MissingConfiguration):
        workflow_ocr.OCRWorkflow()


def test_discover_task_metadata_raises_with_no_tessdata(monkeypatch):
    user_options = {"tessdata": "/some/path"}
    monkeypatch.setattr(os.path, "exists", lambda args: True)
    workflow = workflow_ocr.OCRWorkflow(global_settings=user_options)

    monkeypatch.setattr(os.path, "exists", lambda args: False)
    with pytest.raises(SpeedwagonException):
        user_options = {"tessdata": None}
        workflow.discover_task_metadata([], None, **user_options)


def test_discover_task_metadata(monkeypatch, tmpdir):
    user_options = {"tessdata": "/some/path"}
    monkeypatch.setattr(os.path, "exists", lambda args: True)
    workflow = workflow_ocr.OCRWorkflow(global_settings=user_options)
    tessdata_dir = tmpdir / "tessdata"
    image_dir = tmpdir / "images"
    tessdata_dir.ensure_dir()
    user_options = {
        "tessdata": tessdata_dir.strpath,
        'Image File Type': 'JPEG 2000',
        'Language': 'English',
        'Path':  image_dir.strpath
    }
    initial_results = [
        Result(source=workflow_ocr.FindImagesTask, data=[(image_dir / "dummy.jp2").strpath])
    ]

    new_tasks = workflow.discover_task_metadata(initial_results, None, **user_options)
    assert len(new_tasks) == 1
    new_task = new_tasks[0]
    assert new_task == {
        'source_file_path': (image_dir / "dummy.jp2").strpath,
        'destination_path': image_dir.strpath,
        'output_file_name': 'dummy.txt',
        'lang_code': 'eng',
    }


def test_generate_task_creates_a_file(monkeypatch, tmpdir):
    source_image = tmpdir / "dummy.jp2"
    out_text = tmpdir / "dummy.txt"
    tessdata_dir = tmpdir / "tessdata"
    tessdata_dir.ensure_dir()
    (tessdata_dir / "eng.traineddata").ensure()
    (tessdata_dir / "osd.traineddata").ensure()

    def mock_read(*args, **kwargs):
        return "Spam bacon eggs"
    mock_reader = Mock()

    with monkeypatch.context() as patcher:
        patcher.setattr(reader.Reader, "read", mock_read)
        patcher.setattr(tesseractwrap, "Reader", mock_reader)
        task = workflow_ocr.GenerateOCRFileTask(
            source_image=source_image.strpath,
            out_text_file=out_text.strpath,
            tesseract_path=tessdata_dir.strpath
        )
        task.log = MagicMock()

        task.work()

    assert os.path.exists(out_text.strpath)
    with open(out_text.strpath, "r") as f:
        assert f.read() == "Spam bacon eggs"


class MockGenerateOCRFileTask(workflow_ocr.GenerateOCRFileTask):
    def mock_reader(self, *args, **kwargs):
        mock_class = Mock(read=Mock(return_value="Spam bacon eggs"))
        return mock_class

    engine = Mock(get_reader=mock_reader)


def test_runs(tool_job_manager_spy, tmpdir):
    class MockOCRWorkflow(workflow_ocr.OCRWorkflow):
        def create_new_task(self, task_builder, **job_args):
            image_file = job_args["source_file_path"]
            destination_path = job_args["destination_path"]
            ocr_file_name = job_args["output_file_name"]
            lang_code = job_args["lang_code"]

            ocr_generation_task = MockGenerateOCRFileTask(
                source_image=image_file,
                out_text_file=os.path.join(destination_path, ocr_file_name),
                lang=lang_code,
                tesseract_path=self.tessdata_path
            )
            task_builder.add_subtask(ocr_generation_task)

    my_logger = logging.getLogger(__file__)
    image_path = tmpdir / "images"
    (image_path / "00000001.jp2").ensure()

    tool_job_manager_spy.run(
        None,
        MockOCRWorkflow(global_settings={
            "tessdata": "sample"
        }),
        options={
            "Path": image_path.strpath,
            'Image File Type': 'JPEG 2000',
            'Language': 'English',
        },
        logger=my_logger
    )
    expected_ocr_file = image_path / "00000001.txt"
    with open(expected_ocr_file) as f:
        assert f.read() == "Spam bacon eggs"
