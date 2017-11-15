import abc
from PyQt5 import QtWidgets

class AbsTool(metaclass=abc.ABCMeta):
    name = None  # type: str
    description = None  # type: str
    def __init__(self) -> None:
        super().__init__()
        self.options = []  # type: ignore


class AbsToolData(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def widget(self):
        pass

    def __init__(self):
        self.label = ""

    def __del__(self):
        print("Deteting")


class SelectDirectory(AbsToolData):
    @property
    def widget(self):
        return QtWidgets.QLineEdit()


class MakeChecksumBatch(AbsTool):
    name = "Make Checksum Batch"
    description = "Makes a checksums"

    def __init__(self) -> None:
        super().__init__()
        source = SelectDirectory()
        source.label = "Source"
        self.options.append(source)


class Spam(AbsTool):
    name = "Spam"
    description = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin ac diam id purus pretium " \
                  "venenatis. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia " \
                  "Curae; Fusce laoreet fermentum lorem et pretium. Duis iaculis venenatis sagittis. Nulla tristique " \
                  "tellus at dolor laoreet maximus. Aenean ac posuere augue, quis volutpat felis. Phasellus egestas " \
                  "orci id erat fringilla, in euismod purus luctus. Proin faucibus condimentum imperdiet. Lorem " \
                  "ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque porttitor eu erat at congue. " \
                  "Quisque feugiat pulvinar eleifend. Nulla tincidunt nibh velit, non fermentum lorem pharetra at. " \
                  "Sed eleifend sapien ut faucibus convallis. Orci varius natoque penatibus et magnis dis parturient " \
                  "montes, nascetur ridiculus mus. Nullam lacinia sed augue quis iaculis. Aliquam commodo dictum mi, " \
                  "non semper quam varius ut."

    def __init__(self) -> None:
        super().__init__()

        input_data = SelectDirectory()
        input_data.label = "Input"
        self.options.append(input_data)

        output_data = SelectDirectory()
        output_data.label = "Output"
        self.options.append(output_data)


class Eggs(AbsTool):
    name = "Eggs"
    description = "Sed odio sem, vestibulum a lacus sed, posuere porta neque. Ut urna arcu, dignissim a dolor ac, " \
                  "sollicitudin pellentesque mi. Curabitur feugiat interdum mauris nec venenatis. In arcu elit, " \
                  "scelerisque et bibendum id, faucibus id enim. Proin dui mi, imperdiet eget varius ut, faucibus at " \
                  "lectus. Sed accumsan quis turpis id bibendum. Mauris in ligula nec tortor vulputate vulputate. " \
                  "Nullam tincidunt leo nec odio tincidunt malesuada. Integer ut massa dictum, scelerisque turpis " \
                  "eget, auctor nibh. Vestibulum sollicitudin sem eget enim congue tristique. Cras sed purus ac diam " \
                  "pulvinar scelerisque et efficitur justo. Duis eu nunc arcu"

    def __init__(self) -> None:
        super().__init__()

        input_data = SelectDirectory()
        input_data.label = "Goes In"
        self.options.append(input_data)

        output_data = SelectDirectory()
        output_data.label = "Goes out"
        self.options.append(output_data)