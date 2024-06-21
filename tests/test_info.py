from unittest.mock import Mock, mock_open, patch

import sys
if sys.version_info >= (3, 10):
    from importlib import metadata
else:
    import importlib_metadata as metadata

import speedwagon.info


def test_get_install_packages(monkeypatch):

    def mock_distributions(*args, **kwargs):
        fake_distributions = [
            {
                "Name": 'Spam',
                "Version": '1.0',
            },
            {
                "Name": 'Bacon',
                "Version": '1.1',
            },
            {
                "Name": 'Eggs',
                "Version": '0.1',
            }
        ]
        return [Mock(metadata=d) for d in fake_distributions]

    with monkeypatch.context() as ctx:
        ctx.setattr(metadata, "distributions", mock_distributions)
        system_info = speedwagon.info.SystemInfo()
        assert system_info.get_installed_packages(
            formatter=speedwagon.info.convert_package_metadata_to_string
        ) == [
            'Bacon 1.1',
            'Eggs 0.1',
            'Spam 1.0',
        ]


def test_system_info_to_text_formatter():
    system_info =\
        Mock(
            spec=speedwagon.info.SystemInfo,
            get_installed_packages=Mock(return_value=[
                "Whoosh 2.7.4",
                "Dummy 1.2.3"
            ])
        )
    report = speedwagon.info.system_info_to_text_formatter(system_info)
    assert "Whoosh 2.7.4" in report


def test_write_system_info_to_file_calls_write():
    system_info = \
        Mock(
            spec=speedwagon.info.SystemInfo,
            get_installed_packages=Mock(return_value=[
                "Whoosh 2.7.4",
                "Dummy 1.2.3"
            ])
        )
    mocked_open = mock_open()
    with patch('speedwagon.info.open', mocked_open) as mocked_file:
        speedwagon.info.write_system_info_to_file(
            system_info,
            "fake_file.txt",
            Mock(return_value='dummy')
        )
        handle = mocked_file()
    handle.write.assert_called_once_with("dummy")


class TestSystemInfo:
    def test_get_runtime_information_python_version(self, monkeypatch):
        system_info = speedwagon.info.SystemInfo()
        monkeypatch.setattr(
            speedwagon.info.platform,
            "python_version_tuple",
            Mock(return_value=("3", "11", "2"))
        )
        runtime_info = system_info.get_runtime_information()
        assert runtime_info['python_version'] == "3.11.2"
