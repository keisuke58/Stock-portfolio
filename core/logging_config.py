"""
Centralized logging configuration.

Provides consistent logging setup across all modules with:
- Console output with colors (optional)
- File logging with rotation
- JSON format for production environments
- Configurable log levels per module
"""
import logging
import logging.handlers
import sys
import json
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Output format:
    {
        "timestamp": "2026-01-24T10:30:00.000Z",
        "level": "INFO",
        "logger": "fetchers.yahoo",
        "message": "Fetched price for AAPL",
        "extra": {...}
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)

        # Add extra fields if present
        extra = {k: v for k, v in record.__dict__.items()
                 if k not in ('name', 'msg', 'args', 'created', 'filename',
                              'funcName', 'levelname', 'levelno', 'lineno',
                              'module', 'msecs', 'pathname', 'process',
                              'processName', 'relativeCreated', 'stack_info',
                              'thread', 'threadName', 'exc_info', 'exc_text',
                              'message', 'taskName')}
        if extra:
            log_obj['extra'] = extra

        return json.dumps(log_obj)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for better readability.
    """

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def __init__(self, fmt: str = None, use_colors: bool = True):
        super().__init__(fmt or '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors and record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
            )
        return super().format(record)


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    json_format: bool = False,
    use_colors: bool = True,
    max_bytes: int = 10_000_000,  # 10MB
    backup_count: int = 5,
    module_levels: Optional[Dict[str, int]] = None
) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Default logging level (default: INFO)
        log_file: Optional file path for log output
        json_format: Use JSON format for logs (for production)
        use_colors: Use colored output in console (default: True)
        max_bytes: Max size of log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
        module_levels: Dict of module names to their log levels

    Example:
        setup_logging(
            level=logging.INFO,
            log_file='logs/app.log',
            module_levels={
                'urllib3': logging.WARNING,
                'yfinance': logging.WARNING,
            }
        )
    """
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        # Use colored formatter for console
        console_handler.setFormatter(ColoredFormatter(use_colors=use_colors))

    handlers.append(console_handler)

    # File handler (optional)
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Use rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)

        # Always use standard format for file logs
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))

        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(level=level, handlers=handlers, force=True)

    # Set levels for noisy third-party loggers
    noisy_loggers = {
        'urllib3': logging.WARNING,
        'yfinance': logging.WARNING,
        'requests': logging.WARNING,
        'httpx': logging.WARNING,
        'httpcore': logging.WARNING,
    }

    for logger_name, logger_level in noisy_loggers.items():
        logging.getLogger(logger_name).setLevel(logger_level)

    # Apply custom module levels
    if module_levels:
        for module_name, module_level in module_levels.items():
            logging.getLogger(module_name).setLevel(module_level)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.

    This is a convenience wrapper around logging.getLogger()
    that ensures logging is configured.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# ============================================================================
# Convenience functions for common setups
# ============================================================================

def setup_development_logging() -> None:
    """Setup logging for development (colored console output)."""
    setup_logging(
        level=logging.DEBUG,
        use_colors=True,
        json_format=False
    )


def setup_production_logging(log_file: str = 'logs/app.log') -> None:
    """Setup logging for production (JSON format, file logging)."""
    setup_logging(
        level=logging.INFO,
        log_file=log_file,
        json_format=True,
        use_colors=False
    )


def setup_test_logging() -> None:
    """Setup logging for testing (minimal output)."""
    setup_logging(
        level=logging.WARNING,
        use_colors=False,
        json_format=False
    )
