"""
RYX Core - Permission Decorators and Context

Provides Level 1-2-3 permission system with decorators:
- Level 1 (SAFE): Read-only operations, auto-approved
- Level 2 (MODIFY): Write operations, may require confirmation
- Level 3 (DESTROY): Destructive operations, always requires confirmation
"""

from contextvars import ContextVar
from enum import IntEnum
from functools import wraps
from typing import Callable, Optional, Any, Dict, TypeVar, ParamSpec
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


class PermissionLevel(IntEnum):
    """Permission levels for operations (1-3 system)"""
    SAFE = 1      # Level 1: Read-only, auto-approved
    MODIFY = 2    # Level 2: Write operations
    DESTROY = 3   # Level 3: Destructive, always confirm
    BLOCKED = 99  # Completely blocked operations


@dataclass
class PermissionContext:
    """Context for permission checking"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    safety_mode: str = "normal"  # 'strict', 'normal', 'loose'
    confirmed: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def requires_confirmation(self, level: PermissionLevel) -> bool:
        """Check if this context requires confirmation for given level"""
        if self.safety_mode == "strict":
            return level >= PermissionLevel.MODIFY
        elif self.safety_mode == "loose":
            return level >= PermissionLevel.DESTROY
        else:  # normal
            return level >= PermissionLevel.DESTROY


# Thread-safe context storage using contextvars
_permission_context_var: ContextVar[Optional[PermissionContext]] = ContextVar(
    'permission_context', default=None
)


def get_permission_context() -> PermissionContext:
    """Get the current permission context (thread-safe)"""
    ctx = _permission_context_var.get()
    if ctx is None:
        ctx = PermissionContext()
        _permission_context_var.set(ctx)
    return ctx


def set_permission_context(context: PermissionContext) -> None:
    """Set the current permission context (thread-safe)"""
    _permission_context_var.set(context)


class PermissionDenied(Exception):
    """Raised when permission is denied for an operation"""
    def __init__(self, level: PermissionLevel, reason: str):
        self.level = level
        self.reason = reason
        super().__init__(f"Permission denied (Level {level.value}): {reason}")


class ConfirmationRequired(Exception):
    """Raised when user confirmation is required"""
    def __init__(self, level: PermissionLevel, operation: str, details: str = ""):
        self.level = level
        self.operation = operation
        self.details = details
        super().__init__(
            f"Confirmation required for Level {level.value} operation: {operation}"
        )


def check_permission(
    level: PermissionLevel,
    operation: str,
    context: Optional[PermissionContext] = None,
    auto_confirm: bool = False,
) -> bool:
    """
    Check if an operation is permitted
    
    Args:
        level: Required permission level
        operation: Description of the operation
        context: Permission context (uses global if not provided)
        auto_confirm: If True, auto-confirm if possible
        
    Returns:
        True if permitted
        
    Raises:
        PermissionDenied: If level is BLOCKED
        ConfirmationRequired: If confirmation needed and not confirmed
    """
    ctx = context or get_permission_context()
    
    if level == PermissionLevel.BLOCKED:
        raise PermissionDenied(level, f"Operation blocked: {operation}")
    
    if ctx.requires_confirmation(level) and not ctx.confirmed and not auto_confirm:
        raise ConfirmationRequired(level, operation)
    
    logger.debug(f"Permission granted for Level {level.value} operation: {operation}")
    return True


def permission_level(level: PermissionLevel) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to mark a function with a required permission level
    
    Usage:
        @permission_level(PermissionLevel.MODIFY)
        def edit_file(path: str, content: str):
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            check_permission(level, func.__name__)
            return func(*args, **kwargs)
        
        # Store metadata on the function
        wrapper._permission_level = level  # type: ignore
        wrapper._permission_decorated = True  # type: ignore
        return wrapper
    return decorator


def requires_safe(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator for Level 1 (SAFE) operations
    
    These are read-only operations that are always auto-approved.
    
    Usage:
        @requires_safe
        def read_file(path: str) -> str:
            ...
    """
    return permission_level(PermissionLevel.SAFE)(func)


def requires_modify(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator for Level 2 (MODIFY) operations
    
    These are write operations that may require confirmation in strict mode.
    
    Usage:
        @requires_modify
        def write_file(path: str, content: str):
            ...
    """
    return permission_level(PermissionLevel.MODIFY)(func)


def requires_destroy(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator for Level 3 (DESTROY) operations
    
    These are destructive operations that always require confirmation.
    
    Usage:
        @requires_destroy
        def delete_file(path: str):
            ...
    """
    return permission_level(PermissionLevel.DESTROY)(func)


def get_function_permission_level(func: Callable) -> Optional[PermissionLevel]:
    """Get the permission level of a decorated function"""
    return getattr(func, '_permission_level', None)


def is_permission_decorated(func: Callable) -> bool:
    """Check if a function has permission decorators"""
    return getattr(func, '_permission_decorated', False)
