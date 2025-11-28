"""
Ryx AI - Comprehensive Error Handler
Provides robust error handling and recovery mechanisms
"""

import functools
import logging
import traceback
from typing import Callable, Any, Optional, Dict
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Comprehensive error handling with auto-recovery

    Features:
    - Retry logic with exponential backoff
    - Error logging and tracking
    - Graceful degradation
    - User-friendly error messages
    """

    def __init__(self) -> None:
        """Initialize error handler with tracking"""
        self.error_count = {}
        self.last_errors = []
        self.max_error_history = 100

    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Handle an error with logging and tracking

        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred

        Returns:
            Dict with error info
        """
        error_type = type(error).__name__
        error_msg = str(error)

        # Track error count
        if error_type not in self.error_count:
            self.error_count[error_type] = 0
        self.error_count[error_type] += 1

        # Log error
        logger.error(f"{context}: {error_type}: {error_msg}")
        logger.debug(traceback.format_exc())

        # Store in history
        error_info = {
            'type': error_type,
            'message': error_msg,
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'count': self.error_count[error_type]
        }

        self.last_errors.append(error_info)
        if len(self.last_errors) > self.max_error_history:
            self.last_errors.pop(0)

        return error_info

    def get_user_friendly_message(self, error: Exception) -> str:
        """Convert technical error to user-friendly message"""
        error_type = type(error).__name__
        error_msg = str(error)

        # Common error patterns
        if 'Connection' in error_type or 'connection' in error_msg.lower():
            return "❌ Connection error - check if the service is running"

        if '404' in error_msg:
            return "❌ Resource not found (404) - trying auto-fix..."

        if 'Permission' in error_type or 'permission' in error_msg.lower():
            return "❌ Permission denied - check file permissions"

        if 'Database' in error_type or 'database' in error_msg.lower():
            return "❌ Database error - trying auto-repair..."

        if 'Timeout' in error_type or 'timeout' in error_msg.lower():
            return "⏱️  Operation timed out - retrying..."

        if 'Memory' in error_type or 'memory' in error_msg.lower():
            return "💾 Out of memory - freeing resources..."

        # Default
        return f"❌ Error: {error_msg[:100]}"

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            'total_errors': sum(self.error_count.values()),
            'error_types': dict(self.error_count),
            'recent_errors': self.last_errors[-10:] if self.last_errors else []
        }


def retry_on_error(max_retries: int = 3, backoff: list = None, exceptions: tuple = (Exception,)):
    """
    Decorator for automatic retry with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        backoff: List of delays in seconds (default: [1, 2, 4])
        exceptions: Tuple of exceptions to catch

    Usage:
        @retry_on_error(max_retries=3)
        def my_function():
            ...
    """
    if backoff is None:
        backoff = [1, 2, 4]

    def decorator(func: Callable) -> Callable:
        """Decorator implementation for retry logic"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """Wrapper that retries on error with backoff"""
            import time

            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}"
                    )

                    if attempt < max_retries - 1:
                        delay = backoff[min(attempt, len(backoff) - 1)]
                        logger.info(f"Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}")

            # All retries exhausted
            raise last_exception

        return wrapper
    return decorator


def graceful_failure(default_return: Any = None, log_error: bool = True):
    """
    Decorator for graceful failure - returns default value instead of raising

    Args:
        default_return: Value to return on error
        log_error: Whether to log the error

    Usage:
        @graceful_failure(default_return={})
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        """Decorator implementation for graceful failure"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """Wrapper that catches errors and returns default value"""
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"Error in {func.__name__}: {e}")
                    logger.debug(traceback.format_exc())
                return default_return

        return wrapper
    return decorator


def safe_execute(func: Callable, *args, **kwargs) -> tuple[bool, Any]:
    """
    Safely execute a function and return (success, result)

    Args:
        func: Function to execute
        *args, **kwargs: Arguments to pass to function

    Returns:
        Tuple of (success: bool, result: Any)
        - If success: (True, function_result)
        - If error: (False, error_message)
    """
    try:
        result = func(*args, **kwargs)
        return (True, result)
    except Exception as e:
        logger.error(f"Error in {func.__name__}: {e}")
        return (False, str(e))


# Global error handler instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    return _error_handler
