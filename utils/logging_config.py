"""
Centralized logging configuration.

Replaces all print() statements with proper structured logging.

Usage:
    from utils.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("Processing ticker", extra={'ticker': 'AAPL'})
    logger.error("Failed to fetch data", exc_info=True)
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading

# Thread-safe logger cache
_loggers = {}
_lock = threading.Lock()

# Default format
DEFAULT_FORMAT = '[%(asctime)s] %(levelname)s %(name)s: %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors for terminal output."""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        log_message = super().format(record)
        if record.levelname in self.COLORS:
            return f"{self.COLORS[record.levelname]}{log_message}{self.RESET}"
        return log_message


def setup_logging(
    name: str = 'stock_scanner',
    level: int = logging.INFO,
    log_to_file: bool = False,
    log_dir: Optional[Path] = None,
    use_colors: bool = True,
    format_string: str = DEFAULT_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
) -> logging.Logger:
    """
    Configure and return a logger.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to also log to file
        log_dir: Directory for log files (default: logs/)
        use_colors: Use colored output in terminal
        format_string: Log message format
        date_format: Timestamp format

    Returns:
        Configured logger instance
    """
    with _lock:
        # Return existing logger if already configured
        if name in _loggers:
            return _loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Avoid duplicate handlers if logger was partially configured
        if logger.handlers:
            _loggers[name] = logger
            return logger

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        if use_colors and sys.stdout.isatty():
            formatter = ColoredFormatter(format_string, datefmt=date_format)
        else:
            formatter = logging.Formatter(format_string, datefmt=date_format)

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (optional)
        if log_to_file:
            if log_dir is None:
                log_dir = Path('logs')
            log_dir = Path(log_dir)
            log_dir.mkdir(exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_dir / f'{name.replace(".", "_")}_{datetime.now().strftime("%Y%m%d")}.log',
                maxBytes=10_000_000,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(format_string, datefmt=date_format)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        # Prevent propagation to root logger
        logger.propagate = False

        _loggers[name] = logger
        return logger


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get or create a logger for the given module name.

    This is the primary function to use in modules.

    Args:
        name: Module name (use __name__)
        level: Logging level

    Returns:
        Logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Starting scan")
    """
    return setup_logging(name, level=level)


def set_global_level(level: int):
    """Set logging level for all configured loggers."""
    with _lock:
        for logger in _loggers.values():
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)


# Import logging.handlers for RotatingFileHandler
import logging.handlers
