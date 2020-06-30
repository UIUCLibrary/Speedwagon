import contextlib
import os

import pytest
from speedwagon import runner_strategies
from speedwagon.worker import ToolJobManager
import logging

from speedwagon.workflows.workflow_make_checksum import \
    MakeChecksumBatchSingleWorkflow


class SpyDialogBox:

    def __init__(self) -> None:
        super().__init__()
        self._value = None
        self._maxiumum = None

    def setRange(self, a, b):
        pass

    def accept(self):
        pass

    def close(self):
        pass

    def setWindowTitle(self, x):
        pass

    def setMaximum(self, value, *args, **kwargs):
        self._maxiumum = value

    def show(self):
        pass

    def maximum(self):
        return self._maxiumum

    def value(self):
        return self._value

    def setValue(self, x):
        self._value = x


class SpyWorkRunner(contextlib.AbstractContextManager):

    def __init__(self, parent):
        self.dialog = SpyDialogBox()
        self.was_aborted = False

    def __exit__(self, exc_type, exc_value, traceback):
        return

    def progress_dialog_box_handler(self, *args, **kwargs):
        pass


class SpyToolJobManager(ToolJobManager):
    def open(self, parent, runner, *args, **kwargs):
        return SpyWorkRunner(*args, **kwargs, parent=parent)

    def flush_message_buffer(self):
        pass


def test_singleChecksum(tmpdir):
    sample_pkg_dir = tmpdir / "sample"
    sample_pkg_dir.mkdir()
    sample_file = sample_pkg_dir / "dummy.txt"
    sample_file.write_text("", encoding="utf8")
    with SpyToolJobManager() as e:
        manager_strat = runner_strategies.UsingExternalManagerForAdapter(
            manager=e)

        runner = runner_strategies.RunRunner(manager_strat)
        my_logger = logging.getLogger()
        runner.run(None,
                   MakeChecksumBatchSingleWorkflow(),
                   options={
                       "Input": sample_pkg_dir.realpath()},
                   logger=my_logger)

    exp_res = os.path.join(sample_pkg_dir.realpath(), "checksum.md5")
    assert os.path.exists(exp_res)
