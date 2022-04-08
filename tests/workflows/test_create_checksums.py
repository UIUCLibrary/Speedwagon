
import os

import logging
from unittest.mock import Mock, MagicMock

from speedwagon import runner_strategies
from speedwagon.frontend.qtwidgets import runners
from speedwagon.workflows.workflow_make_checksum import \
    MakeChecksumBatchSingleWorkflow, MakeChecksumBatchMultipleWorkflow


def test_singleChecksum(qtbot, tool_job_manager_spy, tmpdir, monkeypatch):
    sample_pkg_dir = tmpdir / "sample"
    sample_pkg_dir.mkdir()
    sample_file = sample_pkg_dir / "dummy.txt"
    sample_file.write_text("", encoding="utf8")
    my_logger = logging.getLogger()

    monkeypatch.setattr(runners, "QtDialogProgress", MagicMock())
    tool_job_manager_spy.run(
               MakeChecksumBatchSingleWorkflow(),
               options={
                   "Input": sample_pkg_dir.realpath()},
               logger=my_logger)

    exp_res = os.path.join(sample_pkg_dir.realpath(), "checksum.md5")
    assert os.path.exists(exp_res)


def test_singleChecksum_has_options():
    workflow = MakeChecksumBatchSingleWorkflow()
    user_options = workflow.get_user_options()
    assert len(user_options) > 0


def test_mutipleChecksum(qtbot, tool_job_manager_spy, tmpdir, monkeypatch):
    number_of_test_packages = 2
    monkeypatch.setattr(runners, "QtDialogProgress", MagicMock())
    for p_i in range(number_of_test_packages):
        sample_pkg_dir = tmpdir / f"sample_{p_i+1}"
        sample_pkg_dir.mkdir()
        for f_i in range(4):
            sample_file = sample_pkg_dir / f"dummy_{f_i+1}.txt"
            sample_file.write_text("", encoding="utf8")
    tool_job_manager_spy.run(MakeChecksumBatchMultipleWorkflow(),
                             options={
                                 "Input": tmpdir.realpath()},
                             logger=logging.getLogger()
                             )
    for p_i in range(number_of_test_packages):
        sample_pkg_dir = tmpdir / f"sample_{p_i + 1}"
        exp_res = os.path.join(sample_pkg_dir, "checksum.md5")
        assert os.path.exists(exp_res)


def test_multipleChecksum_has_options():
    workflow = MakeChecksumBatchMultipleWorkflow()
    user_options = workflow.get_user_options()
    assert len(user_options) > 0
