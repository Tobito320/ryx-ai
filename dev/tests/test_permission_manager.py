"""
Tests for Permission Manager module.
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile

from ryx_core.permissions import (
    PermissionLevel,
    PermissionDenied as PermissionDeniedError,
    requires_safe,
    requires_modify,
    requires_destroy,
)
from core.permissions import PermissionManager
# Note: Permission decorators are in ryx_core.permissions, PermissionManager in core.permissions


@pytest.fixture
def manager():
    """Create a non-interactive permission manager."""
    return PermissionManager(interactive=False)


@pytest.fixture
def temp_audit_log(tmp_path):
    """Create a manager with temp audit log."""
    manager = PermissionManager(interactive=False)
    manager.AUDIT_LOG_PATH = tmp_path / "audit.log"
    return manager, tmp_path / "audit.log"


class TestPermissionLevels:
    """Tests for permission level checks."""
    
    @pytest.mark.asyncio
    async def test_read_auto_approved(self, manager):
        """Test that READ operations are auto-approved."""
        result = await manager.check_permission(
            PermissionLevel.READ, "read_file", "/path/to/file"
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_modify_denied_non_interactive(self, manager):
        """Test that MODIFY is denied in non-interactive mode."""
        result = await manager.check_permission(
            PermissionLevel.MODIFY, "edit_file", "/path/to/file"
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_dangerous_denied_non_interactive(self, manager):
        """Test that DANGEROUS is denied in non-interactive mode."""
        result = await manager.check_permission(
            PermissionLevel.DANGEROUS, "delete_file", "/path/to/file"
        )
        assert result is False
    
    def test_permission_level_ordering(self):
        """Test permission levels are ordered correctly."""
        assert PermissionLevel.READ < PermissionLevel.MODIFY
        assert PermissionLevel.MODIFY < PermissionLevel.DANGEROUS


class TestCaching:
    """Tests for permission caching."""
    
    @pytest.mark.asyncio
    async def test_permission_cached(self, manager):
        """Test that permissions are cached."""
        # First call
        await manager.check_permission(PermissionLevel.READ, "read", "/test")
        
        # Should be in cache
        assert (PermissionLevel.READ, "read") in manager._cache
    
    def test_clear_cache(self, manager):
        """Test cache clearing."""
        manager._cache[(PermissionLevel.READ, "test")] = (True, datetime.now())
        manager.clear_cache()
        assert len(manager._cache) == 0
    
    def test_cache_stats(self, manager):
        """Test cache statistics."""
        manager._cache[(PermissionLevel.READ, "test")] = (True, datetime.now())
        
        stats = manager.get_cache_stats()
        
        assert "total" in stats
        assert "valid" in stats
        assert "expired" in stats
        assert stats["total"] >= 1


class TestAuditLogging:
    """Tests for audit logging."""
    
    @pytest.mark.asyncio
    async def test_audit_log_created(self, temp_audit_log):
        """Test that audit log is created."""
        manager, log_path = temp_audit_log
        await manager.check_permission(PermissionLevel.READ, "read", "/test")
        
        assert log_path.exists()
        content = log_path.read_text()
        assert "read" in content
        assert "GRANTED" in content
    
    @pytest.mark.asyncio
    async def test_audit_log_format(self, temp_audit_log):
        """Test audit log format."""
        manager, log_path = temp_audit_log
        await manager.check_permission(PermissionLevel.READ, "read_file", "/path/test")
        
        content = log_path.read_text()
        # Should contain timestamp, level, operation, target, status
        assert "[READ]" in content
        assert "read_file" in content
        assert "/path/test" in content


class TestDecorator:
    """Tests for permission decorator."""
    
    @pytest.mark.asyncio
    async def test_decorated_function_allowed(self):
        """Test decorated function with allowed permission."""
        manager = PermissionManager(interactive=False, auto_approve_read=True)
        set_permission_manager(manager)
        
        @require_permission(PermissionLevel.READ)
        async def test_read(path: str) -> str:
            return "content"
        
        result = await test_read("/test/path")
        assert result == "content"
    
    @pytest.mark.asyncio
    async def test_decorated_function_denied(self):
        """Test decorated function with denied permission."""
        manager = PermissionManager(interactive=False)
        set_permission_manager(manager)
        
        @require_permission(PermissionLevel.DANGEROUS)
        async def test_dangerous(path: str) -> str:
            return "executed"
        
        with pytest.raises(PermissionDeniedError):
            await test_dangerous("/test/path")


class TestConfiguration:
    """Tests for manager configuration."""
    
    def test_default_interactive_mode(self):
        """Test default interactive mode."""
        manager = PermissionManager()
        assert manager.interactive is True
    
    def test_disable_auto_approve_read(self):
        """Test disabling auto-approve for READ."""
        manager = PermissionManager(auto_approve_read=False, interactive=False)
        # READ should not be auto-approved
        assert manager.auto_approve_read is False
