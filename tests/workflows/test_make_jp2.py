import os
from unittest.mock import Mock

import pytest

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
