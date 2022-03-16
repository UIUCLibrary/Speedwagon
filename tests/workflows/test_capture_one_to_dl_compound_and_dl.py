from unittest.mock import Mock, MagicMock, call

import pytest
from uiucprescon import packager
import speedwagon
import speedwagon.exceptions
from speedwagon import models
from speedwagon.workflows \
    import workflow_capture_one_to_dl_compound_and_dl as ht_wf

import os.path


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


def test_discover_task_metadata(monkeypatch, user_options):
    additional_data = {}
    initial_results = []

    user_options['Package Type'] = "Capture One"
    user_options["Input"] = "some_real_source_folder"
    user_options["Output Digital Library"] = "./some_real_dl_folder/"
    user_options["Output HathiTrust"] = "./some_real_ht_folder/"
    # }
    workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()

    def mock_exists(path):
        if path == user_options["Input"]:
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
            **user_options
        )

    assert len(new_task_metadata) == 1
    md = new_task_metadata[0]
    assert \
        md['source_path'] == user_options['Input'] and \
        md['output_dl'] == user_options['Output Digital Library'] and \
        md['output_ht'] == user_options['Output HathiTrust']


def test_create_new_task_hathi_and_dl(monkeypatch):
    task_builder = speedwagon.tasks.TaskBuilder(
        speedwagon.tasks.MultiStageTaskBuilder("."),
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


class TestWorkflow:

    @pytest.mark.parametrize("dl_outpath, ht_outpath", [
        ("some/real/output/dl", "some/real/output/ht"),
        (None, "some/real/output/ht"),
        ("some/real/output/dl", None),
    ])
    def test_output(self, user_options, monkeypatch, dl_outpath, ht_outpath):
        user_options['Package Type'] = "Capture One"
        user_options['Input'] = "some/real/path"
        user_options['Output Digital Library'] = dl_outpath
        user_options['Output HathiTrust'] = ht_outpath
        import os

        def mock_scandir(path):
            for i_number in range(20):
                file_mock = Mock()
                file_mock.name = \
                    f"99423682912205899-{str(i_number).zfill(8)}.tif"

                file_mock.path = path

                yield file_mock

        initial_results = []
        additional_data = {}
        with monkeypatch.context() as mp:
            mp.setattr(os.path, "exists", lambda path: path in [
                user_options['Input'],
                user_options['Output Digital Library'],
                user_options['Output HathiTrust']
            ])

            workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()
            mp.setattr(os, "scandir", mock_scandir)
            new_task_metadata = workflow.discover_task_metadata(
                initial_results=initial_results,
                additional_data=additional_data,
                **user_options
            )
            package_factory = Mock()
            for task_metadata in new_task_metadata:
                task_builder = speedwagon.tasks.TaskBuilder(
                    speedwagon.tasks.MultiStageTaskBuilder("."),
                    "."
                )
                workflow.create_new_task(task_builder, **task_metadata)
                for t in task_builder.build_task().subtasks:
                    t.package_factory = Mock(return_value=package_factory)
                    t.exec()

            assert package_factory.transform.called is True
            calls = []
            if dl_outpath is not None:
                calls.append(
                    call(task_metadata['package'],
                         dest=user_options['Output Digital Library'])
                )

            if ht_outpath is not None:
                calls.append(
                    call(task_metadata['package'],
                         dest=user_options['Output HathiTrust']
                         )
                )

            assert package_factory.transform.call_count == len(
                list(filter(lambda x: x is not None, [dl_outpath, ht_outpath]))
            )

            package_factory.transform.assert_has_calls(calls, any_order=True)


@pytest.fixture()
def user_options():
    workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()
    return models.ToolOptionsModel4(workflow.get_user_options()).get()
    # return models.ToolOptionsModel3(workflow.user_options()).get()


class TestValidateUserArgs:
    @pytest.mark.parametrize("key", ht_wf.UserArgs.__annotations__.keys())
    def test_user_options_matches_user_typedict(self, user_options, key):
        assert key in user_options

    @pytest.mark.parametrize("dl_outpath, ht_outpath, is_valid", [
        ("some/real/output/dl", "some/real/output/ht", True),
        (None, "some/real/output/ht", True),
        ("some/real/output/dl", None, True),
        (None, None, False),
    ])
    def test_one_output_must_exist(
            self, user_options, monkeypatch, dl_outpath, ht_outpath, is_valid
    ):
        user_options['Input'] = "some/real/path"
        user_options['Output Digital Library'] = dl_outpath
        user_options['Output HathiTrust'] = ht_outpath

        existing_paths = [
            user_options['Input'],
            user_options['Output Digital Library'],
            user_options['Output HathiTrust']
        ]

        monkeypatch.setattr(
            os.path,
            "exists",
            lambda path: path in existing_paths and path is not None
        )

        workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()
        if is_valid is True:
            assert workflow.validate_user_options(**user_options) is True
        else:
            with pytest.raises(ValueError):
                workflow.validate_user_options(**user_options)

    def test_valid(self, user_options, monkeypatch):
        user_options['Input'] = "some/real/path"
        user_options['Output Digital Library'] = "some/real/output/dl"
        user_options['Output HathiTrust'] = "some/real/output/ht"
        import os
        workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()
        with monkeypatch.context() as mp:
            mp.setattr(os.path, "exists", lambda x: True)
            assert workflow.validate_user_options(**user_options) is True

    def test_invalid_no_outputs(self, user_options):
        user_options['Input'] = "some/real/path"
        user_options['Output Digital Library'] = None
        user_options['Output HathiTrust'] = None
        workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()
        with pytest.raises(ValueError):
            workflow.validate_user_options(**user_options)


@pytest.mark.parametrize("dl_outpath, ht_outpath, is_valid", [
        ("some/real/output/dl", "some/real/output/ht", True),
        (None, "some/real/output/ht", True),
        ("some/real/output/dl", None, True),
        (None, None, False),
    ])
def test_output_validator(monkeypatch, dl_outpath, ht_outpath, is_valid):
    user_options = {}
    user_options['Input'] = "some/real/path"
    user_options['Output Digital Library'] = dl_outpath
    user_options['Output HathiTrust'] = ht_outpath
    checks = [
        'Output Digital Library',
        'Output HathiTrust'
    ]
    existing_paths = [
        user_options['Output Digital Library'],
        user_options['Output HathiTrust']
    ]
    monkeypatch.setattr(
        os.path,
        "exists",
        lambda path: path in existing_paths and path is not None
    )
    validator = ht_wf.MinimumOutputsValidator(checks)
    assert \
        validator.is_valid(
            **user_options
        ) is is_valid, validator.explanation(**user_options)


def test_output_validator_success_is_ok(user_options, monkeypatch):
    user_options['Input'] = "some/real/path"
    user_options['Output Digital Library'] = "some/real/output_path_for_dl"
    user_options['Output HathiTrust'] = "some/real/output_path_for_ht"

    validator = ht_wf.MinimumOutputsValidator(
        ['Output Digital Library', "Output HathiTrust"]
    )
    with monkeypatch.context() as mp:
        mp.setattr(
            ht_wf.MinimumOutputsValidator,
            "is_valid",
            lambda *args, **user_args: True
        )
        assert validator.explanation(**user_options) == "ok"


@pytest.mark.parametrize(
    "user_selected_package_type, expected_package_type", [
        ("Capture One", packager.packages.CaptureOnePackage),
        ("Archival collections/Non EAS", packager.packages.ArchivalNonEAS),
        ("Cataloged collections/Non EAS", packager.packages.CatalogedNonEAS),
    ]
)
def test_discover_task_metadata_gets_right_package(
        user_options,
        user_selected_package_type,
        expected_package_type,
        monkeypatch
):
    additional_data = {}
    initial_results = []
    user_args = {
        "Input": "some_real_source_folder",
        "Package Type": user_selected_package_type,
        "Output Digital Library": "./some_real_dl_folder/",
        "Output HathiTrust": "./some_real_ht_folder/",
    }
    workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()

    def mock_scandir(path):
        for i_number in range(20):
            file_mock = Mock()
            file_mock.name = f"99423682912205899-{str(i_number).zfill(8)}.tif"
            file_mock.path = os.path.join(path, file_mock.name)
            yield file_mock

    real_paths = [
        user_args["Input"],
        user_args["Output Digital Library"],
        user_args["Output HathiTrust"],
    ]

    def PackageFactory(package_type):
        assert isinstance(package_type, expected_package_type)
        return package_type

    with monkeypatch.context() as mp:
        mp.setattr(
            os.path,
            "exists",
            lambda path: path in real_paths and path is not None
        )
        mp.setattr(os, "scandir", mock_scandir)
        from uiucprescon import packager

        mp.setattr(packager, "PackageFactory", PackageFactory)
        workflow.discover_task_metadata(
            initial_results=initial_results,
            additional_data=additional_data,
            **user_args
        )
    # assert PackageFactory.called is True
    #
    # calls = [
    #     call(packager.packages.CaptureOnePackage(delimiter="-"))
    # ]
    # PackageFactory.assert_has_calls(calls)


def test_discover_task_metadata_invalid_package(user_options):
    workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()
    initial_results = []
    additional_data = {}
    user_options['Package Type'] = "not a real package type"
    with pytest.raises(ValueError):
        workflow.discover_task_metadata(
            initial_results=initial_results,
            additional_data=additional_data,
            **user_options
        )


def test_failed_to_locate_files_throws_speedwagon_exception(
        user_options, monkeypatch
):

    workflow = ht_wf.CaptureOneToDlCompoundAndDLWorkflow()
    from uiucprescon.packager import PackageFactory
    monkeypatch.setattr(
        PackageFactory,
        "locate_packages",
        Mock(side_effect=FileNotFoundError)
    )
    user_options['Package Type'] = "Capture One"
    with pytest.raises(speedwagon.exceptions.SpeedwagonException):
        workflow.discover_task_metadata(
            initial_results=[],
            additional_data={},
            **user_options
        )


def test_package_converter_invalid_format():
    with pytest.raises(ValueError) as e:
        ht_wf.PackageConverter(
            source_path="some_path",
            packaging_id="fake",
            existing_package=None,
            new_package_root="new_path",
            package_format="invalid package format"
        )
    assert "is not a known value" in str(e.value)


class TestOutputsValidValuesValidator:
    def test_valid(self):
        validator = ht_wf.OutputsValidValuesValidator(
            keys_to_check=[
                'Output Digital Library',
                'Output HathiTrust'
            ]
        )
        user_options = {
            "Input": "some_path",
            "Package Type": "Capture One",
            "Output Digital Library":
                os.path.join("valid", "path", "that", "exists", "1"),
            "Output HathiTrust":
                os.path.join("valid", "path", "that", "exists", "2"),
        }
        validator.directory_validator = lambda entry: True
        assert validator.is_valid(**user_options) is True

    def test_valid_explaination_ok(self):
        validator = ht_wf.OutputsValidValuesValidator(
            keys_to_check=[
                'Output Digital Library',
                'Output HathiTrust'
            ]
        )
        user_options = {
            "Input": "some_path",
            "Package Type": "Capture One",
            "Output Digital Library":
                os.path.join("valid", "path", "that", "exists", "1"),
            "Output HathiTrust":
                os.path.join("valid", "path", "that", "exists", "2"),
        }
        validator.directory_validator = lambda entry: True
        assert validator.explanation(**user_options) == "ok"

    def test_single_invalid_dir(self):
        validator = ht_wf.OutputsValidValuesValidator(
            keys_to_check=[
                'Output Digital Library',
                'Output HathiTrust'
            ]
        )
        user_options = {
            "Input": "some_path",
            "Package Type": "Capture One",
            "Output Digital Library":
                os.path.join("valid", "path", "that", "doesnot", "exist"),
            "Output HathiTrust":
                os.path.join("valid", "path", "that", "exists", "2"),
        }

        validator.directory_validator = \
            lambda entry: entry == user_options['Output Digital Library']

        assert validator.is_valid(**user_options) is False

    def test_single_invalid_dir_message(self):
        validator = ht_wf.OutputsValidValuesValidator(
            keys_to_check=[
                'Output Digital Library',
                'Output HathiTrust'
            ]
        )
        user_options = {
            "Input": "some_path",
            "Package Type": "Capture One",
            "Output Digital Library":
                os.path.join("valid", "path", "that", "doesnot", "exist"),
            "Output HathiTrust":
                os.path.join("valid", "path", "that", "exists", "2"),
        }

        validator.directory_validator = \
            lambda entry: entry != user_options['Output Digital Library']

        assert user_options['Output Digital Library'] in \
               validator.explanation(**user_options)

    def test_multiple_invalid_dir_message(self):
        validator = ht_wf.OutputsValidValuesValidator(
            keys_to_check=[
                'Output Digital Library',
                'Output HathiTrust'
            ]
        )

        user_options = {
            "Input": "some_path",
            "Package Type": "Capture One",
            "Output Digital Library":
                os.path.join("valid", "path", "that", "doesnot", "exist", "1"),
            "Output HathiTrust":
                os.path.join("valid", "path", "that", "doesnot", "exist", "2"),
        }

        validator.directory_validator = \
            lambda entry: entry not in [
                user_options['Output Digital Library'],
                user_options['Output HathiTrust'],
            ]

        explanation = validator.explanation(**user_options)

        assert user_options['Output Digital Library'] in explanation and \
               user_options['Output HathiTrust'] in explanation

    def test_one_valid_on_none(self):
        validator = ht_wf.OutputsValidValuesValidator(
            keys_to_check=[
                'Output Digital Library',
                'Output HathiTrust'
            ]
        )
        user_options = {
            "Input": "some_path",
            "Package Type": "Capture One",
            "Output Digital Library": None,
            "Output HathiTrust":
                os.path.join("valid", "path", "that", "exists"),
        }

        validator.directory_validator = \
            lambda entry: entry == user_options['Output HathiTrust']

        assert validator.is_valid(**user_options) is True


def test_tasks_have_description():
    task = ht_wf.PackageConverter(
        source_path="some_source_path",
        packaging_id="123",
        existing_package=Mock(),
        new_package_root="some_root",
        package_format="HathiTrust jp2"
    )
    assert task.task_description() is not None
