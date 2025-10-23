import logging

from shadowgate.logging_setup import get_logger


def test_get_logger_returns_logger():
    lg = get_logger("shadowgate.test")
    assert isinstance(lg, logging.Logger)
    lg.debug("test ok")
