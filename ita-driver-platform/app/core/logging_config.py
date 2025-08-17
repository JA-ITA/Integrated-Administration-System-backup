"""
Logging configuration for the Island Traffic Authority application.
Provides structured JSON logging with appropriate formatting for development and production.
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any

from core.config import settings


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration based on environment."""
    
    # Base logging configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {
                "format": "%(levelname)s - %(name)s - %(message)s",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "simple" if settings.is_development else "json",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "ita": {
                "level": settings.LOG_LEVEL,
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "alembic": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO" if settings.is_development else "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console"],
        },
    }
    
    # Add file handler if log file is specified
    if settings.LOG_FILE:
        log_path = Path(settings.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.LOG_LEVEL,
            "formatter": "json",
            "filename": str(log_path),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
        }
        
        # Add file handler to all loggers
        for logger_config in config["loggers"].values():
            logger_config["handlers"].append("file")
        config["root"]["handlers"].append("file")
    
    # Adjust for development environment
    if settings.is_development:
        # More verbose SQLAlchemy logging
        config["loggers"]["sqlalchemy.engine"] = {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        }
        
        # Enable detailed formatter for console in development
        config["handlers"]["console"]["formatter"] = "detailed"
    
    # Adjust for testing environment
    if settings.is_testing:
        # Reduce log noise in tests
        config["handlers"]["console"]["level"] = "WARNING"
        config["loggers"]["ita"]["level"] = "WARNING"
    
    return config


def setup_logging():
    """Setup logging configuration for the application."""
    
    # Install python-json-logger if using JSON logging
    if settings.LOG_FORMAT == "json" and not settings.is_development:
        try:
            import pythonjsonlogger
        except ImportError:
            print("Warning: pythonjsonlogger not installed. Falling back to simple format.")
            # Fallback to simple format if JSON logger is not available
            config = get_logging_config()
            for handler in config["handlers"].values():
                if handler.get("formatter") == "json":
                    handler["formatter"] = "detailed"
    
    # Apply logging configuration
    logging_config = get_logging_config()
    logging.config.dictConfig(logging_config)
    
    # Set up logger for this module
    logger = logging.getLogger("ita.logging")
    logger.info(f"Logging configured - Level: {settings.LOG_LEVEL}, Format: {settings.LOG_FORMAT}")
    
    # Log environment and configuration info
    logger.info(
        f"Application starting - Environment: {settings.ENVIRONMENT}, Debug: {settings.DEBUG}"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(f"ita.{name}")


# Custom log filters and formatters
class HealthCheckFilter(logging.Filter):
    """Filter out health check requests from logs."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out health check endpoints."""
        message = record.getMessage()
        return "/health" not in message and "/metrics" not in message


class SensitiveDataFilter(logging.Filter):
    """Filter out sensitive data from logs."""
    
    SENSITIVE_PATTERNS = [
        "password",
        "token",
        "secret",
        "key",
        "authorization",
        "cookie",
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out records containing sensitive data."""
        message = record.getMessage().lower()
        return not any(pattern in message for pattern in self.SENSITIVE_PATTERNS)


# Context managers for structured logging
class LogContext:
    """Context manager for adding contextual information to logs."""
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


# Performance logging utilities
def log_performance(func):
    """Decorator to log function performance."""
    import functools
    import time
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_logger("performance")
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{func.__name__} completed in {duration:.4f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} failed after {duration:.4f}s: {str(e)}")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_logger("performance")
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{func.__name__} completed in {duration:.4f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} failed after {duration:.4f}s: {str(e)}")
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper