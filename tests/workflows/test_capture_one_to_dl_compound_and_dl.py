from unittest.mock import Mock, MagicMock

import pytest

from speedwagon import tasks
from speedwagon.workflows \
    import workflow_capture_one_to_dl_compound_and_dl as ht_wf

import os.path


def test_output_must_exist(monkeypatch):
    options = {
        "Input": "some_real_source_folder",
        "Output Digital Library": "./invalid_folder/",
        "Output HathiTrust": "./other_invalid_folder/",
    }

    def mock_exists(path):
        if any((
                path == options["Output Digital Library"],
                path == options["Output HathiTrust"]
        )):
            return False
        else:
            return True
    with monkeypatch.context() as mp:
        mp.setattr(os.path, "exists", mock_exists)
        with pytest.raises(ValueError) as e:
            workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()
            workflow.validate_user_options(**options)

    assert 'Directory "./invalid_folder/" does not exist' in str(e.value)


def test_input_must_exist(monkeypatch):

    options = {
        "Input": "./invalid_folder/",
        "Output Digital Library": "./some_real_DL_folder",
        "Output HathiTrust": "./some_real_HT_folder",
    }

    def mock_exists(path):
        if path == options["Input"]:
            return False
        else:
            return True
    with monkeypatch.context() as mp:
        mp.setattr(os.path, "exists", mock_exists)
        with pytest.raises(ValueError) as e:
            workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()
            workflow.validate_user_options(**options)
        assert 'Directory "./invalid_folder/" does not exist' in str(e.value)


def test_input_and_out_invalid_produces_errors_with_both(monkeypatch):
    options = {
        "Input": "some_real_source_folder",
        "Output Digital Library": "./invalid_folder/",
        "Output HathiTrust": "./other_invalid_folder/",
    }

    def mock_exists(path):
        if path == options["Input"]:
            return True
        else:
            return False

    with monkeypatch.context() as mp:
        mp.setattr(os.path, "exists", mock_exists)
        with pytest.raises(ValueError) as e:
            workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()
            workflow.validate_user_options(**options)
        assert \
            'Directory "./invalid_folder/" does not exist' in str(e.value) and \
            'Directory "./other_invalid_folder/" does not exist' in str(e.value)


def test_discover_task_metadata(monkeypatch):
    additional_data = {}
    initial_results = []
    user_args = {
        "Input": "some_real_source_folder",
        "Output Digital Library": "./some_real_dl_folder/",
        "Output HathiTrust": "./some_real_ht_folder/",
    }
    workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()

    def mock_exists(path):
        if path == user_args["Input"]:
            return True
        else:
            return False

    def mock_scandir(path):
        for i_number in range(20):
            file_mock = Mock()
            file_mock.name = f"99423682912205899-{str(i_number).zfill(8)}.tif"
            yield file_mock

    with monkeypatch.context() as mp:
        mp.setattr(os.path, "exists", mock_exists)
        mp.setattr(os, "scandir", mock_scandir)
        new_task_metadata = workflow.discover_task_metadata(
            initial_results=initial_results,
            additional_data=additional_data,
            **user_args
        )

    assert len(new_task_metadata) == 1
    md = new_task_metadata[0]
    assert \
        md['source_path'] == user_args['Input'] and \
        md['output_dl'] == user_args['Output Digital Library'] and \
        md['output_ht'] == user_args['Output HathiTrust']


def test_create_new_task_hathi_and_dl(monkeypatch):
    task_builder = tasks.TaskBuilder(
        tasks.MultiStageTaskBuilder("."),
        "."
    )
    mock_package = MagicMock()
    mock_package.metadata = MagicMock()
    job_args = {
        'package': mock_package,
        "output_dl": "./some_real_dl_folder/",
        "output_ht": "./some_real_ht_folder/",
        "source_path": "./some_real_source_folder/",
    }
    workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()
    workflow.create_new_task(task_builder, **job_args)
    task_built = task_builder.build_task()
    assert len(task_built.subtasks) == 2
    tasks_sorted = sorted(task_built.subtasks, key=lambda t: t.package_format)
    assert tasks_sorted[0].package_format == 'Digital Library Compound' and \
           tasks_sorted[1].package_format == 'HathiTrust jp2'


def test_package_converter(tmpdir):
    output_ht = tmpdir / "ht"
    output_ht.ensure_dir()

    mock_source_package = MagicMock()
    mock_dest_package = MagicMock()
    options = {
        "source_path":  "./some_path/99423682912205899-00000001.tif",
        "packaging_id": "99423682912205899",
        "existing_package": mock_source_package,
        "new_package_root": output_ht.strpath,
        "package_format": 'mock_new_format'
    }

    ht_wf.PackageConverter.package_formats['mock_new_format'] = \
        mock_dest_package

    new_task = ht_wf.PackageConverter(**options)

    new_task.log = MagicMock()
    mock_packager = MagicMock()
    mock_packager.transform = MagicMock()
    new_task.package_factory = MagicMock(return_value=mock_packager)
    new_task.work()
    mock_packager.transform.assert_called_with(
        mock_source_package,
        dest=options['new_package_root']
    )
