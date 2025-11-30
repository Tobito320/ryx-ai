# Task 2.4: Tool Executor - Part 2 (Write Operations)

**Time:** 45 min | **Priority:** HIGH | **Agent:** Claude Opus

## Objective

Complete the `ToolExecutor` class with write operations: `edit_file()`, `create_file()`, and `launch_app()`. Each method should have proper permission decorators with descriptions, backup creation for modifications, and syntax validation.

## Output File(s)

- `ryx/core/tool_executor.py` (extend from Task 2.3)
- `tests/test_tool_executor.py` (extend tests)

## Dependencies

- Task 2.2: `PermissionManager` with `@require_permission` decorator
- Task 2.3: `ToolExecutor` with read operations

## Requirements

### Methods to Implement

1. `edit_file(path: str, content: str, create_backup: bool = True) -> ToolResult`
   - Edit existing file contents
   - Permission: Level 2 (MODIFY) with description
   - Create backup before modification (`.bak` extension)
   - Validate syntax by file extension
   - Return success status

2. `create_file(path: str, content: str, overwrite: bool = False) -> ToolResult`
   - Create a new file
   - Permission: Level 2 (MODIFY) with description
   - Fail if file exists and `overwrite=False`
   - Create parent directories if needed
   - Validate syntax by file extension

3. `launch_app(app_name: str, args: List[str] = None) -> ToolResult`
   - Launch an application
   - Permission: Level 3 (DANGEROUS) with description
   - Use `subprocess` for execution
   - Capture stdout/stderr
   - Timeout: 30 seconds

### Backup System

```python
# Before editing file.txt, create file.txt.bak
# If file.txt.bak exists, create file.txt.bak.1, etc.
```

### Syntax Validation

| Extension | Validation |
|-----------|------------|
| .py | `ast.parse()` |
| .json | `json.loads()` |
| .yaml, .yml | `yaml.safe_load()` |
| .toml | `tomllib.loads()` (Python 3.11+) |
| Others | No validation |

### Permission Decorators with Descriptions

```python
@require_permission(
    PermissionLevel.MODIFY,
    description="Edit file: {path}"
)
async def edit_file(self, path: str, content: str) -> ToolResult:
    pass

@require_permission(
    PermissionLevel.MODIFY,
    description="Create file: {path}"
)
async def create_file(self, path: str, content: str) -> ToolResult:
    pass

@require_permission(
    PermissionLevel.DANGEROUS,
    description="Launch application: {app_name}"
)
async def launch_app(self, app_name: str, args: List[str] = None) -> ToolResult:
    pass
```

## Code Template (Extend tool_executor.py)

```python
# Add these imports at the top
import ast
import json
import shutil
import subprocess
import yaml  # PyYAML

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback


# Add these methods to ToolExecutor class

class ToolExecutor:
    # ... (existing code from Task 2.3)
    
    # Timeout configurations
    TIMEOUT_APP_LAUNCH = 30.0
    
    @require_permission(PermissionLevel.MODIFY, description="Edit file")
    async def edit_file(
        self,
        path: str,
        content: str,
        create_backup: bool = True,
        validate_syntax: bool = True,
    ) -> ToolResult:
        """
        Edit an existing file.
        
        Args:
            path: Path to the file to edit
            content: New file content
            create_backup: Create backup before editing
            validate_syntax: Validate syntax by extension
            
        Returns:
            ToolResult indicating success/failure
            
        Raises:
            ToolFileNotFoundError: If file doesn't exist
            ToolValidationError: If syntax validation fails
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            file_path = Path(path).expanduser().resolve()
            
            # Check if file exists
            if not file_path.exists():
                raise ToolFileNotFoundError(f"File not found: {path}")
            
            # Validate syntax if enabled
            if validate_syntax:
                self._validate_syntax(file_path.suffix, content)
            
            # Create backup
            if create_backup:
                await self._create_backup(file_path)
            
            # Write new content
            async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
                await f.write(content)
            
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return ToolResult(
                success=True,
                output=f"File edited: {path}",
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
    
    @require_permission(PermissionLevel.MODIFY, description="Create file")
    async def create_file(
        self,
        path: str,
        content: str,
        overwrite: bool = False,
        validate_syntax: bool = True,
    ) -> ToolResult:
        """
        Create a new file.
        
        Args:
            path: Path to the file to create
            content: File content
            overwrite: Overwrite if exists
            validate_syntax: Validate syntax by extension
            
        Returns:
            ToolResult indicating success/failure
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            file_path = Path(path).expanduser().resolve()
            
            # Check if file exists
            if file_path.exists() and not overwrite:
                raise ToolExecutionError(f"File already exists: {path}")
            
            # Validate syntax if enabled
            if validate_syntax:
                self._validate_syntax(file_path.suffix, content)
            
            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
                await f.write(content)
            
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
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
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
            '.py': self._validate_python,
            '.json': self._validate_json,
            '.yaml': self._validate_yaml,
            '.yml': self._validate_yaml,
            '.toml': self._validate_toml,
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
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ToolValidationError(f"YAML syntax error: {e}")
    
    def _validate_toml(self, content: str) -> None:
        """Validate TOML syntax."""
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
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
        
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


# Add new exception
class ToolValidationError(ToolExecutionError):
    """Syntax validation failed."""
    pass
```

## Unit Tests (Extend test_tool_executor.py)

```python
class TestEditFile:
    @pytest.mark.asyncio
    async def test_edit_existing_file(self, executor, temp_file):
        # Set permission manager to approve MODIFY
        manager = PermissionManager(interactive=False)
        manager._cache[(PermissionLevel.MODIFY, "edit_file")] = (True, datetime.now())
        set_permission_manager(manager)
        
        result = await executor.edit_file(str(temp_file), "New content")
        assert result.success is True
        assert temp_file.read_text() == "New content"
    
    @pytest.mark.asyncio
    async def test_edit_creates_backup(self, executor, temp_file):
        manager = PermissionManager(interactive=False)
        manager._cache[(PermissionLevel.MODIFY, "edit_file")] = (True, datetime.now())
        set_permission_manager(manager)
        
        await executor.edit_file(str(temp_file), "New content")
        
        backup_path = temp_file.with_suffix(".txt.bak")
        assert backup_path.exists()
        assert backup_path.read_text() == "Hello, World!"
    
    @pytest.mark.asyncio
    async def test_edit_validates_python_syntax(self, executor, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text("# valid")
        
        manager = PermissionManager(interactive=False)
        manager._cache[(PermissionLevel.MODIFY, "edit_file")] = (True, datetime.now())
        set_permission_manager(manager)
        
        with pytest.raises(ToolValidationError):
            await executor.edit_file(str(py_file), "def invalid(")


class TestCreateFile:
    @pytest.mark.asyncio
    async def test_create_new_file(self, executor, tmp_path):
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
        manager = PermissionManager(interactive=False)
        manager._cache[(PermissionLevel.MODIFY, "create_file")] = (True, datetime.now())
        set_permission_manager(manager)
        
        with pytest.raises(ToolExecutionError):
            await executor.create_file(str(temp_file), "New content")


class TestLaunchApp:
    @pytest.mark.asyncio
    async def test_launch_echo(self, executor):
        manager = PermissionManager(interactive=False)
        manager._cache[(PermissionLevel.DANGEROUS, "launch_app")] = (True, datetime.now())
        set_permission_manager(manager)
        
        result = await executor.launch_app("echo", ["Hello"])
        
        assert result.success is True
        assert "Hello" in result.output["stdout"]
    
    @pytest.mark.asyncio
    async def test_launch_nonexistent_app(self, executor):
        manager = PermissionManager(interactive=False)
        manager._cache[(PermissionLevel.DANGEROUS, "launch_app")] = (True, datetime.now())
        set_permission_manager(manager)
        
        with pytest.raises(ToolExecutionError):
            await executor.launch_app("nonexistent_app_12345")
```

## Acceptance Criteria

- [ ] `edit_file()` method with MODIFY permission decorator
- [ ] `edit_file()` creates backup before modification
- [ ] `edit_file()` validates syntax by extension
- [ ] `create_file()` method with MODIFY permission decorator
- [ ] `create_file()` fails if file exists (unless overwrite=True)
- [ ] `create_file()` creates parent directories
- [ ] `launch_app()` method with DANGEROUS permission decorator
- [ ] `launch_app()` has 30s timeout
- [ ] `launch_app()` captures stdout/stderr
- [ ] `ToolValidationError` exception class created
- [ ] Python syntax validation via `ast.parse()`
- [ ] JSON syntax validation via `json.loads()`
- [ ] YAML syntax validation via `yaml.safe_load()`
- [ ] TOML syntax validation via `tomllib.loads()`
- [ ] Backup naming: `.bak`, `.bak.1`, `.bak.2`, etc.
- [ ] Unit tests passing for all new methods

## Notes

- Extend the existing `tool_executor.py` from Task 2.3
- Add new exceptions to the exceptions section
- Backup files should preserve original permissions
- Syntax validation should be optional (disable for binary/unknown files)
- Permission descriptions should be human-readable
