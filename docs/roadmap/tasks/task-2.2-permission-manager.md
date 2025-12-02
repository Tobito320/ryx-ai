# Task 2.2: Permission Manager Implementation

**Time:** 45 min | **Priority:** HIGH | **Agent:** Claude Opus

## Objective

Implement a full `PermissionManager` class with 3 permission levels, a decorator system for protecting operations, audit logging, and permission caching.

## Output File(s)

- `ryx/core/permission_manager.py`
- `tests/test_permission_manager.py`

## Requirements

### Permission Levels

| Level | Name | Behavior | Examples |
|-------|------|----------|----------|
| 1 | READ | Auto-approve | read_file, list_dir, search |
| 2 | MODIFY | Ask user | edit_file, create_file, rename |
| 3 | DANGEROUS | Warn user + confirm | delete_file, run_shell, system_config |

### Core Methods

1. `check_permission(level: PermissionLevel, operation: str, target: str) -> bool`
   - Check if operation is allowed
   - Level 1: Always True
   - Level 2: Prompt user for confirmation
   - Level 3: Show warning, require explicit "yes" confirmation

2. `request_permission(operation: str, target: str, level: PermissionLevel) -> bool`
   - Request user permission interactively
   - Display operation description
   - Handle timeout (30 seconds)

3. `log_audit(operation: str, target: str, level: PermissionLevel, granted: bool) -> None`
   - Log all permission checks to `~/.config/ryx/audit.log`
   - Format: `[timestamp] [level] operation: target -> granted/denied`

### Decorator System

```python
@require_permission(PermissionLevel.READ)
async def read_file(path: str) -> str:
    pass

@require_permission(PermissionLevel.MODIFY, description="Edit configuration file")
async def edit_file(path: str, content: str) -> bool:
    pass

@require_permission(PermissionLevel.DANGEROUS, description="Execute shell command")
async def run_command(command: str) -> str:
    pass
```

### Permission Caching

- Cache granted permissions for 1 hour
- Cache key: `(level, operation_type)`
- Clear cache on explicit reset or restart

## Code Template

```python
"""
Ryx AI - Permission Manager
Role-based permission system with audit logging
"""

import asyncio
import functools
import os
from datetime import datetime, timedelta
from enum import IntEnum
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple, Any
from dataclasses import dataclass


class PermissionLevel(IntEnum):
    """Permission levels for operations."""
    READ = 1       # Auto-approve
    MODIFY = 2     # Ask user
    DANGEROUS = 3  # Warn + confirm


@dataclass
class PermissionRequest:
    """Details of a permission request."""
    operation: str
    target: str
    level: PermissionLevel
    description: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class PermissionDeniedError(Exception):
    """Raised when permission is denied."""
    pass


class PermissionManager:
    """
    Manages operation permissions with audit logging.
    
    Features:
        - Three permission levels (READ, MODIFY, DANGEROUS)
        - Interactive permission requests
        - Audit logging to file
        - Permission caching (1 hour TTL)
    
    Example:
        manager = PermissionManager()
        if await manager.check_permission(PermissionLevel.MODIFY, "edit_file", "/etc/config"):
            # Perform operation
            pass
    """
    
    CACHE_TTL = timedelta(hours=1)
    AUDIT_LOG_PATH = Path.home() / ".config" / "ryx" / "audit.log"
    
    def __init__(self, auto_approve_read: bool = True, interactive: bool = True):
        """
        Initialize the Permission Manager.
        
        Args:
            auto_approve_read: Auto-approve READ level operations
            interactive: Enable interactive prompts for MODIFY/DANGEROUS
        """
        self.auto_approve_read = auto_approve_read
        self.interactive = interactive
        
        # Permission cache: (level, operation) -> (granted, timestamp)
        self._cache: Dict[Tuple[PermissionLevel, str], Tuple[bool, datetime]] = {}
        
        # Ensure audit log directory exists
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
            operation: Operation name (e.g., "edit_file")
            target: Target of operation (e.g., file path)
            description: Optional description for user prompt
            
        Returns:
            True if operation is permitted
        """
        # Check cache
        cache_key = (level, operation)
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
        valid = sum(1 for _, (_, ts) in self._cache.items() if now - ts < self.CACHE_TTL)
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
```

## Unit Tests

Create tests in `tests/test_permission_manager.py`:

```python
import pytest
from unittest.mock import patch, AsyncMock
from pathlib import Path
import tempfile

from ryx.core.permission_manager import (
    PermissionManager,
    PermissionLevel,
    PermissionDeniedError,
    require_permission,
    set_permission_manager,
)


@pytest.fixture
def manager():
    return PermissionManager(interactive=False)


@pytest.fixture
def temp_audit_log(tmp_path):
    log_path = tmp_path / "audit.log"
    manager = PermissionManager(interactive=False)
    manager.AUDIT_LOG_PATH = log_path
    return manager, log_path


class TestPermissionLevels:
    @pytest.mark.asyncio
    async def test_read_auto_approved(self, manager):
        result = await manager.check_permission(
            PermissionLevel.READ, "read_file", "/path/to/file"
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_modify_denied_non_interactive(self, manager):
        result = await manager.check_permission(
            PermissionLevel.MODIFY, "edit_file", "/path/to/file"
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_dangerous_denied_non_interactive(self, manager):
        result = await manager.check_permission(
            PermissionLevel.DANGEROUS, "delete_file", "/path/to/file"
        )
        assert result is False


class TestCaching:
    @pytest.mark.asyncio
    async def test_permission_cached(self, manager):
        # First call
        await manager.check_permission(PermissionLevel.READ, "read", "/test")
        
        # Should be in cache
        assert (PermissionLevel.READ, "read") in manager._cache
    
    def test_clear_cache(self, manager):
        manager._cache[(PermissionLevel.READ, "test")] = (True, None)
        manager.clear_cache()
        assert len(manager._cache) == 0


class TestAuditLogging:
    @pytest.mark.asyncio
    async def test_audit_log_created(self, temp_audit_log):
        manager, log_path = temp_audit_log
        await manager.check_permission(PermissionLevel.READ, "read", "/test")
        
        assert log_path.exists()
        content = log_path.read_text()
        assert "read" in content
        assert "GRANTED" in content


class TestDecorator:
    @pytest.mark.asyncio
    async def test_decorated_function_allowed(self):
        manager = PermissionManager(interactive=False, auto_approve_read=True)
        set_permission_manager(manager)
        
        @require_permission(PermissionLevel.READ)
        async def test_read(path: str) -> str:
            return "content"
        
        result = await test_read("/test/path")
        assert result == "content"
    
    @pytest.mark.asyncio
    async def test_decorated_function_denied(self):
        manager = PermissionManager(interactive=False)
        set_permission_manager(manager)
        
        @require_permission(PermissionLevel.DANGEROUS)
        async def test_dangerous(path: str) -> str:
            return "executed"
        
        with pytest.raises(PermissionDeniedError):
            await test_dangerous("/test/path")
```

## Acceptance Criteria

- [ ] `PermissionLevel` enum with READ (1), MODIFY (2), DANGEROUS (3)
- [ ] `PermissionRequest` dataclass created
- [ ] `PermissionDeniedError` exception class created
- [ ] `check_permission()` method with level-based logic
- [ ] `request_permission()` method with interactive prompts
- [ ] `log_audit()` method writing to `~/.config/ryx/audit.log`
- [ ] Permission caching with 1-hour TTL
- [ ] `@require_permission` decorator working
- [ ] READ operations auto-approved when `auto_approve_read=True`
- [ ] DANGEROUS operations require "yes" confirmation
- [ ] Audit log format: `[timestamp] [level] operation: target -> status`
- [ ] Unit tests passing with >80% coverage

## Notes

- The decorator should work with async functions
- Timeout for user input should be 30 seconds
- Cache should use tuple (level, operation) as key
- Audit log directory should be created if it doesn't exist
- Non-interactive mode should deny MODIFY and DANGEROUS by default
