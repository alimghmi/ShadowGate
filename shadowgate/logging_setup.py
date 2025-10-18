import logging

_PACKAGE_LOGGER_NAME = "shadowgate"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    pkg = logging.getLogger(_PACKAGE_LOGGER_NAME)
    if not pkg.handlers:
        pkg.addHandler(logging.NullHandler())
    return logger
