"""
Ryx AI - Permission Manager
Handles permission checking for system operations.
"""

import asyncio
import functools
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple


class PermissionLevel(IntEnum):
    """Permission levels for operations."""

    READ = 1  # Safe operations like viewing files
    MODIFY = 2  # Operations that change files
    DANGEROUS = 3  # System-level or destructive operations


@dataclass
class PermissionRequest:
    """A permission request."""

    level: PermissionLevel
    operation: str
    target: str
    description: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class PermissionDeniedError(Exception):
    """Raised when permission is denied."""

    pass


class PermissionManager:
    """
    Manages permission checking for Ryx AI operations.

    Features:
        - Three-tier permission levels (READ, MODIFY, DANGEROUS)
        - Auto-approve safe operations (READ)
        - Interactive prompts for risky operations
        - Audit logging to file
        - Permission caching

    Example:
        manager = PermissionManager()
        if await manager.check_permission(PermissionLevel.MODIFY, "edit_file", "/path"):
            # Proceed with operation
            pass
    """

    # Cache TTL for permission checks
    CACHE_TTL = timedelta(hours=1)

    # Audit log path
    AUDIT_LOG_PATH = Path.home() / ".config" / "ryx" / "audit.log"

    def __init__(
        self,
        interactive: bool = True,
        auto_approve_read: bool = True,
    ):
        """
        Initialize the PermissionManager.

        Args:
            interactive: Whether to prompt for permissions interactively
            auto_approve_read: Auto-approve READ level operations
        """
        self.interactive = interactive
        self.auto_approve_read = auto_approve_read

        # Permission cache: (level, operation) -> (granted, timestamp)
        self._cache: Dict[Tuple[PermissionLevel, str], Tuple[bool, datetime]] = {}

        # Ensure config directory exists
        self.AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    async def check_permission(
        self,
        level: PermissionLevel,
        operation: str,
        target: str,
        description: Optional[str] = None,
    ) -> bool:
        """
        Check if an operation is permitted.

        Args:
            level: Required permission level
            operation: Operation name (e.g., "read_file", "edit_file")
            target: Target of operation (e.g., file path)
            description: Optional human-readable description

        Returns:
            True if operation is permitted
        """
        cache_key = (level, operation)

        # Check cache
        if cache_key in self._cache:
            granted, cached_at = self._cache[cache_key]
            if datetime.now() - cached_at < self.CACHE_TTL:
                self.log_audit(operation, target, level, granted, cached=True)
                return granted

        # Level 1 (READ): Auto-approve
        if level == PermissionLevel.READ and self.auto_approve_read:
            self._cache[cache_key] = (True, datetime.now())
            self.log_audit(operation, target, level, True)
            return True

        # Level 2 & 3: Request permission
        if self.interactive:
            granted = await self.request_permission(
                operation, target, level, description
            )
        else:
            granted = False

        # Cache result
        self._cache[cache_key] = (granted, datetime.now())
        self.log_audit(operation, target, level, granted)

        return granted

    async def request_permission(
        self,
        operation: str,
        target: str,
        level: PermissionLevel,
        description: Optional[str] = None,
    ) -> bool:
        """
        Request user permission interactively.

        Args:
            operation: Operation name
            target: Target of operation
            level: Permission level
            description: Optional description

        Returns:
            True if user grants permission
        """
        # Build prompt
        level_names = {
            PermissionLevel.READ: "READ",
            PermissionLevel.MODIFY: "MODIFY",
            PermissionLevel.DANGEROUS: "⚠️  DANGEROUS",
        }

        print(f"\n[{level_names[level]}] Permission Request")
        print(f"Operation: {operation}")
        print(f"Target: {target}")
        if description:
            print(f"Description: {description}")

        if level == PermissionLevel.DANGEROUS:
            print("\n⚠️  WARNING: This operation may cause data loss or system changes!")
            prompt = "Type 'yes' to confirm: "
            expected = "yes"
        else:
            prompt = "Allow? [y/N]: "
            expected = "y"

        try:
            # Async input with timeout
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, input, prompt),
                timeout=30.0,
            )
            return response.strip().lower() == expected
        except asyncio.TimeoutError:
            print("\nPermission request timed out.")
            return False

    def log_audit(
        self,
        operation: str,
        target: str,
        level: PermissionLevel,
        granted: bool,
        cached: bool = False,
    ) -> None:
        """
        Log permission check to audit file.

        Args:
            operation: Operation name
            target: Target of operation
            level: Permission level
            granted: Whether permission was granted
            cached: Whether result was from cache
        """
        timestamp = datetime.now().isoformat()
        status = "GRANTED" if granted else "DENIED"
        cache_note = " (cached)" if cached else ""

        log_line = f"[{timestamp}] [{level.name}] {operation}: {target} -> {status}{cache_note}\n"

        try:
            with open(self.AUDIT_LOG_PATH, "a") as f:
                f.write(log_line)
        except Exception:
            pass  # Don't fail on logging errors

    def clear_cache(self) -> None:
        """Clear the permission cache."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        now = datetime.now()
        valid = sum(
            1 for _, (_, ts) in self._cache.items() if now - ts < self.CACHE_TTL
        )
        return {
            "total": len(self._cache),
            "valid": valid,
            "expired": len(self._cache) - valid,
        }


def require_permission(
    level: PermissionLevel,
    description: Optional[str] = None,
) -> Callable:
    """
    Decorator to require permission for a function.

    Args:
        level: Required permission level
        description: Operation description for user prompt

    Returns:
        Decorated function that checks permission before execution

    Example:
        @require_permission(PermissionLevel.MODIFY, "Edit file")
        async def edit_file(path: str, content: str):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get the permission manager (assume global or from context)
            manager = _get_permission_manager()

            # Extract target from first argument
            target = str(args[0]) if args else kwargs.get("path", "unknown")

            # Check permission
            granted = await manager.check_permission(
                level=level,
                operation=func.__name__,
                target=target,
                description=description,
            )

            if not granted:
                raise PermissionDeniedError(
                    f"Permission denied for {func.__name__} on {target}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Global permission manager instance
_permission_manager: Optional[PermissionManager] = None


def _get_permission_manager() -> PermissionManager:
    """Get or create the global permission manager."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager


def set_permission_manager(manager: PermissionManager) -> None:
    """Set the global permission manager."""
    global _permission_manager
    _permission_manager = manager
