import logging
import pytest
from speedwagon.workflows.workflow_hathi_limited_to_dl_compound import \
    HathiLimitedToDLWorkflow


def test_hathi_limited_to_dl_compound_run(tool_job_manager_spy, tmpdir):
    sample_pkg_dir = tmpdir / "sample"
    sample_pkg_dir.mkdir()
    sample_file = sample_pkg_dir / "dummy.txt"
    sample_file.write_text("", encoding="utf8")
    my_logger = logging.getLogger()
    tool_job_manager_spy.run(None,
               HathiLimitedToDLWorkflow(),
               options={
                   "Input": sample_pkg_dir.realpath()},
               logger=my_logger)

    # exp_res = os.path.join(sample_pkg_dir.realpath(), "checksum.md5")
    # assert os.path.exists(exp_res)

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

