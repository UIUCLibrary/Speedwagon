"""Toolkit for generating new workflows."""

import abc
import json
from typing import Any, Dict, List, Optional, Union


class AbsOutputOptionDataType(abc.ABC):
    """Base case for generating user option types."""

    label: str
    widget_name: str

    def __init_subclass__(cls) -> None:
        """Verify that any subclass has a widget_name defined."""
        if not hasattr(cls, "widget_name"):
            raise TypeError(f"Can't instantiate abstract class {cls.__name__} "
                            f"without abstract property widget_name")
        return super().__init_subclass__()

    def __init__(self, label: str) -> None:
        """Create a new output time with a given label."""
        super().__init__()
        self.label = label
        self.value: Optional[Union[str, int, bool]] = None
        self.placeholder_text: Optional[str] = None

    def serialize(self) -> Dict[str, Any]:
        """Serialize the data."""
        data = {
            "widget_type": self.widget_name,
            "label": self.label
        }
        if self.placeholder_text is not None:
            data['placeholder_text'] = self.placeholder_text
        return data

    def build_json_data(self) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.serialize())


class ChoiceSelection(AbsOutputOptionDataType):
    """Choice of predefined strings."""

    widget_name: str = "ChoiceSelection"

    def __init__(self, label: str) -> None:
        """Present the user with a possible selection of choices."""
        super().__init__(label)
        self._selections: List[str] = []

    def add_selection(self, label: str) -> None:
        """Add a possible choice for the user to select."""
        self._selections.append(label)

    def serialize(self) -> Dict[str, Any]:
        """Serialize the data.

        Notes:
            placeholder_text and selections are added here.
        """
        data = super().serialize()
        if self.placeholder_text is not None:
            data["placeholder_text"] = self.placeholder_text
        data["selections"] = self._selections
        return data


class FileSelectData(AbsOutputOptionDataType):
    """File selection."""

    widget_name: str = "FileSelect"

    def __init__(self, label: str) -> None:
        """Select a file."""
        super().__init__(label)
        self.filter: Optional[str] = None

    def serialize(self) -> Dict[str, Any]:
        """Serialize the data.

        Notes:
            filter is added for selecting certain file types.
        """
        data = super().serialize()
        data['filter'] = self.filter
        return data


class TextLineEditData(AbsOutputOptionDataType):
    """Single text line."""

    widget_name = "line_edit"


class DirectorySelect(AbsOutputOptionDataType):
    """Directory path selection."""

    widget_name = "DirectorySelect"


class BooleanSelect(AbsOutputOptionDataType):
    """Boolean selection."""

    widget_name = "BooleanSelect"
