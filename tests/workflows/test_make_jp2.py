import os
from unittest.mock import Mock
import pytest
import speedwagon
from speedwagon.workflows import workflow_make_jp2


@pytest.mark.parametrize("index,label", [
    (0, "Input"),
    (1, "Output"),
    (2, "Profile"),
])
def test_make_jp2_workflow_options(index, label):
    workflow = workflow_make_jp2.MakeJp2Workflow()
    user_options = workflow.get_user_options()
    assert len(user_options) > 0
    assert user_options[index].label == label


@pytest.fixture
def unconfigured_workflow():
    workflow = workflow_make_jp2.MakeJp2Workflow()
    user_options = {i.label: i.value for i in workflow.get_user_options()}

    return workflow, user_options


@pytest.mark.parametrize("profile_name, profile",
                         workflow_make_jp2.ProfileFactory.profiles.items())
def test_discover_task_metadata(monkeypatch, unconfigured_workflow,
                                profile_name, profile):

    workflow, user_options = unconfigured_workflow
    user_options['Input'] = "input_dir"
    user_options['Output'] = "output_dir_path"
    user_options['Profile'] = profile_name
    initial_results = []
    additional_data = {}
    number_of_fake_images = 10

    def mock_locate_source_files(self, root):
        for i_number in range(number_of_fake_images):
            file_name = f"99423682912205899-{str(i_number).zfill(8)}.tif"
            yield os.path.join(root, file_name)

    with monkeypatch.context() as mp:
        mp.setattr(profile, "locate_source_files",
                   mock_locate_source_files)
        new_task_md = workflow.discover_task_metadata(
            initial_results=initial_results,
            additional_data=additional_data,
            **user_options
        )

    assert len(new_task_md) == number_of_fake_images
    assert all(
        x['source_root'] == user_options['Input'] for x in new_task_md
    ) and all(
        x['destination_root'] == user_options['Output'] for x in new_task_md
    ) and all(
        x['new_file_name'].endswith(".jp2") for x in new_task_md
    )


@pytest.mark.parametrize("profile",
                         workflow_make_jp2.ProfileFactory.profiles.values())
def test_create_new_task_generates_subtask(unconfigured_workflow, profile):
    workflow, user_options = unconfigured_workflow
    mock_builder = Mock()
    job_args = {
        'source_root': "/some/source/package",
        'source_file': "123.tif",
        'destination_root': "/some/destination",
        "new_file_name": "123.jp2",
        "relative_location": ".",
        "image_factory": profile.image_factory,
    }
    workflow.create_new_task(
        mock_builder,
        **job_args
    )
    assert mock_builder.add_subtask.called is True
    assert mock_builder.add_subtask.call_count == 2
    assert isinstance(
        mock_builder.add_subtask.call_args_list[0][0][0],
        workflow_make_jp2.EnsurePathTask
    ) and isinstance(
               mock_builder.add_subtask.call_args_list[1][0][0],
               workflow_make_jp2.ConvertFileTask
           )


def test_generate_report_creates_a_report(unconfigured_workflow):
    workflow, user_options = unconfigured_workflow
    job_args = {}
    results = [
        speedwagon.tasks.Result(
            source=workflow_make_jp2.ConvertFileTask,
            data={'file_created': "123.jp2"}
        )
    ]
    message = workflow.generate_report(results, **job_args)
    assert "Results" in message and \
           "123.jp2" in message


def test_package_naming_convention_task(monkeypatch):

    task = \
        workflow_make_jp2.ConvertFileTask(
            source_file="somefile.tif",
            destination_file="somefile.jp2",
            image_factory_name="HathiTrust JPEG 2000"
        )
    task.log = Mock()
    mock_convert = Mock()

    with monkeypatch.context() as mp:
        from uiucprescon import images
        mp.setattr(images, "convert_image", mock_convert)
        mp.setattr(os.path, "exists", lambda x: x == "somefile.jp2")
        assert task.work() is True
    assert mock_convert.called is True
    assert mock_convert.call_args_list[0][0][0] == "somefile.tif" and \
           mock_convert.call_args_list[0][0][1] == "somefile.jp2" and \
           mock_convert.call_args_list[0][0][2] == "HathiTrust JPEG 2000"


@pytest.mark.parametrize("profile_name", ["HathiTrust", "Digital Library"])
def test_create_jp2(monkeypatch, profile_name):
    import pykdu_compress
    workflow = workflow_make_jp2.MakeJp2Workflow()
    initial_results = []
    additional_data = {}
    user_args = {
        'Input': "some_source_path",
        "Output": "somepath",
        "Profile": profile_name
    }
    files_in_package = [
        "12345_1.tif",
        "12345_2.tif"
    ]

    def mock_walk(root):
        return [
            ("12345", ['access'], tuple(files_in_package))
        ]

    def mock_scandir(path):
        for file_name in files_in_package:
            file_mock = Mock()
            file_mock.name = file_name
            file_mock.path = os.path.join(path, file_name)
            yield file_mock

    with monkeypatch.context() as mp:
        mp.setattr(os, "walk", mock_walk)
        mp.setattr(os, "scandir", mock_scandir)
        tasks_md = workflow.discover_task_metadata(
            initial_results=initial_results,
            additional_data=additional_data,
            **user_args
        )
    assert len(tasks_md) > 0
    working_dir = 'some_working_path'
    task_builder = speedwagon.tasks.TaskBuilder(
        speedwagon.tasks.MultiStageTaskBuilder(working_dir),
        working_dir=working_dir
    )
    for task_metadata in tasks_md:
        workflow.create_new_task(task_builder, **task_metadata)
    new_tasks = task_builder.build_task()

    created_files = []

    def mock_kdu_compress_cli2(infile: str, outfile: str,
                               in_args=None, out_args=None) -> int:
        created_files.append(outfile)
        return 0

    with monkeypatch.context() as mp:
        mp.setattr(workflow_make_jp2.os, "makedirs", Mock())
        mp.setattr(pykdu_compress, "kdu_compress_cli2", mock_kdu_compress_cli2)
        for n in new_tasks.subtasks:
            n.work()

    assert len(created_files) == len(files_in_package)
    assert all(
        source_file.replace(".tif", ".jp2") in
        [os.path.basename(created_file) for created_file in created_files]
        for source_file in files_in_package
    )


@pytest.mark.parametrize(
    "task",
    [
        workflow_make_jp2.EnsurePathTask(path="path"),
        workflow_make_jp2.ConvertFileTask(
            source_file="source_file",
            destination_file="destination_file",
            image_factory_name="image_factory_name"


        )
    ]
)
def test_tasks_have_description(task):
    assert task.task_description() is not None


class TestMakeJp2Workflow:
    def test_validate_user_options_success(self, monkeypatch):
        workflow = workflow_make_jp2.MakeJp2Workflow()
        user_args = {
            "Input": os.path.join("some", "source", "path"),
            "Output": os.path.join("some", "output", "path")

        }

        monkeypatch.setattr(
            workflow_make_jp2.os.path, "exists", lambda path: True
        )

        monkeypatch.setattr(
            workflow_make_jp2.os.path, "isdir", lambda path: True
        )

        assert workflow.validate_user_options(**user_args) is True

    def test_validate_user_options_not_exists(self, monkeypatch):
        workflow = workflow_make_jp2.MakeJp2Workflow()
        user_args = {
            "Input": os.path.join("some", "source", "path"),
            "Output": os.path.join("some", "output", "path")

        }

        # Simulate that the input directory does not exists
        def exists(path):
            if path == user_args["Input"]:
                return False
            return True

        monkeypatch.setattr(
            workflow_make_jp2.os.path, "exists", exists
        )

        monkeypatch.setattr(
            workflow_make_jp2.os.path, "isdir", lambda path: True
        )
        with pytest.raises(ValueError):
            workflow.validate_user_options(**user_args)

    def test_validate_user_options_input_not_exists(self, monkeypatch):
        workflow = workflow_make_jp2.MakeJp2Workflow()
        user_args = {
            "Input": os.path.join("some", "source", "path"),
            "Output": os.path.join("some", "output", "path")

        }

        # Simulate that the input directory does not exists
        def exists(path):
            if path == user_args["Output"]:
                return False
            return True

        monkeypatch.setattr(
            workflow_make_jp2.os.path, "exists", exists
        )

        monkeypatch.setattr(
            workflow_make_jp2.os.path, "isdir", lambda path: True
        )
        with pytest.raises(ValueError):
            workflow.validate_user_options(**user_args)

    def test_validate_user_options_input_file_is_error(self, monkeypatch):
        workflow = workflow_make_jp2.MakeJp2Workflow()
        user_args = {
            "Input": os.path.join("some", "source", "file.txt"),
            "Output": os.path.join("some", "output", "path")

        }

        # Simulate that the input is a file
        def isdir(path):
            if path == user_args["Input"]:
                return False
            return True

        monkeypatch.setattr(
            workflow_make_jp2.os.path, "exists", lambda path: True
        )

        monkeypatch.setattr(
            workflow_make_jp2.os.path, "isdir", isdir
        )
        with pytest.raises(ValueError):
            workflow.validate_user_options(**user_args)

    def test_validate_user_options_output_file_is_error(self, monkeypatch):
        workflow = workflow_make_jp2.MakeJp2Workflow()
        user_args = {
            "Input": os.path.join("some", "source", "path"),
            "Output": os.path.join("some", "output", "file.txt")

        }

        # Simulate that the input is a file
        def isdir(path):
            if path == user_args["Output"]:
                return False
            return True

        monkeypatch.setattr(
            workflow_make_jp2.os.path, "exists", lambda path: True
        )

        monkeypatch.setattr(
            workflow_make_jp2.os.path, "isdir", isdir
        )
        with pytest.raises(ValueError):
            workflow.validate_user_options(**user_args)
