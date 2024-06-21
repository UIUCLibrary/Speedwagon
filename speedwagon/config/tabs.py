"""Configuration of tabs."""

from __future__ import annotations

import abc
import io
from typing import List, NamedTuple, Dict, Optional, Callable, Iterable

import yaml

import speedwagon.exceptions


class AbsTabsConfigDataManagement(abc.ABC):
    """Abstract base model for managing saving and loading serialized data."""

    @abc.abstractmethod
    def data(self) -> List[CustomTabData]:
        """Get the data for custom tabs."""

    @abc.abstractmethod
    def save(self, tabs: List[CustomTabData]) -> None:
        """Get the data for custom tabs."""


class CustomTabData(NamedTuple):
    """Custom tab data."""

    tab_name: str
    workflow_names: List[str]


class AbsTabsYamlFileReader(abc.ABC):
    """Abstract base class for tabs yaml file reader."""

    @staticmethod
    @abc.abstractmethod
    def read_file(yaml_file: str) -> str:
        """Read file and return a string."""

    @abc.abstractmethod
    def decode_tab_settings_yml_data(self, data: str) -> Dict[str, List[str]]:
        """Decode data."""


class TabsYamlFileReader(AbsTabsYamlFileReader):
    """Tabs yaml file reader."""

    @staticmethod
    def read_file(yaml_file: str) -> str:
        """Read file."""
        with open(yaml_file, encoding="utf-8") as file_handler:
            return file_handler.read()

    def decode_tab_settings_yml_data(self, data: str) -> Dict[str, List[str]]:
        """Decode tab settings yml data."""
        if len(data) == 0:
            return {}
        tabs_config_data = yaml.load(data, Loader=yaml.SafeLoader)
        if not isinstance(tabs_config_data, dict):
            raise speedwagon.exceptions.FileFormatError("Failed to parse file")
        return tabs_config_data


class CustomTabsYamlConfig(AbsTabsConfigDataManagement):
    """YAML config file manager."""

    def __init__(self, yaml_file: str) -> None:
        """Create a new yaml config object.

        Args:
            yaml_file: path to a yaml file to use to read or save to.

        """
        self.yaml_file = yaml_file
        self.file_reader_strategy: AbsTabsYamlFileReader = TabsYamlFileReader()
        self.file_writer_strategy: AbsTabWriter = TabsYamlWriter()
        self.data_reader: Optional[Callable[[], str]] = None

    def decode_data(self, data: str) -> Dict[str, List[str]]:
        """Decode a YAML string to a dictionary."""
        return self.file_reader_strategy.decode_tab_settings_yml_data(data)

    def data(self) -> List[CustomTabData]:
        """Get Yaml file data."""
        try:
            if self.data_reader is not None:
                data = self.data_reader()
            else:
                data = self.file_reader_strategy.read_file(self.yaml_file)
            yml_data = self.file_reader_strategy.decode_tab_settings_yml_data(
                data
            )
        except yaml.YAMLError as error:
            raise speedwagon.exceptions.TabLoadFailure(
                f"{self.yaml_file} file failed to load."
            ) from error
        except FileNotFoundError as error:
            raise speedwagon.exceptions.TabLoadFailure(
                f"Custom tabs file {self.yaml_file} not found"
            ) from error
        except (TypeError, speedwagon.exceptions.FileFormatError) as error:
            raise speedwagon.exceptions.TabLoadFailure() from error
        return [
            CustomTabData(tab_name, workflow_names)
            for tab_name, workflow_names in yml_data.items()
        ]

    def save(self, tabs: List[CustomTabData]) -> None:
        """Write tabs to a yaml file."""
        self.file_writer_strategy.save(self.yaml_file, tabs)


class AbsTabWriter(abc.ABC):  # pylint: disable=R0903
    """Abstract base class for writing tab data."""

    @abc.abstractmethod
    def save(self, file_name: str, tabs: List[CustomTabData]) -> None:
        """Save tabs data to a file format."""


class TabsYamlWriter(AbsTabWriter):
    """Tabs Yaml Writer."""

    def save(self, file_name: str, tabs: List[CustomTabData]) -> None:
        """Save to file."""
        self.write_data(file_name, self.serialize(tabs))

    @staticmethod
    def write_data(file_name: str, data: str) -> None:
        """Write data."""
        with open(file_name, "w", encoding="utf-8") as file_handle:
            file_handle.write(data)

    @staticmethod
    def serialize(tabs: Iterable[CustomTabData]) -> str:
        """Serialize tab info."""
        tabs_data = {
            tab_name: list(tab_workflows) for tab_name, tab_workflows in tabs
        }
        with io.StringIO() as file_handle:
            yaml.dump(tabs_data, file_handle, default_flow_style=False)
            value = file_handle.getvalue()
        return value
