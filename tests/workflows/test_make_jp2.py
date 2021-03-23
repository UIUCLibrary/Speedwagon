import os
from unittest.mock import Mock

import pytest

from speedwagon import tasks
from speedwagon.workflows import workflow_make_jp2


@pytest.mark.parametrize("index,label", [
    (0, "Input"),
    (1, "Output"),
    (2, "Profile"),
])
def test_make_jp2_workflow_options(index, label):
    workflow = workflow_make_jp2.MakeJp2Workflow()
    user_options = workflow.user_options()
    assert len(user_options) > 0
    assert user_options[index].label_text == label


@pytest.fixture
def unconfigured_workflow():
    workflow = workflow_make_jp2.MakeJp2Workflow()
    user_options = {i.label_text: i.data for i in workflow.user_options()}

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
        tasks.Result(
            source=workflow_make_jp2.ConvertFileTask,
            data={'file_created': "123.jp2"}
        )
    ]
    message = workflow.generate_report(results, **job_args)
    assert "Results" in message and \
           "123.jp2" in message
