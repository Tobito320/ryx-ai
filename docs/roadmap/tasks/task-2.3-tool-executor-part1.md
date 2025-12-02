# Task 2.3: Tool Executor - Part 1 (Read Operations)

**Time:** 45 min | **Priority:** HIGH | **Agent:** Claude Opus

## Objective

Implement the first part of the `ToolExecutor` class with read-only operations: `read_file()`, `search_local()`, and `search_web()`. Each method should have proper permission decorators, timeouts, and async implementation.

## Output File(s)

- `ryx/core/tool_executor.py`
- `tests/test_tool_executor.py` (partial)

## Dependencies

- Task 2.2: `PermissionManager` with `@require_permission` decorator

## Requirements

### Methods to Implement

1. `read_file(path: str) -> str`
   - Read file contents
   - Permission: Level 1 (READ)
   - Timeout: 0.5 seconds for files
   - Support text files only
   - Return file contents as string

2. `search_local(pattern: str, directory: str = ".") -> List[str]`
   - Search for files matching pattern
   - Permission: Level 1 (READ)
   - Use `glob` or `rglob` for searching
   - Return list of matching file paths

3. `search_web(query: str, max_results: int = 5) -> List[Dict]`
   - Search the web (mock implementation for now)
   - Permission: Level 1 (READ)
   - Return list of search results with title, url, snippet
   - Timeout: 5 seconds

### Timeouts

| Operation | Timeout |
|-----------|---------|
| File operations | 0.5s |
| Local search | 2s |
| Web search | 5s |

### Error Handling

```python
class ToolExecutionError(Exception):
    """Base exception for tool execution errors."""
    pass

class FileNotFoundError(ToolExecutionError):
    """File not found."""
    pass

class TimeoutError(ToolExecutionError):
    """Operation timed out."""
    pass

class PermissionError(ToolExecutionError):
    """Permission denied for operation."""
    pass
```

## Code Template

```python
"""
Ryx AI - Tool Executor
Executes tools with permission checks and timeouts
"""

import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from ryx.core.permission_manager import (
    PermissionLevel,
    require_permission,
    PermissionDeniedError,
)


# =============================================================================
# Exceptions
# =============================================================================

class ToolExecutionError(Exception):
    """Base exception for tool execution errors."""
    pass


class ToolFileNotFoundError(ToolExecutionError):
    """File not found."""
    pass


class ToolTimeoutError(ToolExecutionError):
    """Operation timed out."""
    pass


class ToolPermissionError(ToolExecutionError):
    """Permission denied for operation."""
    pass


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    latency_ms: float = 0.0
    tool_name: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class SearchResult:
    """Result from web search."""
    title: str
    url: str
    snippet: str


# =============================================================================
# Tool Executor
# =============================================================================

class ToolExecutor:
    """
    Executes Ryx AI tools with permission checks and timeouts.
    
    Part 1: Read Operations
        - read_file: Read file contents
        - search_local: Search local filesystem
        - search_web: Search the web
    
    Example:
        executor = ToolExecutor()
        content = await executor.read_file("/path/to/file.txt")
        files = await executor.search_local("*.py", "/home/user/projects")
    """
    
    # Timeout configurations (seconds)
    TIMEOUT_FILE = 0.5
    TIMEOUT_LOCAL_SEARCH = 2.0
    TIMEOUT_WEB_SEARCH = 5.0
    
    def __init__(self, max_file_size: int = 10 * 1024 * 1024):
        """
        Initialize the Tool Executor.
        
        Args:
            max_file_size: Maximum file size to read (default: 10MB)
        """
        self.max_file_size = max_file_size
    
    @require_permission(PermissionLevel.READ, description="Read file contents")
    async def read_file(self, path: str) -> ToolResult:
        """
        Read contents of a file.
        
        Args:
            path: Path to the file to read
            
        Returns:
            ToolResult with file contents
            
        Raises:
            ToolFileNotFoundError: If file doesn't exist
            ToolTimeoutError: If operation times out
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            file_path = Path(path).expanduser().resolve()
            
            # Check if file exists
            if not file_path.exists():
                raise ToolFileNotFoundError(f"File not found: {path}")
            
            # Check if it's a file
            if not file_path.is_file():
                raise ToolExecutionError(f"Not a file: {path}")
            
            # Check file size
            if file_path.stat().st_size > self.max_file_size:
                raise ToolExecutionError(f"File too large: {path}")
            
            # Read with timeout
            async with asyncio.timeout(self.TIMEOUT_FILE):
                async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                    content = await f.read()
            
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return ToolResult(
                success=True,
                output=content,
                latency_ms=latency,
                tool_name="read_file",
            )
            
        except asyncio.TimeoutError:
            raise ToolTimeoutError(f"Timeout reading file: {path}")
        except PermissionDeniedError:
            raise ToolPermissionError(f"Permission denied: {path}")
        except ToolExecutionError:
            raise
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                tool_name="read_file",
            )
    
    @require_permission(PermissionLevel.READ, description="Search local files")
    async def search_local(
        self,
        pattern: str,
        directory: str = ".",
        recursive: bool = True,
        max_results: int = 100,
    ) -> ToolResult:
        """
        Search for files matching a pattern.
        
        Args:
            pattern: Glob pattern to match (e.g., "*.py", "**/*.md")
            directory: Directory to search in
            recursive: Search recursively
            max_results: Maximum number of results
            
        Returns:
            ToolResult with list of matching file paths
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            dir_path = Path(directory).expanduser().resolve()
            
            if not dir_path.exists():
                raise ToolFileNotFoundError(f"Directory not found: {directory}")
            
            if not dir_path.is_dir():
                raise ToolExecutionError(f"Not a directory: {directory}")
            
            # Search with timeout
            async with asyncio.timeout(self.TIMEOUT_LOCAL_SEARCH):
                # Run glob in executor to not block
                loop = asyncio.get_event_loop()
                
                def do_search():
                    if recursive:
                        matches = list(dir_path.rglob(pattern))[:max_results]
                    else:
                        matches = list(dir_path.glob(pattern))[:max_results]
                    return [str(m) for m in matches]
                
                results = await loop.run_in_executor(None, do_search)
            
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return ToolResult(
                success=True,
                output=results,
                latency_ms=latency,
                tool_name="search_local",
            )
            
        except asyncio.TimeoutError:
            raise ToolTimeoutError(f"Timeout searching: {directory}")
        except PermissionDeniedError:
            raise ToolPermissionError(f"Permission denied: {directory}")
        except ToolExecutionError:
            raise
        except Exception as e:
            return ToolResult(
                success=False,
                output=[],
                error=str(e),
                tool_name="search_local",
            )
    
    @require_permission(PermissionLevel.READ, description="Search the web")
    async def search_web(
        self,
        query: str,
        max_results: int = 5,
    ) -> ToolResult:
        """
        Search the web for information.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            ToolResult with list of SearchResult objects
            
        Note:
            This is a mock implementation. Full implementation
            would integrate with a search API.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with asyncio.timeout(self.TIMEOUT_WEB_SEARCH):
                # Mock implementation - would integrate with DuckDuckGo/Google API
                # For now, return empty results
                results: List[SearchResult] = []
                
                # TODO: Implement actual web search
                # Example integration:
                # async with httpx.AsyncClient() as client:
                #     response = await client.get(
                #         "https://api.duckduckgo.com/",
                #         params={"q": query, "format": "json"}
                #     )
                #     data = response.json()
                #     results = [SearchResult(...) for item in data["results"]]
            
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return ToolResult(
                success=True,
                output=results,
                latency_ms=latency,
                tool_name="search_web",
            )
            
        except asyncio.TimeoutError:
            raise ToolTimeoutError(f"Timeout searching web: {query}")
        except PermissionDeniedError:
            raise ToolPermissionError("Permission denied for web search")
        except Exception as e:
            return ToolResult(
                success=False,
                output=[],
                error=str(e),
                tool_name="search_web",
            )
```

## Unit Tests

Create tests in `tests/test_tool_executor.py`:

```python
import pytest
import tempfile
from pathlib import Path

from ryx.core.tool_executor import (
    ToolExecutor,
    ToolResult,
    ToolFileNotFoundError,
    ToolTimeoutError,
)
from ryx.core.permission_manager import (
    PermissionManager,
    set_permission_manager,
)


@pytest.fixture
def executor():
    # Set up permission manager to auto-approve
    manager = PermissionManager(auto_approve_read=True, interactive=False)
    set_permission_manager(manager)
    return ToolExecutor()


@pytest.fixture
def temp_file(tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("Hello, World!")
    return file_path


class TestReadFile:
    @pytest.mark.asyncio
    async def test_read_existing_file(self, executor, temp_file):
        result = await executor.read_file(str(temp_file))
        assert result.success is True
        assert result.output == "Hello, World!"
        assert result.tool_name == "read_file"
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, executor):
        with pytest.raises(ToolFileNotFoundError):
            await executor.read_file("/nonexistent/path.txt")
    
    @pytest.mark.asyncio
    async def test_read_file_latency_recorded(self, executor, temp_file):
        result = await executor.read_file(str(temp_file))
        assert result.latency_ms > 0


class TestSearchLocal:
    @pytest.mark.asyncio
    async def test_search_pattern(self, executor, tmp_path):
        # Create test files
        (tmp_path / "test1.py").write_text("# test")
        (tmp_path / "test2.py").write_text("# test")
        (tmp_path / "readme.md").write_text("# readme")
        
        result = await executor.search_local("*.py", str(tmp_path))
        assert result.success is True
        assert len(result.output) == 2
    
    @pytest.mark.asyncio
    async def test_search_nonexistent_directory(self, executor):
        with pytest.raises(ToolFileNotFoundError):
            await executor.search_local("*.py", "/nonexistent/dir")


class TestSearchWeb:
    @pytest.mark.asyncio
    async def test_search_web_mock(self, executor):
        result = await executor.search_web("python tutorial")
        assert result.success is True
        assert isinstance(result.output, list)
        assert result.tool_name == "search_web"
```

## Acceptance Criteria

- [ ] `ToolExecutionError` base exception class created
- [ ] `ToolFileNotFoundError`, `ToolTimeoutError`, `ToolPermissionError` created
- [ ] `ToolResult` dataclass with success, output, error, latency_ms, tool_name
- [ ] `SearchResult` dataclass with title, url, snippet
- [ ] `read_file()` method with READ permission decorator
- [ ] `read_file()` has 0.5s timeout
- [ ] `read_file()` checks file existence and size
- [ ] `search_local()` method with glob pattern matching
- [ ] `search_local()` has 2s timeout
- [ ] `search_local()` supports recursive search
- [ ] `search_web()` method (mock implementation)
- [ ] `search_web()` has 5s timeout
- [ ] All methods return `ToolResult` objects
- [ ] Latency tracked for all operations
- [ ] Unit tests passing

## Notes

- Use `aiofiles` for async file operations
- Use `asyncio.timeout()` for Python 3.11+ timeouts
- File size limit should be configurable
- Web search is a mock for now - will be implemented later
- All operations should be async
- Permission decorators from Task 2.2 must be used
