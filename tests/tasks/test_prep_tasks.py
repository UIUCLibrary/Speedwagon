from unittest.mock import Mock, MagicMock

import pytest
import os
import speedwagon.tasks.prep


def test_make_yaml_task_calls_make_yaml(monkeypatch):
    root_path = "some/sample/root"

    task = speedwagon.tasks.prep.MakeYamlTask(
        package_id="1234",
        source=root_path,
        title_page="1234-0001.tif"
    )

    task.log = Mock()
    mock_package_builder = MagicMock()

    def mock_inplace_package(*args, **kwargs):
        return mock_package_builder

    from pyhathiprep import package_creater
    import shutil
    with monkeypatch.context() as mp:
        mp.setattr(package_creater, "InplacePackage", mock_inplace_package)
        mp.setattr(os, "makedirs", lambda x: None)
        mp.setattr(os.path, "exists", lambda x: True)
        mp.setattr(shutil, "move", lambda source, dest: True)
        assert task.work() is True
    assert mock_package_builder.make_yaml.called is True


def test_generate_checksum_task_task_calls_create_checksum_report(monkeypatch):
    root_path = "some/sample/root"

    task = speedwagon.tasks.prep.GenerateChecksumTask(
        package_id="1234",
        source=root_path,
    )

    task.log = Mock()
    mock_package_builder = MagicMock()

    def mock_inplace_package(*args, **kwargs):
        return mock_package_builder

    from pyhathiprep import package_creater
    import shutil
    with monkeypatch.context() as mp:
        mp.setattr(package_creater, "InplacePackage", mock_inplace_package)
        mp.setattr(os, "makedirs", lambda x: None)
        mp.setattr(os.path, "exists", lambda x: True)
        mp.setattr(shutil, "move", lambda source, dest: True)
        assert task.work() is True
    assert mock_package_builder.create_checksum_report.called is True


def test_prep_task_task_calls_generate_package(monkeypatch):
    root_path = "some/sample/root"

    task = speedwagon.tasks.prep.PrepTask(
        source=root_path,
        title_page="1234-0001.tif"
    )

    task.log = Mock()
    mock_package_builder = MagicMock()

    def mock_inplace_package(*args, **kwargs):
        return mock_package_builder

    from pyhathiprep import package_creater
    with monkeypatch.context() as mp:
        mp.setattr(package_creater, "InplacePackage", mock_inplace_package)
        assert task.work() is True
    assert mock_package_builder.generate_package.called is True


@pytest.mark.parametrize(
    "task",
    [
        speedwagon.tasks.prep.PrepTask(source="source", title_page="title_page"),
        speedwagon.tasks.prep.MakeYamlTask(
            package_id="package_id",
            source="source",
            title_page="title_page"
        ),
        speedwagon.tasks.prep.GenerateChecksumTask(
            package_id="package_id",
            source="source"
        )
    ]
)
def test_tasks_have_description(task):
    assert task.task_description() is not None
