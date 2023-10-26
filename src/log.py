import logging
import os
from pathlib import Path

log_path = Path(os.path.dirname(__file__)).parent / "/var/log/chatgpt/"


def getlogger():
    # create a custom logger if no log handler
    logger = logging.getLogger(__name__)
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        # create handlers
        warn_handler = logging.StreamHandler(log_path + 'warn.log', mode="a")
        info_handler = logging.StreamHandler(log_path + 'info.log', mode="a")
        error_handler = logging.FileHandler(log_path + 'error.log', mode="a")
        warn_handler.setLevel(logging.WARNING)
        error_handler.setLevel(logging.ERROR)
        info_handler.setLevel(logging.INFO)

        # create formatters
        warn_format = logging.Formatter(
            "%(asctime)s - %(funcName)s - %(levelname)s - %(message)s",
        )
        error_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s",
        )
        info_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # set formatter
        warn_handler.setFormatter(warn_format)
        error_handler.setFormatter(error_format)
        info_handler.setFormatter(info_format)

        # add handlers to logger
        logger.addHandler(warn_handler)
        logger.addHandler(error_handler)
        logger.addHandler(info_handler)

    return logger
