import os
from unittest.mock import Mock, MagicMock

import pytest

import speedwagon
from speedwagon.workflows import workflow_completeness
from hathi_validate import process, validator


@pytest.mark.parametrize("index,label", [
    (0, "Source"),
    (1, "Check for page_data in meta.yml"),
    (2, "Check ALTO OCR xml files"),
    (3, "Check OCR xml files are utf-8"),
])
def test_completeness_workflow_options(index, label):
    workflow = workflow_completeness.CompletenessWorkflow()
    user_options = workflow.user_options()
    assert len(user_options) > 0
    assert user_options[index].label_text == label


def test_initial_task_creates_task():
    workflow = workflow_completeness.CompletenessWorkflow()
    user_args = {
        "Source": "./some_real_source_folder",
        "Check for page_data in meta.yml": False,
        "Check ALTO OCR xml files": False,
        "Check OCR xml files are utf-8": False
    }

    mock_builder = Mock()
    workflow.initial_task(
        task_builder=mock_builder,
        **user_args
    )
    source = user_args['Source']
    assert \
        mock_builder.add_subtask.called is True and \
        mock_builder.add_subtask.call_args[1]['subtask'].batch_root == source


@pytest.fixture
def unconfigured_workflow():
    workflow = workflow = workflow_completeness.CompletenessWorkflow()
    user_options = {i.label_text: i.data for i in workflow.user_options()}

    return workflow, user_options


def test_discover_task_metadata_one_per_package(
        monkeypatch, unconfigured_workflow):

    workflow, user_options = unconfigured_workflow
    initial_results = []
    additional_data = {}
    number_of_fake_packages = 10

    def mock_scandir(path):
        for i_number in range(number_of_fake_packages):
            package_mock = Mock()
            package_mock.name = f"99423682{str(i_number).zfill(2)}2205899"
            package_mock.is_dir = Mock(return_value=True)
            yield package_mock

    monkeypatch.setattr(os, "scandir", mock_scandir)
    monkeypatch.setattr(os, "access", lambda *args: True)
    new_task_md = workflow.discover_task_metadata(
        initial_results=initial_results,
        additional_data=additional_data,
        **user_options
    )
    assert len(new_task_md) == number_of_fake_packages


def test_create_new_task_generates_subtask(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    mock_builder = Mock()
    job_args = {
        'package_path': "/some/source/package",
        'destination': "/some/destination",
        'check_ocr_data': False,
        '_check_ocr_utf8': False,
    }
    workflow.create_new_task(
        mock_builder,
        **job_args
    )
    assert mock_builder.add_subtask.called is True


def test_generate_report_creates_a_report(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    job_args = {}
    results = [
        speedwagon.tasks.Result(
            workflow_completeness.HathiCheckMissingPackageFilesTask,
            data=[]
        ),
        speedwagon.tasks.Result(
            workflow_completeness.HathiManifestGenerationTask,
            data="Manifest"
        ),
        speedwagon.tasks.Result(
            workflow_completeness.HathiCheckMissingComponentsTask,
            data=[]
        ),
        speedwagon.tasks.Result(
            workflow_completeness.ValidateChecksumsTask,
            data=[]
        ),
        speedwagon.tasks.Result(
            workflow_completeness.ValidateMarcTask,
            data=[]
        ),
        speedwagon.tasks.Result(
            workflow_completeness.ValidateYMLTask,
            data=[]
        ),
        speedwagon.tasks.Result(
            workflow_completeness.ValidateExtraSubdirectoriesTask,
            data=[]
        ),
        speedwagon.tasks.Result(
            workflow_completeness.PackageNamingConventionTask,
            data=[]
        ),
    ]
    message = workflow.generate_report(results, **job_args)
    assert "Report" in message


checksum_results = [
    ([], None),
    (MagicMock(), None),
    ([], FileNotFoundError),
    ([], PermissionError),
]


@pytest.mark.parametrize("errors_found,throw_exception", checksum_results)
def test_hathi_missing_checksum_task_calls_validator(
        monkeypatch, errors_found, throw_exception):

    package_path = "./sample_path/package1"
    check_ocr = False
    task = workflow_completeness.HathiCheckMissingComponentsTask(
        check_ocr=check_ocr,
        package_path=package_path
    )

    task.log = Mock()
    mock_run_validation = MagicMock(return_value=errors_found)
    if throw_exception is not None:
        def exception_runner(*args, **kwargs):
            raise throw_exception
        mock_run_validation.side_effect = exception_runner
    from hathi_validate import process, validator
    with monkeypatch.context() as mp:
        mp.setattr(process, "run_validation", mock_run_validation)
        assert task.work() is (throw_exception is None)

    assert mock_run_validation.called is True and \
           mock_run_validation.call_args[0][0].path == package_path and \
           isinstance(mock_run_validation.call_args[0][0],
                      validator.ValidateComponents)
    assert all([a == b for a, b in zip(errors_found, task.results)])


validation_tasks = [
    (workflow_completeness.HathiCheckMissingPackageFilesTask,
     validator.ValidateMissingFiles),
    (workflow_completeness.ValidateExtraSubdirectoriesTask,
     validator.ValidateExtraSubdirectories),
    (workflow_completeness.ValidateOCRFilesTask,
     validator.ValidateOCRFiles),
]


@pytest.mark.parametrize("validator_task, validator_process",
                         validation_tasks)
def test_validator_task_calls_validator(monkeypatch, validator_task,
                                        validator_process):

    package_path = "./sample_path/package1"

    task = validator_task(package_path=package_path)
    task.log = Mock()
    mock_run_validation = MagicMock(return_value=[])

    with monkeypatch.context() as mp:
        mp.setattr(process, "run_validation", mock_run_validation)
        assert task.work() is True

    assert mock_run_validation.called is True and \
           mock_run_validation.call_args[0][0].path == package_path and \
           isinstance(mock_run_validation.call_args[0][0], validator_process)


def test_hathi_checksum_task_calls_validator(monkeypatch):
    package_path = "./sample_path/package1"
    from hathi_validate import process, validator

    task = workflow_completeness.ValidateChecksumsTask(
        package_path=package_path)

    task.log = Mock()
    mock_run_validation = MagicMock(return_value=[])
    mock_extracts_checksums = MagicMock(return_value=[])

    with monkeypatch.context() as mp:
        mp.setattr(process, "run_validation", mock_run_validation)
        mp.setattr(process, "extracts_checksums", mock_extracts_checksums)
        assert task.work() is True

    assert mock_run_validation.called is True and \
           mock_run_validation.call_args[0][0].path == package_path and \
           isinstance(
               mock_run_validation.call_args[0][0],
               validator.ValidateChecksumReport
           )


def test_validate_marc_task_calls_validator(monkeypatch):
    package_path = os.path.join("sample_path", "package1")
    marc_file = os.path.join(package_path, "marc.xml")
    from hathi_validate import process, validator

    task = workflow_completeness.ValidateMarcTask(package_path=package_path)
    task.log = Mock()
    mock_run_validation = MagicMock(return_value=[])

    with monkeypatch.context() as mp:
        mp.setattr(process, "run_validation", mock_run_validation)
        mp.setattr(os.path, "exists", lambda x: x == marc_file)
        assert task.work() is True

    assert mock_run_validation.called is True and \
           mock_run_validation.call_args[0][0].marc_file == marc_file and \
           isinstance(
               mock_run_validation.call_args[0][0],
               validator.ValidateMarc
           )


class TestValidateYMLTask:
    def test_validate_yml_task_calls_validator(self, monkeypatch):
        package_path = os.path.join("sample_path", "package1")
        yaml_file = os.path.join(package_path, "meta.yml")
        from hathi_validate import process, validator

        task = workflow_completeness.ValidateYMLTask(package_path=package_path)
        task.log = Mock()
        mock_run_validation = MagicMock(return_value=[])

        with monkeypatch.context() as mp:
            mp.setattr(process, "run_validation", mock_run_validation)
            mp.setattr(os.path, "exists", lambda x: x == yaml_file)
            assert task.work() is True

        assert mock_run_validation.called is True and \
               mock_run_validation.call_args[0][0].path == package_path and \
               mock_run_validation.call_args[0][0].yaml_file == yaml_file and \
               isinstance(
                   mock_run_validation.call_args[0][0],
                   validator.ValidateMetaYML
               )

    def test_yaml_file_not_found_error(self, monkeypatch):
        package_path = os.path.join("sample_path", "package1")
        yaml_file = os.path.join(package_path, "meta.yml")
        task = workflow_completeness.ValidateYMLTask(package_path=package_path)
        task.log = Mock()
        mock_run_validation = MagicMock(side_effect=FileNotFoundError("Nope"))
        with monkeypatch.context() as mp:
            mp.setattr(process, "run_validation", mock_run_validation)
            mp.setattr(os.path, "exists", lambda x: x == yaml_file)
            task.work()

        assert any(
            "Unable to validate YAML" in res.message for res in task.results
        ) is True


def test_validate_ocr_utf8_task_calls_validator(monkeypatch):
    package_path = os.path.join("sample_path", "package1")
    from hathi_validate import process, validator

    task = \
        workflow_completeness.ValidateOCFilesUTF8Task(
            package_path=package_path)

    task.log = Mock()
    mock_run_validation = MagicMock(return_value=[])

    def mock_scandir(path):
        for i_number in range(20):
            file_mock = Mock()
            file_mock.name = f"99423682912205899-{str(i_number).zfill(8)}.xml"
            yield file_mock

    with monkeypatch.context() as mp:
        mp.setattr(process, "run_validation", mock_run_validation)
        mp.setattr(os, "scandir", mock_scandir)
        assert task.work() is True

    assert mock_run_validation.called is True and \
           mock_run_validation.call_args[0][0].file_path.endswith(".xml") and \
           isinstance(
               mock_run_validation.call_args[0][0],
               validator.ValidateUTF8Files
           )


def test_manifest_generations_task(monkeypatch):
    package_path = os.path.join("sample_path", "package1")

    task = \
        workflow_completeness.HathiManifestGenerationTask(
            batch_root=package_path)
    task.log = Mock()
    number_of_fake_packages = 2

    def mock_scandir(path):
        for i_number in range(number_of_fake_packages):
            package_mock = Mock()
            package_mock.name = f"99423682{str(i_number).zfill(2)}2205899"
            package_mock.is_dir = Mock(return_value=True)
            yield package_mock

    def mock_walk(root):
        return [
            ("12345", [], ("12345_1.tif", "12345_2.tif"))
        ]

    with monkeypatch.context() as mp:
        mp.setattr(os, "scandir", mock_scandir)
        mp.setattr(os, "walk", mock_walk)
        # mp.setattr(os.path, "exists", lambda x: x == package_path)
        assert task.work() is True
    assert ".tif: 2 file(s)" in task.results


def test_package_naming_convention_task(monkeypatch):
    package_path = os.path.join("sample_path", "package1")

    task = \
        workflow_completeness.PackageNamingConventionTask(
            package_path=package_path)
    task.log = Mock()
    with monkeypatch.context() as mp:
        mp.setattr(os.path, "isdir", lambda x: x == package_path)
        assert task.work() is True
    assert len(task.results) == 1


def test_extra_subdirectory_permission_issues(monkeypatch, caplog):
    task = workflow_completeness.ValidateExtraSubdirectoriesTask("some_path")
    monkeypatch.setattr(
        workflow_completeness.validate_process,
        "run_validation",
        Mock(side_effect=PermissionError))
    task.work()
    assert any(
        "Permission issues" in result.message for result in task.results
    )


@pytest.mark.parametrize(
    "task",
    [
        workflow_completeness.ValidateExtraSubdirectoriesTask(
            package_path="some_path"),
        workflow_completeness.PackageNamingConventionTask(
            package_path="some_path"
        ),
        workflow_completeness.ValidateOCFilesUTF8Task(
            package_path="some_path"
        ),
        workflow_completeness.ValidateYMLTask(
            package_path="some_path"
        ),
        workflow_completeness.ValidateOCRFilesTask(
            package_path="some_path"
        ),
        workflow_completeness.ValidateMarcTask(
            package_path="some_path"
        ),
        workflow_completeness.HathiCheckMissingPackageFilesTask(
            package_path="some_path"
        ),
        workflow_completeness.HathiCheckMissingComponentsTask(
            package_path="some_path",
            check_ocr=False
        ),
        workflow_completeness.ValidateChecksumsTask(
            package_path="some_path"
        ),
        workflow_completeness.HathiManifestGenerationTask(
            batch_root="some_path"
        )
    ]
)
def test_tasks_have_description(task):
    assert task.task_description() is not None


class TestCompletenessReportGenerator:
    def test_empty_report(self):
        report_builder = workflow_completeness.CompletenessReportBuilder()
        report = report_builder.build_report()
        assert "No validation errors detected" in report

    def test_with_error(self):
        import hathi_validate
        report_builder = workflow_completeness.CompletenessReportBuilder()
        hathi_validate_result = \
            hathi_validate.result.Result(result_type="Spam!")
        hathi_validate_result.message = "spam"
        task = workflow_completeness.HathiCheckMissingPackageFilesTask
        report_builder.results[task] = [
            speedwagon.tasks.tasks.Result(
                source=hathi_validate.result.Result("Dddd"),
                data=hathi_validate_result
            )
        ]
        report = report_builder.build_report()
        assert "spam" in report


class TestValidateOCRFilesTask:
    def test_permission_error_mentioned_in_report(self, monkeypatch):
        run_validation = MagicMock()
        run_validation.side_effect = PermissionError()
        monkeypatch.setattr(
            workflow_completeness.validate_process,
            "run_validation",
            run_validation
        )
        task = workflow_completeness.ValidateOCRFilesTask("somepath")
        task.work()
        assert any("Permission issues" in a.message for a in task.results)