"""
Ryx AI - Self-Healing System

Inspired by: healing-agent

Components:
1. ExceptionHandler - Captures full context when errors occur
2. AIFixer - Uses LLM to generate fixes
3. CodeReplacer - Safely applies code patches
4. HealingDecorator - @self_healing decorator for functions

This enables Ryx to:
- Catch runtime errors
- Analyze what went wrong
- Generate and apply fixes
- Retry with the fix
- Learn from the experience
"""

import sys
import traceback
import inspect
import ast
import logging
from typing import Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExceptionContext:
    """Full context captured when an exception occurs"""
    
    # Exception info
    exception_type: str
    exception_message: str
    traceback_str: str
    
    # Location
    file_path: Optional[str] = None
    function_name: Optional[str] = None
    line_number: Optional[int] = None
    
    # Context
    source_code: Optional[str] = None
    local_vars: Dict[str, str] = field(default_factory=dict)
    global_vars: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    python_version: str = field(default_factory=lambda: sys.version)
    
    def to_prompt(self) -> str:
        """Convert to a prompt for the LLM to analyze"""
        prompt = f"""# Exception Analysis Request

## Error Information
- **Type**: {self.exception_type}
- **Message**: {self.exception_message}
- **Location**: {self.file_path}:{self.line_number} in {self.function_name}

## Traceback
```
{self.traceback_str}
```

## Source Code (around error)
```python
{self.source_code or 'Not available'}
```

## Local Variables
{self._format_vars(self.local_vars)}

## Task
1. Analyze why this error occurred
2. Provide a fixed version of the code
3. Explain the fix

Respond with:
1. **Root Cause**: Why did this happen?
2. **Fix**: The corrected code
3. **Prevention**: How to prevent this in future
"""
        return prompt
    
    def _format_vars(self, vars_dict: Dict[str, str]) -> str:
        if not vars_dict:
            return "None captured"
        lines = []
        for name, value in list(vars_dict.items())[:10]:  # Limit to 10
            lines.append(f"- `{name}`: {value[:100]}")
        return "\n".join(lines)


class ExceptionHandler:
    """
    Captures comprehensive context when an exception occurs.
    
    Usage:
        handler = ExceptionHandler()
        
        try:
            risky_code()
        except Exception as e:
            context = handler.capture(e)
            # Now we have full context to analyze
    """
    
    def __init__(self, max_source_lines: int = 20):
        self.max_source_lines = max_source_lines
    
    def capture(self, exception: Exception, frame: Optional[Any] = None) -> ExceptionContext:
        """Capture full context from an exception"""
        
        # Get traceback
        tb_str = traceback.format_exc()
        
        # Extract exception info
        exc_type = type(exception).__name__
        exc_msg = str(exception)
        
        # Get the frame where exception occurred
        if frame is None:
            tb = exception.__traceback__
            while tb and tb.tb_next:
                tb = tb.tb_next
            frame = tb.tb_frame if tb else None
        
        # Extract location info
        file_path = None
        func_name = None
        line_no = None
        source_code = None
        local_vars = {}
        global_vars = {}
        
        if frame:
            file_path = frame.f_code.co_filename
            func_name = frame.f_code.co_name
            line_no = frame.f_lineno
            
            # Get local variables (safely)
            local_vars = self._safe_repr_vars(frame.f_locals)
            
            # Get relevant global variables
            global_vars = self._safe_repr_vars(
                {k: v for k, v in frame.f_globals.items() 
                 if not k.startswith('__') and not inspect.ismodule(v)}
            )
            
            # Get source code around the error
            source_code = self._get_source_context(file_path, line_no)
        
        return ExceptionContext(
            exception_type=exc_type,
            exception_message=exc_msg,
            traceback_str=tb_str,
            file_path=file_path,
            function_name=func_name,
            line_number=line_no,
            source_code=source_code,
            local_vars=local_vars,
            global_vars=global_vars,
        )
    
    def _safe_repr_vars(self, vars_dict: Dict) -> Dict[str, str]:
        """Safely get string representation of variables"""
        result = {}
        for name, value in vars_dict.items():
            try:
                # Skip internal/private
                if name.startswith('_'):
                    continue
                # Skip callables
                if callable(value) and not isinstance(value, type):
                    continue
                
                repr_val = repr(value)
                if len(repr_val) > 200:
                    repr_val = repr_val[:200] + "..."
                result[name] = repr_val
            except Exception:
                result[name] = "<unable to repr>"
        return result
    
    def _get_source_context(self, file_path: str, line_no: int) -> Optional[str]:
        """Get source code around the error line"""
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            with open(path) as f:
                lines = f.readlines()
            
            start = max(0, line_no - self.max_source_lines // 2)
            end = min(len(lines), line_no + self.max_source_lines // 2)
            
            result = []
            for i in range(start, end):
                marker = ">>> " if i == line_no - 1 else "    "
                result.append(f"{marker}{i+1:4d} | {lines[i].rstrip()}")
            
            return "\n".join(result)
        except Exception:
            return None


@dataclass
class FixResult:
    """Result of attempting to fix code"""
    success: bool
    original_code: str
    fixed_code: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None
    applied: bool = False


class AIFixer:
    """
    Uses LLM to analyze errors and generate fixes.
    
    Usage:
        fixer = AIFixer(llm_client)
        context = handler.capture(exception)
        fix = await fixer.generate_fix(context)
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._fix_history: list = []
    
    async def generate_fix(
        self,
        context: ExceptionContext,
        max_attempts: int = 3
    ) -> FixResult:
        """Generate a fix for the exception"""
        
        if not self.llm_client:
            return FixResult(
                success=False,
                original_code=context.source_code or "",
                error="No LLM client configured"
            )
        
        prompt = context.to_prompt()
        
        system = """You are an expert Python debugger. 
Analyze the error and provide a fix.

IMPORTANT: Respond in this exact format:

## Root Cause
<brief explanation>

## Fixed Code
```python
<the corrected code>
```

## Prevention
<how to prevent this>
"""
        
        try:
            # Try to get fix from LLM
            response = await self.llm_client.generate(
                prompt=prompt,
                system=system,
                temperature=0.2,
                max_tokens=2000
            )
            
            if response.error:
                return FixResult(
                    success=False,
                    original_code=context.source_code or "",
                    error=response.error
                )
            
            # Parse the response
            fixed_code = self._extract_code(response.response)
            explanation = self._extract_explanation(response.response)
            
            if fixed_code:
                # Validate the fix is valid Python
                try:
                    ast.parse(fixed_code)
                    return FixResult(
                        success=True,
                        original_code=context.source_code or "",
                        fixed_code=fixed_code,
                        explanation=explanation
                    )
                except SyntaxError as e:
                    return FixResult(
                        success=False,
                        original_code=context.source_code or "",
                        fixed_code=fixed_code,
                        error=f"Generated code has syntax error: {e}"
                    )
            else:
                return FixResult(
                    success=False,
                    original_code=context.source_code or "",
                    error="Could not extract fixed code from response"
                )
                
        except Exception as e:
            return FixResult(
                success=False,
                original_code=context.source_code or "",
                error=str(e)
            )
    
    def _extract_code(self, response: str) -> Optional[str]:
        """Extract code block from response"""
        import re
        
        # Look for ```python ... ```
        patterns = [
            r'```python\n(.*?)```',
            r'```\n(.*?)```',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_explanation(self, response: str) -> Optional[str]:
        """Extract explanation from response"""
        import re
        
        # Look for Root Cause section
        match = re.search(r'## Root Cause\n(.*?)(?=##|\Z)', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return None


class CodeReplacer:
    """
    Safely replaces code in files.
    
    Features:
    - AST-based replacement (safer than string replace)
    - Backup before changes
    - Rollback support
    """
    
    def __init__(self, backup_dir: Optional[Path] = None):
        if backup_dir:
            self.backup_dir = backup_dir
        else:
            self.backup_dir = Path.home() / "ryx-ai" / "data" / "healing" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def replace_function(
        self,
        file_path: str,
        function_name: str,
        new_code: str,
        backup: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Replace a function in a file with new code.
        
        Returns:
            (success, error_message)
        """
        path = Path(file_path)
        
        if not path.exists():
            return False, f"File not found: {file_path}"
        
        try:
            # Read original
            original = path.read_text()
            
            # Backup
            if backup:
                backup_path = self.backup_dir / f"{path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                backup_path.write_text(original)
            
            # Parse original
            tree = ast.parse(original)
            
            # Find and replace function
            replaced = False
            new_tree = ast.parse(new_code)
            
            for i, node in enumerate(tree.body):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    # Find the replacement function in new code
                    for new_node in new_tree.body:
                        if isinstance(new_node, ast.FunctionDef) and new_node.name == function_name:
                            tree.body[i] = new_node
                            replaced = True
                            break
            
            if not replaced:
                return False, f"Function {function_name} not found in file"
            
            # Generate new source
            import astor
            new_source = astor.to_source(tree)
            
            # Write back
            path.write_text(new_source)
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def replace_block(
        self,
        file_path: str,
        old_code: str,
        new_code: str,
        backup: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Replace a code block using string matching.
        Simpler but less safe than AST-based.
        """
        path = Path(file_path)
        
        if not path.exists():
            return False, f"File not found: {file_path}"
        
        try:
            original = path.read_text()
            
            if old_code not in original:
                return False, "Original code block not found in file"
            
            # Backup
            if backup:
                backup_path = self.backup_dir / f"{path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                backup_path.write_text(original)
            
            # Replace
            new_content = original.replace(old_code, new_code, 1)
            
            # Validate syntax
            ast.parse(new_content)
            
            # Write
            path.write_text(new_content)
            
            return True, None
            
        except SyntaxError as e:
            return False, f"Replacement would create invalid syntax: {e}"
        except Exception as e:
            return False, str(e)
    
    def rollback(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Rollback to most recent backup"""
        path = Path(file_path)
        
        # Find most recent backup
        backups = sorted(
            self.backup_dir.glob(f"{path.name}.*.bak"),
            reverse=True
        )
        
        if not backups:
            return False, "No backup found"
        
        try:
            backup_content = backups[0].read_text()
            path.write_text(backup_content)
            return True, None
        except Exception as e:
            return False, str(e)


# Global instances
_handler = ExceptionHandler()
_fixer: Optional[AIFixer] = None
_replacer = CodeReplacer()


def get_exception_handler() -> ExceptionHandler:
    return _handler


def get_ai_fixer(llm_client=None) -> AIFixer:
    global _fixer
    if _fixer is None:
        _fixer = AIFixer(llm_client)
    elif llm_client:
        _fixer.llm_client = llm_client
    return _fixer


def get_code_replacer() -> CodeReplacer:
    return _replacer
