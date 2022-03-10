import abc
import json
from typing import Any, Dict, List, Optional, Union


class AbsOutputOptionDataType(abc.ABC):
    label: str
    widget_name: str

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "widget_name"):
            raise TypeError(f"Can't instantiate abstract class {cls.__name__} "
                            f"without abstract property widget_name")
        return super().__init_subclass__()

    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label
        self.value: Optional[Union[str, int, bool]] = None
        self.placeholder_text: Optional[str] = None

    def serialize(self) -> Dict[str, Any]:
        data = {
            "widget_type": self.widget_name,
            "label": self.label
        }
        if self.placeholder_text is not None:
            data['placeholder_text'] = self.placeholder_text
        return data

    def build_json_data(self) -> str:
        return json.dumps(self.serialize())


class DropDownSelection(AbsOutputOptionDataType):
    widget_name: str = "DropDownSelect"

    def __init__(self, label: str) -> None:
        super().__init__(label)
        self._selections: List[str] = []

    def add_selection(self, label: str) -> None:
        self._selections.append(label)

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()
        if self.placeholder_text is not None:
            data["placeholder_text"] = self.placeholder_text
        data["selections"] = self._selections
        return data


class FileSelectData(AbsOutputOptionDataType):
    widget_name: str = "FileSelect"

    def __init__(self, label: str) -> None:
        super().__init__(label)
        self.filter: Optional[str] = None

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()
        data['filter'] = self.filter
        return data


class TextLineEditData(AbsOutputOptionDataType):
    widget_name = "line_edit"


class DirectorySelect(AbsOutputOptionDataType):
    widget_name = "DirectorySelect"


class BooleanSelect(AbsOutputOptionDataType):
    widget_name = "BooleanSelect"
