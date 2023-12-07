import os.path
import pathlib
from unittest.mock import Mock, MagicMock

import pytest

from speedwagon.workflows import workflow_medusa_preingest
from speedwagon.frontend import interaction
import speedwagon
from speedwagon.tasks import filesystem as filesystem_tasks
import speedwagon.tasks


class TestMedusaPreingestCuration:
    @pytest.fixture
    def default_args(self, workflow):
        return {data.label: data.value for data in workflow.job_options()}

    @pytest.fixture
    def workflow(self):
        return workflow_medusa_preingest.MedusaPreingestCuration()

    def test_default_user_args_are_invalidate(self, workflow, default_args):
        with pytest.raises(ValueError):
            workflow.validate_user_options(**default_args)

    def test_valid_user_args_returns_true(self, workflow, default_args):
        workflow_medusa_preingest.MedusaPreingestCuration.validation_checks = (
            []
        )

        assert workflow.validate_user_options(**default_args) is True

    def test_sort_item_data_unknown_throw(self, workflow, monkeypatch):
        data = [
            "somebaddata",
        ]
        with pytest.raises(ValueError):
            workflow.sort_item_data(data)

    def test_sort_item_data(self, workflow, monkeypatch):
        data = [
            "./some/file.txt",
            "./some/directory/",
        ]
        monkeypatch.setattr(
            workflow_medusa_preingest.os.path,
            "isdir",
            lambda path: path == "./some/directory/",
        )
        monkeypatch.setattr(
            workflow_medusa_preingest.os.path,
            "isfile",
            lambda path: path == "./some/file.txt",
        )
        results = workflow.sort_item_data(data)
        assert results == {
            "files": ["./some/file.txt"],
            "directories": ["./some/directory/"],
        }

    def test_discover_task_metadata(self, workflow, default_args, monkeypatch):
        initial_results = []

        removal_files = ["somefile.txt"]
        removal_dirs = ["somedir", "nested_path"]
        nested_dirs = [os.path.join("nested_path", "a")]

        def isfile(path):
            return path in removal_files

        def isdir(path):
            return path in removal_dirs

        def iterdir(self):
            if self.name == "nested_path":
                return [pathlib.Path(a) for a in nested_dirs]
            return []

        def is_dir(self):
            return self.name in removal_dirs or self.name == os.path.join(
                "nested_path", "a"
            )

        def is_file(self):
            return self.name in removal_files + ["a"]

        monkeypatch.setattr(workflow_medusa_preingest.os.path, "isdir", isdir)
        monkeypatch.setattr(
            workflow_medusa_preingest.os.path, "isfile", isfile
        )
        monkeypatch.setattr(workflow_medusa_preingest.Path, "iterdir", iterdir)
        monkeypatch.setattr(workflow_medusa_preingest.Path, "is_dir", is_dir)
        monkeypatch.setattr(workflow_medusa_preingest.Path, "is_file", is_file)

        new_tasks = workflow.discover_task_metadata(
            initial_results,
            additional_data={
                "to remove": removal_files + removal_dirs + nested_dirs
            },
            **default_args,
        )

        assert all(
            new_task in new_tasks
            for new_task in [
                {"type": "file", "path": "somefile.txt"},
                {"type": "directory", "path": "somedir"},
            ]
        )

    def test_get_additional_info_opens_dialog(
        self,
        workflow,
        default_args,
    ):
        user_request_factory = Mock(spec=interaction.UserRequestFactory)
        user_request_factory.confirm_removal = MagicMock()

        workflow.get_additional_info(
            user_request_factory=user_request_factory,
            options=default_args,
            pretask_results=[MagicMock()],
        )
        assert user_request_factory.confirm_removal.called is True

    @pytest.mark.parametrize(
        "job_args, expected_class",
        [
            (
                {"type": "file", "path": "somefile"},
                filesystem_tasks.DeleteFile,
            ),
            (
                {"type": "directory", "path": "someDirectory"},
                filesystem_tasks.DeleteDirectory,
            ),
        ],
    )
    def test_create_new_task(self, workflow, job_args, expected_class):
        task_builder = Mock(name="task_builder")
        task_builder.add_subtask = Mock(name="add_subtask")
        workflow.create_new_task(task_builder, **job_args)

        assert isinstance(
            task_builder.add_subtask.call_args[0][0], expected_class
        )

    def test_initial_task_adds_finding_task(self, workflow, default_args):
        task_builder = Mock(spec=speedwagon.tasks.TaskBuilder)
        workflow.initial_task(task_builder, **default_args)

        assert (
            task_builder.add_subtask.call_args[0][0].__class__.__name__
            == "FindOffendingFiles"
        )

    def test_generate_report_mentions_file_name(self, workflow, default_args):
        results = [
            Mock(
                spec=speedwagon.tasks.Result,
                source=filesystem_tasks.DeleteFile,
                data="some_file",
            )
        ]
        report = workflow.generate_report(results=results, **default_args)
        assert "some_file" in report


@pytest.fixture()
def default_user_args():
    workflow = workflow_medusa_preingest.MedusaPreingestCuration()
    return {data.label: data.value for data in workflow.job_options()}


def test_validate_missing_values():
    with pytest.raises(ValueError):
        workflow_medusa_preingest.validate_missing_values({})


def test_validate_no_missing_values(default_user_args):
    values = default_user_args.copy()
    values["Path"] = "something"
    workflow_medusa_preingest.validate_missing_values(values)


def test_validate_path_valid(monkeypatch):
    supposed_to_be_real_path = "./some/valid/path"

    monkeypatch.setattr(
        workflow_medusa_preingest.os.path,
        "exists",
        lambda path: path == supposed_to_be_real_path,
    )

    workflow_medusa_preingest.validate_path_valid(
        {"Path": supposed_to_be_real_path}
    )


def test_validate_path_invalid(monkeypatch):
    invalid_path = "./some/valid/path"

    monkeypatch.setattr(
        workflow_medusa_preingest.os.path, "exists", lambda path: False
    )

    with pytest.raises(ValueError):
        workflow_medusa_preingest.validate_path_valid({"Path": invalid_path})


class TestFindOffendingFiles:
    def test_description(self):
        search_path = "./some/path"
        task = workflow_medusa_preingest.FindOffendingFiles(
            **{
                "Path": search_path,
                "Include Subdirectories": True,
                "Locate and delete dot underscore files": True,
                "Locate and delete .DS_Store files": True,
                "Locate and delete Capture One files": True,
                "Locate and delete Thumbs.db files": True,
            }
        )
        assert search_path in task.task_description()

    def test_work_calls_locate_results(self, monkeypatch):
        search_path = "./some/path"
        task = workflow_medusa_preingest.FindOffendingFiles(
            **{
                "Path": search_path,
                "Include Subdirectories": True,
                "Locate and delete dot underscore files": True,
                "Locate and delete .DS_Store files": True,
                "Locate and delete Capture One files": True,
                "Locate and delete Thumbs.db files": True,
            }
        )
        locate_results = Mock()
        monkeypatch.setattr(task, "locate_results", locate_results)
        task.work()

        assert locate_results.called is True

    def test_locate_results_throws_file_not_found_if_not_exists(self):
        search_path = "./some/path"
        task = workflow_medusa_preingest.FindOffendingFiles(
            **{
                "Path": search_path,
                "Include Subdirectories": True,
                "Locate and delete dot underscore files": True,
                "Locate and delete .DS_Store files": True,
                "Locate and delete Capture One files": True,
                "Locate and delete Thumbs.db files": True,
            }
        )
        with pytest.raises(FileNotFoundError):
            task.locate_results()

    # def test_locate_offending_subdirectories_calls_find_capture_one_data(
    #         self,
    #         monkeypatch
    # ):
    #     search_path = "./some/path"
    #     task = workflow_medusa_preingest.FindOffendingFiles(
    #         **{
    #             "Path": search_path,
    #             "Include Subdirectories": True,
    #             "Locate and delete dot underscore files": True,
    #             "Locate and delete .DS_Store files": True,
    #             "Locate and delete Capture One files": True,
    #             "Locate and delete Thumbs.db files": True,
    #         }
    #     )
    #
    #     find_capture_one_data = MagicMock()
    #     monkeypatch.setattr(workflow_medusa_preingest,
    #                         "find_capture_one_data",
    #                         find_capture_one_data)
    #     list(task.locate_offending_subdirectories(search_path))
    #     assert find_capture_one_data.called is True

    @pytest.fixture()
    def offending_files(self):
        def _make_mock_offending_files(search_path):
            ds_store_file = Mock(
                spec_set=pathlib.Path,
                parts=(search_path, ".DS_Store"),
                is_dir=Mock(return_value=True),
                is_file=Mock(return_value=False),
            )
            ds_store_file.name = ".DS_Store"

            dot_under_score_file = Mock(
                spec_set=pathlib.Path,
                parts=(search_path, "._cache"),
                is_dir=Mock(return_value=False),
                is_file=Mock(return_value=True),
            )

            dot_under_score_file.name = "._cache"

            return [ds_store_file, dot_under_score_file]

        return _make_mock_offending_files

    @pytest.mark.parametrize(
        "underscore, ds_store, expected_file, expected_excluded_file",
        [
            (False, True, ".DS_Store", None),
            (True, True, ".DS_Store", None),
            (False, False, None, ".DS_Store"),
            (True, False, "._cache", None),
            (True, True, "._cache", None),
            (False, False, None, "._cache"),
        ],
    )
    def test_locate_offending_files(
        self,
        monkeypatch,
        offending_files,
        underscore,
        ds_store,
        expected_file,
        expected_excluded_file,
    ):
        search_path = os.path.join(".", "some", "path")
        offending_files(search_path)
        task = workflow_medusa_preingest.FindOffendingFiles(
            **{
                "Path": search_path,
                "Include Subdirectories": True,
                "Locate and delete dot underscore files": underscore,
                "Locate and delete .DS_Store files": ds_store,
                "Locate and delete Capture One files": True,
                "Locate and delete Thumbs.db files": True,
            }
        )

        task.filesystem_locator_strategy.locate = Mock(
            return_value=[
                os.path.join(*i.parts) for i in offending_files(search_path)
            ]
        )
        monkeypatch.setattr(
            workflow_medusa_preingest.os.path, "exists", lambda: True
        )
        if expected_file:
            assert os.path.join(search_path, expected_file) in list(
                task.locate_results()
            )

        if expected_excluded_file:
            assert os.path.join(
                search_path, expected_excluded_file
            ) not in list(task.locate_results())

    def test_locate_results(self):
        search_path = os.path.join(".", "some", "path")
        task = workflow_medusa_preingest.FindOffendingFiles(
            **{
                "Path": search_path,
                "Include Subdirectories": True,
                "Locate and delete dot underscore files": False,
                "Locate and delete .DS_Store files": True,
                "Locate and delete Capture One files": True,
                "Locate and delete Thumbs.db files": False,
            }
        )

        task.filesystem_locator_strategy = Mock(
            locate=Mock(
                return_value=[
                    os.path.join(search_path, ".DS_Store"),
                    os.path.join(search_path, "file.txt"),
                ]
            )
        )
        assert task.locate_results() == [
            os.path.join(search_path, ".DS_Store")
        ]


def test_find_capture_one_data_nothing_found(monkeypatch):
    monkeypatch.setattr(
        workflow_medusa_preingest.os.path, "exists", lambda path: False
    )
    items_found = list(
        workflow_medusa_preingest.find_capture_one_data(directory=".")
    )
    assert not items_found


def test_find_capture_one_data_found(monkeypatch):
    starting_point = "."
    monkeypatch.setattr(
        workflow_medusa_preingest.os.path,
        "exists",
        lambda path: path == os.path.join(starting_point, "CaptureOne"),
    )

    def walk(top, *args, **kwargs):
        return [
            [top, (["Cache", "Settings91"]), ([])],
            [os.path.join(top, "Cache"), (), (["someFile"])],
        ]

    monkeypatch.setattr(workflow_medusa_preingest.os, "walk", walk)
    items_found = list(
        workflow_medusa_preingest.find_capture_one_data(
            directory=starting_point
        )
    )
    assert items_found == [
        os.path.join(starting_point, "CaptureOne", "Cache"),
        os.path.join(starting_point, "CaptureOne", "Settings91"),
        os.path.join(starting_point, "CaptureOne", "Cache", "someFile"),
        os.path.join(starting_point, "CaptureOne"),
    ]


class TestFilesystemItemLocator:
    def test_locate_contents_order(self, monkeypatch):
        files = {
            "starting_point": [
                pathlib.Path("starting_point/empty_path"),
                pathlib.Path("starting_point/nested_path/file1.txt"),
                pathlib.Path("starting_point/nested_path/file2.txt"),
                pathlib.Path("starting_point/nested_path"),
                pathlib.Path("starting_point/dummy.txt"),
            ],
        }

        def iterdir(self):
            return files[str(self)]

        monkeypatch.setattr(
            workflow_medusa_preingest.os.path,
            "exists",
            lambda path: path in files,
        )

        monkeypatch.setattr(workflow_medusa_preingest.Path, "iterdir", iterdir)
        locator = workflow_medusa_preingest.FilesystemItemLocator()
        assert set(locator.locate("starting_point")) == {
            "empty_path",
            os.path.join("nested_path", "file2.txt"),
            os.path.join("nested_path", "file1.txt"),
            "nested_path",
            "dummy.txt",
            os.path.join("."),
        }
