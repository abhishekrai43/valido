import logging
import os


def get_logger(name: str = __name__):
    """Return a standard logger configured for JSON/structured logging in later phases.

    Keep this small; replace or extend with structlog/OpenTelemetry integration later.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
        console_handler.setFormatter(formatter)
        
        # File handler - log to a file in the current directory
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "valido.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
    return logger
