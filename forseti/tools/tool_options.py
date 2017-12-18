class ToolOption:

    def __init__(self, name) -> None:
        self.name = name
        # self.data = ""


class ToolOptionDataType(ToolOption):
    def __init__(self, name, data_type=str) -> None:
        super().__init__(name)
        self.data_type = data_type
        self._data = ""

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if not isinstance(value, self.data_type):
            raise TypeError("Invalid type")
        self._data = value
