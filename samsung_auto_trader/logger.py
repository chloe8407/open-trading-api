import logging

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logger() -> None:
    root = logging.getLogger("samsung_auto_trader")
    if root.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root.setLevel(logging.INFO)
    root.addHandler(handler)


logger = logging.getLogger("samsung_auto_trader")
