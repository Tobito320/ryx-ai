"""
Ryx AI - Tool Executor
Executes tools with permission checking and result tracking.
"""

import ast
import asyncio
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import aiofiles

    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    import tomllib

    TOMLLIB_AVAILABLE = True
except ImportError:
    TOMLLIB_AVAILABLE = False

from ryx.core.permission_manager import (
    PermissionDeniedError,
    PermissionLevel,
    require_permission,
)


# =============================================================================
# Exceptions
# =============================================================================


class ToolExecutionError(Exception):
    """Base exception for tool execution errors."""

    pass


class ToolFileNotFoundError(ToolExecutionError):
    """Raised when a file is not found."""

    pass


class ToolTimeoutError(ToolExecutionError):
    """Raised when a tool times out."""

    pass


class ToolPermissionError(ToolExecutionError):
    """Raised when permission is denied."""

    pass


class ToolValidationError(ToolExecutionError):
    """Syntax validation failed."""

    pass


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    output: Any
    error: Optional[str] = None
    latency_ms: Optional[float] = None
    tool_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SearchResult:
    """A search result from web search."""

    title: str
    url: str
    snippet: Optional[str] = None


# =============================================================================
# Tool Executor
# =============================================================================


class ToolExecutor:
    """
    Executes tools with permission checking and result tracking.

    Features:
        - File operations (read, edit, create)
        - Local search (glob patterns)
        - Web search (mock implementation)
        - Application launching
        - Permission integration
        - Syntax validation
        - Backup creation

    Example:
        executor = ToolExecutor()
        result = await executor.read_file("/path/to/file.txt")
    """

    # Timeout constants (in seconds)
    TIMEOUT_FILE = 0.5
    TIMEOUT_LOCAL_SEARCH = 2.0
    TIMEOUT_WEB_SEARCH = 5.0
    TIMEOUT_APP_LAUNCH = 30.0

    def __init__(
        self,
        max_file_size: int = 10 * 1024 * 1024,  # 10 MB
        create_backups: bool = True,
        validate_syntax: bool = True,
    ):
        """
        Initialize the ToolExecutor.

        Args:
            max_file_size: Maximum file size to read (bytes)
            create_backups: Create backups before editing
            validate_syntax: Validate syntax before writing
        """
        self.max_file_size = max_file_size
        self.create_backups = create_backups
        self.validate_syntax = validate_syntax

    # =========================================================================
    # File Reading (Level 1 - READ)
    # =========================================================================

    @require_permission(PermissionLevel.READ, description="Read file contents")
    async def read_file(self, path: str) -> ToolResult:
        """
        Read the contents of a file.

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
                if AIOFILES_AVAILABLE:
                    async with aiofiles.open(
                        file_path, mode="r", encoding="utf-8"
                    ) as f:
                        content = await f.read()
                else:
                    # Fallback to sync read
                    content = file_path.read_text(encoding="utf-8")

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

    # =========================================================================
    # Local Search (Level 1 - READ)
    # =========================================================================

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

    # =========================================================================
    # Web Search (Level 1 - READ, mock implementation)
    # =========================================================================

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

    # =========================================================================
    # File Editing (Level 2 - MODIFY)
    # =========================================================================

    @require_permission(PermissionLevel.MODIFY, description="Edit file contents")
    async def edit_file(
        self,
        path: str,
        content: str,
        create_backup: Optional[bool] = None,
    ) -> ToolResult:
        """
        Edit a file's contents.

        Args:
            path: Path to the file to edit
            content: New file content
            create_backup: Override backup setting

        Returns:
            ToolResult with success status
        """
        start_time = asyncio.get_event_loop().time()
        should_backup = (
            create_backup if create_backup is not None else self.create_backups
        )

        try:
            file_path = Path(path).expanduser().resolve()

            # Check if file exists
            if not file_path.exists():
                raise ToolFileNotFoundError(f"File not found: {path}")

            # Validate syntax if enabled
            if self.validate_syntax:
                self._validate_syntax(file_path.suffix, content)

            # Create backup
            backup_path = None
            if should_backup:
                backup_path = await self._create_backup(file_path)

            # Write with timeout
            async with asyncio.timeout(self.TIMEOUT_FILE):
                if AIOFILES_AVAILABLE:
                    async with aiofiles.open(
                        file_path, mode="w", encoding="utf-8"
                    ) as f:
                        await f.write(content)
                else:
                    file_path.write_text(content, encoding="utf-8")

            latency = (asyncio.get_event_loop().time() - start_time) * 1000

            return ToolResult(
                success=True,
                output=f"File edited: {path}"
                + (f" (backup: {backup_path})" if backup_path else ""),
                latency_ms=latency,
                tool_name="edit_file",
            )

        except PermissionDeniedError:
            raise ToolPermissionError(f"Permission denied: {path}")
        except ToolExecutionError:
            raise
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                tool_name="edit_file",
            )

    # =========================================================================
    # File Creation (Level 2 - MODIFY)
    # =========================================================================

    @require_permission(PermissionLevel.MODIFY, description="Create new file")
    async def create_file(
        self,
        path: str,
        content: str,
        overwrite: bool = False,
    ) -> ToolResult:
        """
        Create a new file.

        Args:
            path: Path to the file to create
            content: File content
            overwrite: Allow overwriting existing file

        Returns:
            ToolResult with success status
        """
        start_time = asyncio.get_event_loop().time()

        try:
            file_path = Path(path).expanduser().resolve()

            # Check if file exists
            if file_path.exists() and not overwrite:
                raise ToolExecutionError(f"File already exists: {path}")

            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Validate syntax if enabled
            if self.validate_syntax:
                self._validate_syntax(file_path.suffix, content)

            # Write with timeout
            async with asyncio.timeout(self.TIMEOUT_FILE):
                if AIOFILES_AVAILABLE:
                    async with aiofiles.open(
                        file_path, mode="w", encoding="utf-8"
                    ) as f:
                        await f.write(content)
                else:
                    file_path.write_text(content, encoding="utf-8")

            latency = (asyncio.get_event_loop().time() - start_time) * 1000

            return ToolResult(
                success=True,
                output=f"File created: {path}",
                latency_ms=latency,
                tool_name="create_file",
            )

        except PermissionDeniedError:
            raise ToolPermissionError(f"Permission denied: {path}")
        except ToolExecutionError:
            raise
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                tool_name="create_file",
            )

    # =========================================================================
    # Application Launch (Level 3 - DANGEROUS)
    # =========================================================================

    @require_permission(PermissionLevel.DANGEROUS, description="Launch application")
    async def launch_app(
        self,
        app_name: str,
        args: Optional[List[str]] = None,
        timeout: Optional[float] = None,
    ) -> ToolResult:
        """
        Launch an application.

        Args:
            app_name: Name or path of application to launch
            args: Command line arguments
            timeout: Execution timeout (default: 30s)

        Returns:
            ToolResult with stdout/stderr output
        """
        start_time = asyncio.get_event_loop().time()
        timeout = timeout or self.TIMEOUT_APP_LAUNCH

        try:
            cmd = [app_name] + (args or [])

            # Run with timeout
            async with asyncio.timeout(timeout):
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

            latency = (asyncio.get_event_loop().time() - start_time) * 1000

            output = {
                "returncode": process.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }

            return ToolResult(
                success=process.returncode == 0,
                output=output,
                error=stderr.decode() if process.returncode != 0 else None,
                latency_ms=latency,
                tool_name="launch_app",
            )

        except asyncio.TimeoutError:
            raise ToolTimeoutError(f"Application timed out: {app_name}")
        except PermissionDeniedError:
            raise ToolPermissionError(f"Permission denied: {app_name}")
        except FileNotFoundError:
            raise ToolExecutionError(f"Application not found: {app_name}")
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                tool_name="launch_app",
            )

    # =========================================================================
    # Validation Helpers
    # =========================================================================

    def _validate_syntax(self, extension: str, content: str) -> None:
        """
        Validate syntax based on file extension.

        Args:
            extension: File extension (e.g., ".py")
            content: File content to validate

        Raises:
            ToolValidationError: If syntax is invalid
        """
        validators = {
            ".py": self._validate_python,
            ".json": self._validate_json,
            ".yaml": self._validate_yaml,
            ".yml": self._validate_yaml,
            ".toml": self._validate_toml,
        }

        validator = validators.get(extension.lower())
        if validator:
            validator(content)

    def _validate_python(self, content: str) -> None:
        """Validate Python syntax."""
        try:
            ast.parse(content)
        except SyntaxError as e:
            raise ToolValidationError(f"Python syntax error: {e}")

    def _validate_json(self, content: str) -> None:
        """Validate JSON syntax."""
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            raise ToolValidationError(f"JSON syntax error: {e}")

    def _validate_yaml(self, content: str) -> None:
        """Validate YAML syntax."""
        if not YAML_AVAILABLE:
            return  # Skip if yaml not installed
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ToolValidationError(f"YAML syntax error: {e}")

    def _validate_toml(self, content: str) -> None:
        """Validate TOML syntax."""
        if not TOMLLIB_AVAILABLE:
            return  # Skip if tomllib not available
        try:
            tomllib.loads(content)
        except Exception as e:
            raise ToolValidationError(f"TOML syntax error: {e}")

    async def _create_backup(self, file_path: Path) -> Path:
        """
        Create a backup of a file.

        Args:
            file_path: Path to file to backup

        Returns:
            Path to backup file
        """
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")

        # Find unique backup name
        counter = 1
        while backup_path.exists():
            backup_path = file_path.with_suffix(f"{file_path.suffix}.bak.{counter}")
            counter += 1

        # Copy file to backup
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            shutil.copy2,
            str(file_path),
            str(backup_path),
        )

        return backup_path
