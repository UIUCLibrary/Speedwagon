import contextlib
import pytest


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

    def setLabelText(self, x):
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
