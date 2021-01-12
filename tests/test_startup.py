import argparse
from unittest.mock import Mock, MagicMock

from speedwagon import startup


def test_version_exits_after_being_called(monkeypatch):

    parser = startup.CliArgsSetter.get_arg_parser()
    version_exit_mock = Mock()

    with monkeypatch.context() as m:
        m.setattr(argparse.ArgumentParser, "exit", version_exit_mock)
        parser.parse_args(["--version"])

    version_exit_mock.assert_called()


def test_run_loads_window(qtbot, monkeypatch, tmpdir):
    app = Mock()
    app.exec_ = MagicMock()
    standard_startup = startup.StartupDefault(app=app)
    standard_startup.startup_settings['debug'] = True
    tabs_file = tmpdir / "user.yaml"
    tabs_file.ensure()
    standard_startup.tabs_file = tabs_file

    standard_startup.run()
    assert app.exec_.called is True
