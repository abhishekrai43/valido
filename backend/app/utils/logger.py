import logging


def get_logger(name: str = __name__):
    """Return a standard logger configured for JSON/structured logging in later phases.

    Keep this small; replace or extend with structlog/OpenTelemetry integration later.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
