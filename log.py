import logging


def getlogger():
    # create a custom logger
    logger = logging.getLogger(__name__)

    # create handlers
    warn_handler = logging.StreamHandler()
    info_handler = logging.StreamHandler()
    error_handler = logging.FileHandler('bot.log', mode='a')
    warn_handler.setLevel(logging.WARNING)
    error_handler.setLevel(logging.ERROR)
    info_handler.setLevel(logging.INFO)

    # create formatters
    warn_format = logging.Formatter(
        '%(name)s - %(funcName)s - %(levelname)s - %(message)s')
    error_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s')
    info_format = logging.Formatter('%(message)s')

    # set formatter
    warn_handler.setFormatter(warn_format)
    error_handler.setFormatter(error_format)
    info_handler.setFormatter(info_format)

    # add handlers to logger
    logger.addHandler(warn_handler)
    logger.addHandler(error_handler)
    logger.addHandler(info_handler)

    return logger
