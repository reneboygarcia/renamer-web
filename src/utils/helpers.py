import logging
import os
from functools import wraps
from typing import Optional, Callable, Any


def setup_logger(name: str = "tv_show_renamer") -> logging.Logger:
    """Configure and return a logger instance with sensitive data filtering."""
    logger = logging.getLogger(name)

    if not logger.handlers:  # Prevent adding handlers multiple times
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.propagate = False

    return logger


def sanitize_log_message(message: str) -> str:
    """Remove sensitive information from log messages."""
    sensitive_keys = ["api_key", "TMDB_API_KEY", "token", "password"]
    sanitized_message = str(message)

    for key in sensitive_keys:
        if key.upper() in os.environ:
            sanitized_message = sanitized_message.replace(
                os.environ[key.upper()], f"[{key.upper()}_HIDDEN]"
            )

    return sanitized_message


def log_safely(func: Callable) -> Callable:
    """Decorator to ensure all logging calls are sanitized."""
    logger = setup_logger()

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"Error in {func.__name__}: {sanitize_log_message(str(e))}"
            )
            raise

    return wrapper


def format_show_name(name: str) -> str:
    """Format show name with consistent casing and spacing."""
    if not name:
        return ""
        
    # Remove extra whitespace
    name = " ".join(name.split())
    
    # Title case the name, but handle special cases
    words = name.title().split()
    articles = {'A', 'An', 'The', 'And', 'Or', 'But', 'Nor', 'For', 'Yet', 'So'}
    
    for i, word in enumerate(words):
        # Keep articles lowercase unless they're the first word
        if i > 0 and word in articles:
            words[i] = word.lower()
            
    return " ".join(words)
