
import logging
import sys


def get_monitor_logger():

    logger = logging.getLogger("MiniShell.ProcessMonitor")

    logger.setLevel(logging.DEBUG)

    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s',
            '%H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger