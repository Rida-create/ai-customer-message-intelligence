import logging
import sys

from app.config import settings


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(settings.LOG_LEVEL)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logger()