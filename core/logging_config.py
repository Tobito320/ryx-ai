"""
Ryx AI - Logging Configuration
Provides comprehensive logging setup with rotation and formatting
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from core.paths import get_log_dir


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for terminal output"""

    COLORS = {
        'DEBUG': '\033[0;36m',     # Cyan
        'INFO': '\033[0;32m',      # Green
        'WARNING': '\033[1;33m',   # Yellow
        'ERROR': '\033[0;31m',     # Red
        'CRITICAL': '\033[1;31m',  # Bold Red
    }
    RESET = '\033[0m'

    def format(self, record):
        # Add color to levelname
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"

        return super().format(record)


def setup_logging(
    name: str = 'ryx_ai',
    level: int = logging.INFO,
    enable_file: bool = True,
    enable_console: bool = True
) -> logging.Logger:
    """
    Setup logging configuration

    Args:
        name: Logger name
        level: Logging level
        enable_file: Enable file logging
        enable_console: Enable console logging

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = ColoredFormatter(
        '%(levelname)s: %(message)s'
    )

    # File handler with rotation
    if enable_file:
        log_dir = get_log_dir()
        log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get or create a logger

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    # Setup if not already configured
    if not logger.handlers:
        return setup_logging(name, level, enable_file=True, enable_console=False)

    return logger
