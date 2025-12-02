"""
Tests for Tool Executor module.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from ryx.core.tool_executor import (
    ToolExecutor,
    ToolResult,
    ToolFileNotFoundError,
    ToolTimeoutError,
    ToolExecutionError,
    ToolValidationError,
)
from ryx.core.permission_manager import (
    PermissionManager,
    PermissionLevel,
    set_permission_manager,
)


@pytest.fixture
def executor():
    """Create a tool executor with auto-approve permissions."""
    manager = PermissionManager(auto_approve_read=True, interactive=False)
    set_permission_manager(manager)
    return ToolExecutor()


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("Hello, World!")
    return file_path


class TestReadFile:
    """Tests for read_file method."""
    
    @pytest.mark.asyncio
    async def test_read_existing_file(self, executor, temp_file):
        """Test reading an existing file."""
        result = await executor.read_file(str(temp_file))
        
        assert result.success is True
        assert result.output == "Hello, World!"
        assert result.tool_name == "read_file"
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, executor):
        """Test reading a non-existent file."""
        with pytest.raises(ToolFileNotFoundError):
            await executor.read_file("/nonexistent/path.txt")
    
    @pytest.mark.asyncio
    async def test_read_file_latency_recorded(self, executor, temp_file):
        """Test that latency is recorded."""
        result = await executor.read_file(str(temp_file))
        
        assert result.latency_ms is not None
        assert result.latency_ms >= 0


class TestSearchLocal:
    """Tests for search_local method."""
    
    @pytest.mark.asyncio
    async def test_search_pattern(self, executor, tmp_path):
        """Test searching with glob patterns."""
        # Create test files
        (tmp_path / "test1.py").write_text("# test")
        (tmp_path / "test2.py").write_text("# test")
        (tmp_path / "readme.md").write_text("# readme")
        
        result = await executor.search_local("*.py", str(tmp_path))
        
        assert result.success is True
        assert len(result.output) == 2
    
    @pytest.mark.asyncio
    async def test_search_nonexistent_directory(self, executor):
        """Test searching in non-existent directory."""
        with pytest.raises(ToolFileNotFoundError):
            await executor.search_local("*.py", "/nonexistent/dir")
    
    @pytest.mark.asyncio
    async def test_search_max_results(self, executor, tmp_path):
        """Test max_results limit."""
        # Create many files
        for i in range(10):
            (tmp_path / f"test{i}.py").write_text("# test")
        
        result = await executor.search_local("*.py", str(tmp_path), max_results=5)
        
        assert len(result.output) <= 5


class TestSearchWeb:
    """Tests for search_web method (mock)."""
    
    @pytest.mark.asyncio
    async def test_search_web_mock(self, executor):
        """Test web search mock implementation."""
        result = await executor.search_web("python tutorial")
        
        assert result.success is True
        assert isinstance(result.output, list)
        assert result.tool_name == "search_web"


class TestEditFile:
    """Tests for edit_file method."""
    
    @pytest.mark.asyncio
    async def test_edit_existing_file(self, executor, temp_file):
        """Test editing an existing file."""
        # Set permission manager to approve MODIFY
        manager = PermissionManager(interactive=False)
        manager._cache[(PermissionLevel.MODIFY, "edit_file")] = (True, datetime.now())
        set_permission_manager(manager)
        
        result = await executor.edit_file(str(temp_file), "New content")
        
        assert result.success is True
        assert temp_file.read_text() == "New content"
    
    @pytest.mark.asyncio
    async def test_edit_creates_backup(self, executor, temp_file):
        """Test that editing creates backup."""
        manager = PermissionManager(interactive=False)
        manager._cache[(PermissionLevel.MODIFY, "edit_file")] = (True, datetime.now())
        set_permission_manager(manager)
        
        original_content = temp_file.read_text()
        await executor.edit_file(str(temp_file), "New content")
        
        backup_path = temp_file.with_suffix(".txt.bak")
        assert backup_path.exists()
        assert backup_path.read_text() == original_content


class TestCreateFile:
    """Tests for create_file method."""
    
    @pytest.mark.asyncio
    async def test_create_new_file(self, executor, tmp_path):
        """Test creating a new file."""
        manager = PermissionManager(interactive=False)
        manager._cache[(PermissionLevel.MODIFY, "create_file")] = (True, datetime.now())
        set_permission_manager(manager)
        
        new_file = tmp_path / "new.txt"
        result = await executor.create_file(str(new_file), "Hello")
        
        assert result.success is True
        assert new_file.exists()
        assert new_file.read_text() == "Hello"
    
    @pytest.mark.asyncio
    async def test_create_fails_if_exists(self, executor, temp_file):
        """Test that creating fails if file exists."""
        manager = PermissionManager(interactive=False)
        manager._cache[(PermissionLevel.MODIFY, "create_file")] = (True, datetime.now())
        set_permission_manager(manager)
        
        with pytest.raises(ToolExecutionError):
            await executor.create_file(str(temp_file), "New content")


class TestSyntaxValidation:
    """Tests for syntax validation."""
    
    def test_validate_python_syntax_valid(self, executor):
        """Test valid Python syntax."""
        # Should not raise
        executor._validate_python("def foo():\n    pass")
    
    def test_validate_python_syntax_invalid(self, executor):
        """Test invalid Python syntax."""
        with pytest.raises(ToolValidationError):
            executor._validate_python("def invalid(")
    
    def test_validate_json_syntax_valid(self, executor):
        """Test valid JSON syntax."""
        executor._validate_json('{"key": "value"}')
    
    def test_validate_json_syntax_invalid(self, executor):
        """Test invalid JSON syntax."""
        with pytest.raises(ToolValidationError):
            executor._validate_json('{invalid}')


class TestToolResult:
    """Tests for ToolResult dataclass."""
    
    def test_tool_result_structure(self):
        """Test ToolResult has expected fields."""
        result = ToolResult(
            success=True,
            output="test output",
            latency_ms=10.5,
            tool_name="test_tool",
        )
        
        assert result.success is True
        assert result.output == "test output"
        assert result.latency_ms == 10.5
        assert result.tool_name == "test_tool"
        assert result.error is None
    
    def test_tool_result_with_error(self):
        """Test ToolResult with error."""
        result = ToolResult(
            success=False,
            output=None,
            error="Something went wrong",
            tool_name="test_tool",
        )
        
        assert result.success is False
        assert result.error == "Something went wrong"
