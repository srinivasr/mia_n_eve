import logging
import sys

def setup_logger(name: str) -> logging.Logger:
    """Configures a standardized logger for the Mia backend."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.propagate = False  # Prevent duplicate lines from root logger
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - [%(name)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        ))
        logger.addHandler(handler)
        
        # File handler
        file_handler = logging.FileHandler('main.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - [%(name)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        ))
        logger.addHandler(file_handler)
    return logger
