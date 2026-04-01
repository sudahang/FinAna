"""Logging configuration for FinAna application.

This module provides centralized logging setup with:
- Trace ID support for request tracking
- Consistent log formatting across all components
- Configurable log levels for different modules
"""

import logging
import sys
from typing import Optional


# Trace ID context storage
import contextvars
_trace_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")


def set_trace_id(trace_id: str):
    """Set trace ID for current context.

    Args:
        trace_id: Unique identifier for request tracing (usually 8 chars)
    """
    _trace_id_ctx.set(trace_id)


def get_trace_id() -> str:
    """Get current trace ID from context.

    Returns:
        Current trace ID or "no-trace" if not set
    """
    return _trace_id_ctx.get() or "no-trace"


class TraceIdFilter(logging.Filter):
    """Logging filter that injects trace ID into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add trace_id attribute to log record.

        Args:
            record: Log record to filter

        Returns:
            True to allow log emission
        """
        record.trace_id = get_trace_id()
        return True


class TraceFormatter(logging.Formatter):
    """Custom formatter that includes trace ID in output."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with trace ID.

        Args:
            record: Log record to format

        Returns:
            Formatted log message
        """
        # Add trace_id if not present
        if not hasattr(record, 'trace_id'):
            record.trace_id = get_trace_id()

        # Use parent formatting
        return super().format(record)


def setup_logging(
    level: int = logging.INFO,
    log_to_file: bool = False,
    log_file: str = "finana.log",
    log_format: str = "detailed"
) -> None:
    """Setup logging configuration for the application.

    Args:
        level: Root logging level (default: INFO)
        log_to_file: Whether to write logs to file (default: False)
        log_file: Path to log file (default: finana.log)
        log_format: Format style - "detailed" or "simple" (default: detailed)

    Example usage:
        ```python
        from logging_config import setup_logging
        import logging

        setup_logging(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        logger.info("Application started")
        ```
    """
    # Define formatters
    if log_format == "simple":
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:  # detailed
        formatter = TraceFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] [TRACE=%(trace_id)s] "
                "[%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(TraceIdFilter())
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_to_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(TraceIdFilter())
        root_logger.addHandler(file_handler)

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Set application module loggers
    logging.getLogger("storage").setLevel(logging.DEBUG if level <= logging.DEBUG else logging.INFO)
    logging.getLogger("workflows").setLevel(logging.DEBUG if level <= logging.DEBUG else logging.INFO)
    logging.getLogger("api").setLevel(logging.DEBUG if level <= logging.DEBUG else logging.INFO)

    # Log startup message
    logging.getLogger(__name__).info(
        f"Logging configured: level={logging.getLevelName(level)}, "
        f"file={log_to_file}"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.

    This is a convenience function that returns a logger
    with the TraceIdFilter automatically applied.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured Logger instance
    """
    logger = logging.getLogger(name)
    return logger
