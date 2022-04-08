import logging
from unittest.mock import MagicMock, Mock, ANY, mock_open, patch

import pytest
import os.path

import speedwagon
from speedwagon.workflows import workflow_ocr
from speedwagon.exceptions import MissingConfiguration, SpeedwagonException
from uiucprescon.ocr import reader, tesseractwrap
from speedwagon.frontend.qtwidgets import models


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
        speedwagon.tasks.Result(
            source=workflow_ocr.FindImagesTask,
            data=[(image_dir / "dummy.jp2").strpath]
        )
    ]

    new_tasks = workflow.discover_task_metadata(
        initial_results, None, **user_options
    )

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
        return Mock(read=Mock(return_value="Spam bacon eggs"))

    engine = Mock(get_reader=mock_reader)


def test_runs(qtbot, tool_job_manager_spy, tmpdir, monkeypatch):
    monkeypatch.setattr(speedwagon.runner_strategies, "QtDialogProgress", MagicMock())
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
    tessdata_dir = tmpdir / "sample"

    (image_path / "00000001.jp2").ensure()
    tool_job_manager_spy.run(
        MockOCRWorkflow(global_settings={
            "tessdata": tessdata_dir.strpath
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


class TestOCRWorkflow:
    @pytest.fixture
    def workflow(self, monkeypatch):
        global_settings = {
            "tessdata": os.path.join("some", "path")
        }
        monkeypatch.setattr(
            workflow_ocr.os.path,
            "exists",
            lambda path: path == global_settings["tessdata"]
        )
        return \
            workflow_ocr.OCRWorkflow(global_settings)

    @pytest.fixture
    def default_options(self, workflow):
        return models.ToolOptionsModel4(
            workflow.get_user_options()
        ).get()

    def test_validate_user_options_valid(
            self,
            monkeypatch,
            workflow,
            default_options
    ):
        import os
        user_options = default_options.copy()
        user_options["Path"] = os.path.join("some", "path")
        monkeypatch.setattr(
            workflow_ocr.os.path,
            "isdir",
            lambda path: path == user_options["Path"]
        )
        assert workflow.validate_user_options(**user_options) is True

    def test_validate_user_options_invalid_empty_path(
            self,
            monkeypatch,
            workflow,
            default_options
    ):
        user_options = default_options.copy()
        user_options["Path"] = None
        user_options["Language"] = "eng"
        with pytest.raises(ValueError):
            workflow.validate_user_options(**user_options)

    @pytest.mark.parametrize("check_function", ["isdir", "exists"])
    def test_validate_user_options_invalid(
            self,
            monkeypatch,
            workflow,
            default_options,
            check_function
    ):
        import os
        user_options = default_options.copy()
        user_options["Path"] = os.path.join("some", "path")
        user_options["Language"] = "eng"

        monkeypatch.setattr(
            workflow_ocr.os.path,
            check_function,
            lambda path: False
        )

        with pytest.raises(ValueError):
            workflow.validate_user_options(**user_options)

    def test_discover_task_metadata(self, workflow, default_options):
        user_options = default_options.copy()
        user_options["Language"] = "English"
        user_options["Path"] = os.path.join("some", "path")

        initial_results = [
            speedwagon.tasks.Result(workflow_ocr.FindImagesTask, [
                "spam.jp2"
            ])
        ]
        additional_data = {}
        tasks_generated = workflow.discover_task_metadata(
            initial_results=initial_results,
            additional_data=additional_data,
            **user_options
        )
        assert len(tasks_generated) == 1
        task = tasks_generated[0]
        assert task['lang_code'] == "eng" and \
               task['source_file_path'] == "spam.jp2" and \
               task["output_file_name"] == "spam.txt"

    def test_create_new_task(self, workflow, monkeypatch):
        import os
        job_args = {
            "source_file_path": os.path.join("some", "path", "bacon.jp2"),
            "output_file_name": "bacon.txt",
            "lang_code": "eng",
            'destination_path':
                os.path.join(
                    "some",
                    "path",
                )
        }
        task_builder = Mock()
        GenerateOCRFileTask = Mock()
        GenerateOCRFileTask.name = "GenerateOCRFileTask"
        monkeypatch.setattr(workflow_ocr, "GenerateOCRFileTask",
                            GenerateOCRFileTask)
        #
        workflow.create_new_task(task_builder, **job_args)
        assert task_builder.add_subtask.called is True
        GenerateOCRFileTask.assert_called_with(
            source_image=job_args['source_file_path'],
            out_text_file=os.path.join("some", "path", "bacon.txt"),
            lang="eng",
            tesseract_path=ANY
        )

    def test_generate_report(self, workflow, default_options):
        user_args = default_options.copy()
        results = [
            speedwagon.tasks.Result(workflow_ocr.GenerateOCRFileTask, {}),
            speedwagon.tasks.Result(workflow_ocr.GenerateOCRFileTask, {}),
        ]
        report = workflow.generate_report(results=results, **user_args)
        assert "Completed generating OCR 2 files" in report

    @pytest.mark.parametrize("image_file_type,expected_file_extension", [
        ('JPEG 2000', '.jp2'),
        ('TIFF', '.tif'),
    ])
    def test_initial_task(self, monkeypatch, workflow, default_options,
                          image_file_type, expected_file_extension):

        user_args = default_options.copy()
        user_args['Image File Type'] = image_file_type
        task_builder = Mock()
        FindImagesTask = Mock()

        monkeypatch.setattr(
            workflow_ocr,
            "FindImagesTask",
            FindImagesTask
        )

        workflow.initial_task(task_builder, **user_args)
        assert task_builder.add_subtask.called is True

        FindImagesTask.assert_called_with(
            ANY,
            file_extension=expected_file_extension
        )

    def test_get_available_languages(self, workflow, monkeypatch):
        path = "tessdir"

        def scandir(path):
            results = []
            m = Mock()
            m.name = "eng.traineddata"
            m.path = os.path.join(path, m.name)
            results.append(m)
            return results

        monkeypatch.setattr(workflow_ocr.os, "scandir", scandir)
        languages = list(workflow.get_available_languages(path))
        assert len(languages) == 1

    def test_get_available_languages_ignores_osd(self, workflow, monkeypatch):
        path = "tessdir"

        def scandir(path):
            results = []
            osd = Mock()
            osd.name = "osd.traineddata"
            osd.path = os.path.join(path, osd.name)
            results.append(osd)

            eng = Mock()
            eng.name = "eng.traineddata"
            eng.path = os.path.join(path, eng.name)
            results.append(eng)
            return results

        monkeypatch.setattr(workflow_ocr.os, "scandir", scandir)
        languages = list(workflow.get_available_languages(path))
        assert len(languages) == 1


class TestFindImagesTask:
    def test_work(self, monkeypatch):
        root = os.path.join("some", "directory")
        file_extension = ".jp2"
        task = workflow_ocr.FindImagesTask(
            root=root,
            file_extension=file_extension
        )

        def walk(path):
            return [
                ("12345", ('access'), ('sample.jp2', "sample.txt"))
            ]

        monkeypatch.setattr(workflow_ocr.os, "walk", walk)
        assert task.work() is True
        assert os.path.join("12345", "sample.jp2") in task.results and \
               os.path.join("12345", "sample.txt") not in task.results


class TestGenerateOCRFileTask:
    def test_work(self, monkeypatch):
        source_image = os.path.join("12345", "sample.jp2")
        out_text_file = os.path.join("12345", "sample.txt")
        lang = "eng"
        tesseract_path = "tesspath"
        workflow_ocr.GenerateOCRFileTask.set_tess_path = Mock()
        workflow_ocr.GenerateOCRFileTask.engine = Mock()
        task = workflow_ocr.GenerateOCRFileTask(
            source_image=source_image,
            out_text_file=out_text_file,
            lang=lang,
            tesseract_path=tesseract_path
        )
        m = mock_open()
        with patch('speedwagon.workflows.workflow_ocr.open', m):
            assert task.work() is True
        assert m.called is True

    def test_read_image(self, monkeypatch):
        source_image = os.path.join("12345", "sample.jp2")
        out_text_file = os.path.join("12345", "sample.txt")
        lang = "eng"
        tesseract_path = "tesspath"
        workflow_ocr.GenerateOCRFileTask.set_tess_path = Mock()
        workflow_ocr.GenerateOCRFileTask.engine = Mock()

        reader = Mock()
        workflow_ocr.GenerateOCRFileTask.engine.get_reader = \
            lambda args: reader

        task = workflow_ocr.GenerateOCRFileTask(
            source_image=source_image,
            out_text_file=out_text_file,
            lang=lang,
            tesseract_path=tesseract_path
        )
        task.read_image(source_image, "eng")
        assert reader.read.called is True


@pytest.mark.parametrize(
    "task",
    [
        workflow_ocr.GenerateOCRFileTask(
            source_image="source_image",
            out_text_file="out_text_file",
            lang="lang",
            tesseract_path="tesseract_path"
        ),
        workflow_ocr.FindImagesTask(
            root="root",
            file_extension=".tif"
        )
    ]
)
def test_tasks_have_description(task):
    assert task.task_description() is not None
