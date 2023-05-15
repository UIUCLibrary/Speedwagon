import pytest
import logging

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QtCore = pytest.importorskip("PySide6.QtCore")

from speedwagon.frontend.qtwidgets import logging_helpers


class TestQtSignalLogHandler:
    def test_signal_emitted(self, qtbot):
        handler = logging_helpers.QtSignalLogHandler()
        logger = logging.Logger("my_hander")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        with qtbot.wait_signal(handler.signals.messageSent) as e:
            logger.log(level=logging.INFO, msg="hello")
        assert e.args[0] == "hello"

