"""Export data to file."""

from __future__ import annotations

import functools
import typing

from typing import Dict, Callable, Iterable, List, Tuple
import sys

from speedwagon import config

if sys.version_info < (3, 10):  # pragma: no cover
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec

if typing.TYPE_CHECKING:
    from speedwagon.frontend.qtwidgets.models.settings import WorkflowsSettings
    from speedwagon.config import CustomTabData

__all__ = [
    "write_customized_tab_data",
    "write_plugins_config_file",
    "write_global_settings_to_config_file",
    "write_customized_tab_data",
]

P = ParamSpec("P")


def report_write_success(func: Callable[P, bool]) -> Callable[P, bool]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> bool:
        try:
            return func(*args, **kwargs)
        except OSError:
            return False

    return wrapper


def serialize_workflow_settings(data: WorkflowsSettings) -> str:
    serializer = config.workflow.SettingsYamlSerializer
    return serializer.serialize_structure_to_yaml(
        {
            workflow_name: serializer.structure_workflow_data(value)
            for (workflow_name, value) in data.items()
        }
    )


@report_write_success
def write_workflow_settings_to_fp(
    fp: typing.TextIO,
    data: WorkflowsSettings,
    serialization_strategy=serialize_workflow_settings,
) -> bool:
    fp.write(serialization_strategy(data))
    return True


@report_write_success
def write_workflow_settings_to_file(
    yaml_file: str,
    data: WorkflowsSettings,
    on_success_save_updated_settings: Callable[[], None],
    serialization_strategy=serialize_workflow_settings,
) -> bool:
    with open(yaml_file, "w", encoding="utf-8") as fp:
        success = write_workflow_settings_to_fp(
            fp, data, serialization_strategy
        )
    on_success_save_updated_settings()
    return success


def plugins_config_file_serialization(
    config_file: str, data: Dict[str, List[Tuple[str, bool]]]
) -> str:
    ini_serializer = config.plugins.IniSerializer()
    ini_serializer.parser.read(config_file)
    return ini_serializer.serialize({"enabled_plugins": data})


@report_write_success
def write_plugins_config_file(
    config_file: str,
    data: Dict[str, List[Tuple[str, bool]]],
    on_success_save_updated_settings: Callable[[], None],
    serialization_strategy=plugins_config_file_serialization,
) -> bool:
    """Write plugin configuration to file.

    Args:
        config_file: path to config file to use
        data: plugin configuration data
        on_success_save_updated_settings: callback to use when successful
        serialization_strategy: Serialization strategy to convert to string

    Returns: True on success and False or failure

    """
    # This has to be called before opening the file to write because
    # serializing the data requires reading the existing file
    serialized_data = serialization_strategy(config_file, data)
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(serialized_data)
    on_success_save_updated_settings()
    return True


@report_write_success
def write_global_settings_to_config_file(
    config_file: str,
    data: config.common.SettingsData,
    on_success_save_updated_settings: Callable[[], None],
) -> bool:
    """Write Global Settings to a config file.

    Args:
        config_file: path to config file to use
        data: Settings data
        on_success_save_updated_settings: callback to use when successful

    Returns: True on success and False or failure

    """
    ini_manager = config.IniConfigManager(config_file)
    ini_manager.save({"GLOBAL": data})
    on_success_save_updated_settings()
    return True


def serialize_tab_data(data: Iterable[CustomTabData]) -> str:
    return config.tabs.TabsYamlWriter().serialize(data)


@report_write_success
def write_customized_tab_data(
    config_file: str,
    data: Iterable[CustomTabData],
    on_success_save_updated_settings: Callable[[], None],
    serialization_strategy: Callable[
        [Iterable[CustomTabData]], str
    ] = serialize_tab_data,
) -> bool:
    """Write tab information to file.

    Args:
        config_file: path to config file to use
        data: custom tabs data
        on_success_save_updated_settings: callback to use when successful
        serialization_strategy: Serialization strategy to convert to string.

    Returns: True on success and False or failure

    """
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(serialization_strategy(data))
    on_success_save_updated_settings()
    return True
