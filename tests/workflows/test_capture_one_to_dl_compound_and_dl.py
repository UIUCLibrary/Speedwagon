from unittest.mock import Mock, MagicMock, call

import pytest
from uiucprescon import packager
from speedwagon import tasks, models
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
    user_options["Input"] = "some_real_source_folder"
    user_options["Output Digital Library"] = "./some_real_dl_folder/"
    user_options["Output HathiTrust"]= "./some_real_ht_folder/"
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


class TestWorkflow:

    @pytest.mark.parametrize("dl_outpath, ht_outpath", [
        ("some/real/output/dl", "some/real/output/ht"),
        (None, "some/real/output/ht"),
        ("some/real/output/dl", None),
    ])
    def test_output(self, user_options, monkeypatch, dl_outpath, ht_outpath):
        user_options['Input'] = "some/real/path"
        user_options['Output Digital Library'] = dl_outpath
        user_options['Output HathiTrust'] = ht_outpath
        import os

        def mock_scandir(path):
            for i_number in range(20):
                file_mock = Mock()
                file_mock.name = f"99423682912205899-{str(i_number).zfill(8)}.tif"
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
                task_builder = tasks.TaskBuilder(
                    tasks.MultiStageTaskBuilder("."),
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
    return models.ToolOptionsModel3(workflow.user_options()).get()


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
    validator = ht_wf.OutputValidator(checks)
    assert validator.is_valid(**user_options) is is_valid, validator.explanation(**user_options)

@pytest.mark.parametrize(
    "user_selected_package_type, expected_package_type", [
        ("Capture One", packager.packages.CaptureOnePackage),
        ("Archival collections/Non EAS", packager.packages.ArchivalNonEAS),
        ("Cataloged collections/Non EAS", packager.packages.CatalogedNonEAS),
    ]
)
def test_discover_task_metadata_gets_right_package(user_options, user_selected_package_type, expected_package_type, monkeypatch):
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
