import argparse
from unittest.mock import Mock

from speedwagon import startup


def test_version_exits_after_being_called(monkeypatch):

    parser = startup.CliArgsSetter.get_arg_parser()
    version_exit_mock = Mock()

    with monkeypatch.context() as m:
        m.setattr(argparse.ArgumentParser, "exit", version_exit_mock)
        parser.parse_args(["--version"])

    version_exit_mock.assert_called()
