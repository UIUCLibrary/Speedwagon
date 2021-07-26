import logging
import os
import shutil
from zipfile import ZipFile

import pykdu_compress
import pytest
from uiucprescon import packager
from uiucprescon.packager import transformations
from uiucprescon.packager.packages import DigitalLibraryCompound
from uiucprescon.packager.packages.collection import Package
from uiucprescon.packager.packages.digital_library_compound import Transform
from uiucprescon.packager.transformations import AbsTransformation

from speedwagon.workflows.workflow_hathi_limited_to_dl_compound import \
    HathiLimitedToDLWorkflow, PackageConverter

@pytest.fixture(scope="module")
def hathi_limited_view_package_dirs(tmpdir_factory):
    test_dir = tmpdir_factory.mktemp(f"hathi_limited", numbered=True)
    sample_package_names = {
        "uiuc.40": [
            (
                "40.mets.xml",
                (
                    "40",
                    [
                        "40.mets.xml"
                    ] +
                    [f"{str(a).zfill(7)}.txt" for a in range(282)] +
                    [f"{str(a).zfill(7)}.jp2" for a in range(282)] +
                    [f"{str(a).zfill(7)}.xml" for a in range(282)]
                )
            )
        ],
        "uiuc.40834v1": [
            (
                "40834v1.mets.xml",
                (
                    "40834v1",
                    [
                        "40834v1.mets.xml"
                    ] +
                    [f"{str(a).zfill(7)}.txt" for a in range(256)] +
                    [f"{str(a).zfill(7)}.tif" for a in range(256)] +
                    [f"{str(a).zfill(7)}.xml" for a in range(256)]
                )
            )
        ],
        "uiuc.5285248v1924": [
            (
                "5285248v1924.mets.xml",
                (
                    "5285248v1924",
                    [
                        "5285248v1924.mets.xml"
                    ] +
                    [f"{str(a).zfill(7)}.txt" for a in range(282)] +
                    [f"{str(a).zfill(7)}.jp2" for a in range(282)] +
                    [f"{str(a).zfill(7)}.xml" for a in range(282)]
                )
            )
        ]
    }

    # eg: 5285248v1924/
    for pkg_name, pkg_data in sample_package_names.items():
        pkg_dir = test_dir.mkdir(pkg_name)

        tmp_dir = test_dir.mkdir(f"build_dir-{pkg_name}")
        for mets_file_filename, archive_data in pkg_data:
            # Add any files to the package
            pkg_dir.join(mets_file_filename).write("")
            bib_id, zip_content = archive_data

            # eg: 5285248v1924/5285248v1924.zip
            with ZipFile(pkg_dir.join(f"{bib_id}.zip"), 'w') as myzip:
                build_package_dir = tmp_dir.mkdir(bib_id)
                for zipped_file in zip_content:
                    generated_file = build_package_dir.join(zipped_file)
                    generated_file.write("")

                    arcname = os.path.join(bib_id, zipped_file)
                    myzip.write(generated_file, arcname=arcname)

    return test_dir


def test_output_input_same_is_invalid(tmpdir):
    temp_dir = tmpdir / "temp"
    temp_dir.mkdir()
    with pytest.raises(ValueError) as e:
        workflow = HathiLimitedToDLWorkflow()
        workflow.validate_user_options(Input=temp_dir.realpath(),
                                       Output=temp_dir.realpath())
    assert "Input cannot be the same as Output" in str(e.value)


def test_output_must_exist(tmpdir):
    temp_dir = tmpdir / "temp"
    temp_dir.mkdir()
    with pytest.raises(ValueError) as e:
        workflow = HathiLimitedToDLWorkflow()
        workflow.validate_user_options(Input=temp_dir.realpath(),
                                       Output="./invalid_folder/")
    assert "Output does not exist" in str(e.value)

@pytest.mark.parametrize("missing", ["Input", "Output"])
def test_no_missing_required(missing, tmpdir):
    temp_dir = tmpdir / "temp"
    temp_dir.mkdir()
    user_args = {
        "Input": temp_dir.realpath(),
        "Output": temp_dir.realpath()
    }
    with pytest.raises(ValueError) as e:
        workflow = HathiLimitedToDLWorkflow()
        user_args[missing] = ""
        workflow.validate_user_options(**user_args)
    assert f"Missing required value for {missing}" in str(e.value)


def test_input_must_exist(tmpdir):
    temp_dir = tmpdir / "temp"
    temp_dir.mkdir()
    with pytest.raises(ValueError) as e:
        workflow = HathiLimitedToDLWorkflow()
        workflow.validate_user_options(Input="./invalid_folder/",
                                       Output=temp_dir.realpath())
    assert "Input does not exist" in str(e.value)


class MockHathiLimitedToDLWorkflow(HathiLimitedToDLWorkflow):

    def create_new_task(self, task_builder, **job_args):
        task_builder.add_subtask(
            MockPackageConverter(src=job_args['package'],
                                 dst=job_args['destination'])
        )


class MockPackageConverter(PackageConverter):

    def __init__(self, src, dst) -> None:
        super().__init__(src, dst)
        self.output_packager = MockDigitalLibraryCompound()


class MockDigitalLibraryCompound(DigitalLibraryCompound):

    @staticmethod
    def _get_transformer(logger, package_builder, destination_root):
        transformer = \
            DigitalLibraryCompound._get_transformer(logger, package_builder,
                                                    destination_root)
        transformer._strategies['ConvertJp2Standard'] = transformations.CopyFile()
        transformer._strategies['ConvertTiff'] = transformations.CopyFile()
        return transformer
    @staticmethod
    def mock_transform(i, source: str, destination: str, logger: logging.Logger) -> str:
        pass


@pytest.mark.slow
def test_hathi_limited_to_dl_compound_run(tool_job_manager_spy,
                                          hathi_limited_view_package_dirs,
                                          monkeypatch,
                                          caplog,
                                          tmpdir):
    output_dir = tmpdir / "output"
    output_dir.mkdir()
    my_logger = logging.getLogger(__file__)

    def mock_transform(*args, **kwargs):
        if len(args) == 3:
            source = args[1]
            destination = args[2]
        else:
            source = kwargs['source']
            destination = kwargs['destination']
        shutil.copyfile(source, destination)

    from uiucprescon.packager.transformations import Transformers
    monkeypatch.setattr(Transformers, "transform", mock_transform)

    tool_job_manager_spy.run(None,
               MockHathiLimitedToDLWorkflow(),
               options={
                   "Input": str(hathi_limited_view_package_dirs),
                   "Output": str(output_dir.realpath())
               },
               logger=my_logger)

    exp_res = output_dir / "40"
    assert os.path.exists(exp_res.realpath()), f"Missing expected directory '{exp_res.relto(tmpdir)}'"


options = [
    (0, "Input"),
    (1, "Output")
]
@pytest.mark.parametrize("index,label", options)
def test_hathi_limited_to_dl_compound_has_options(index, label):
    workflow = HathiLimitedToDLWorkflow()
    user_options = workflow.user_options()
    assert len(user_options) > 0
    assert user_options[index].label_text == label

