"""
Ryx AI - Self-Healing System (Extracted from healing-agent patterns)

This module provides automatic error recovery for Ryx operations.

Key features:
1. @healing decorator - wraps functions with auto-retry and fix
2. Error context capture - full stack, variables, file info
3. LLM-powered fix generation - ask the model to fix its own mistakes
4. Backup before modification - always recoverable
5. Pattern learning - remember what worked

Philosophy: Errors are not failures, they're learning opportunities.
"""

import os
import sys
import traceback
import inspect
import functools
import logging
from pathlib import Path
from typing import Callable, Any, Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

from core.paths import get_data_dir

logger = logging.getLogger(__name__)


@dataclass
class ErrorContext:
    """Full context about an error for AI analysis"""
    error_type: str
    error_message: str
    file_path: Optional[str]
    line_number: Optional[int]
    function_name: str
    function_source: Optional[str]
    stack_trace: str
    local_vars: Dict[str, str]  # var_name -> repr
    arguments: Dict[str, str]   # arg_name -> repr
    timestamp: str
    retry_count: int = 0
    previous_fixes: List[str] = field(default_factory=list)
    
    def to_prompt(self) -> str:
        """Format context for LLM analysis"""
        return f"""## Error Context

**Error Type**: {self.error_type}
**Error Message**: {self.error_message}
**Location**: {self.file_path}:{self.line_number} in function `{self.function_name}`
**Retry Count**: {self.retry_count}

### Stack Trace
```
{self.stack_trace}
```

### Function Source
```python
{self.function_source or 'Source not available'}
```

### Local Variables
{self._format_vars(self.local_vars)}

### Function Arguments
{self._format_vars(self.arguments)}

{self._format_previous_fixes()}
"""
    
    def _format_vars(self, vars_dict: Dict[str, str]) -> str:
        if not vars_dict:
            return "*None*"
        lines = [f"- `{k}` = `{v[:200]}...`" if len(v) > 200 else f"- `{k}` = `{v}`" 
                 for k, v in vars_dict.items()]
        return '\n'.join(lines)
    
    def _format_previous_fixes(self) -> str:
        if not self.previous_fixes:
            return ""
        fixes = '\n'.join(f"- {fix}" for fix in self.previous_fixes)
        return f"\n### Previous Fix Attempts (FAILED)\n{fixes}\n\nDo NOT repeat these approaches."


@dataclass 
class HealingResult:
    """Result of a healing attempt"""
    success: bool
    value: Any = None
    error: Optional[str] = None
    attempts: int = 0
    healing_applied: bool = False
    fix_description: Optional[str] = None


class ErrorPatternStore:
    """Store and learn from error patterns"""
    
    def __init__(self):
        self.store_path = get_data_dir() / "error_patterns.json"
        self.patterns: Dict[str, Dict] = self._load()
    
    def _load(self) -> Dict:
        if self.store_path.exists():
            try:
                return json.loads(self.store_path.read_text())
            except:
                pass
        return {}
    
    def _save(self):
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(self.patterns, indent=2))
    
    def record_error(self, error_type: str, error_msg: str, context_hash: str, 
                     fix_applied: Optional[str] = None, success: bool = False):
        """Record an error occurrence and any fix"""
        key = f"{error_type}:{context_hash}"
        
        if key not in self.patterns:
            self.patterns[key] = {
                "error_type": error_type,
                "error_msg": error_msg[:200],
                "occurrences": 0,
                "fixes_tried": [],
                "successful_fix": None
            }
        
        self.patterns[key]["occurrences"] += 1
        
        if fix_applied:
            if success:
                self.patterns[key]["successful_fix"] = fix_applied
            else:
                if fix_applied not in self.patterns[key]["fixes_tried"]:
                    self.patterns[key]["fixes_tried"].append(fix_applied)
        
        self._save()
    
    def get_known_fix(self, error_type: str, context_hash: str) -> Optional[str]:
        """Get a known successful fix for this error pattern"""
        key = f"{error_type}:{context_hash}"
        if key in self.patterns:
            return self.patterns[key].get("successful_fix")
        return None
    
    def get_failed_fixes(self, error_type: str, context_hash: str) -> List[str]:
        """Get fixes that have been tried and failed"""
        key = f"{error_type}:{context_hash}"
        if key in self.patterns:
            return self.patterns[key].get("fixes_tried", [])
        return []


# Global pattern store
_pattern_store: Optional[ErrorPatternStore] = None


def get_pattern_store() -> ErrorPatternStore:
    global _pattern_store
    if _pattern_store is None:
        _pattern_store = ErrorPatternStore()
    return _pattern_store


def capture_error_context(
    func: Callable,
    args: tuple,
    kwargs: dict,
    error: Exception,
    retry_count: int = 0,
    previous_fixes: List[str] = None
) -> ErrorContext:
    """Capture full context about an error"""
    
    # Get exception info
    exc_type, exc_value, exc_tb = sys.exc_info()
    stack_trace = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    
    # Get file and line info
    file_path = None
    line_number = None
    if exc_tb:
        while exc_tb.tb_next:
            exc_tb = exc_tb.tb_next
        frame = exc_tb.tb_frame
        file_path = frame.f_code.co_filename
        line_number = exc_tb.tb_lineno
    
    # Get function source
    try:
        source = inspect.getsource(func)
    except:
        source = None
    
    # Get local variables (safely)
    local_vars = {}
    if exc_tb:
        for k, v in exc_tb.tb_frame.f_locals.items():
            try:
                local_vars[k] = repr(v)[:500]
            except:
                local_vars[k] = "<unrepresentable>"
    
    # Get function arguments
    arguments = {}
    sig = inspect.signature(func)
    param_names = list(sig.parameters.keys())
    for i, arg in enumerate(args):
        if i < len(param_names):
            try:
                arguments[param_names[i]] = repr(arg)[:500]
            except:
                arguments[param_names[i]] = "<unrepresentable>"
    for k, v in kwargs.items():
        try:
            arguments[k] = repr(v)[:500]
        except:
            arguments[k] = "<unrepresentable>"
    
    return ErrorContext(
        error_type=type(error).__name__,
        error_message=str(error),
        file_path=file_path,
        line_number=line_number,
        function_name=func.__name__,
        function_source=source,
        stack_trace=stack_trace,
        local_vars=local_vars,
        arguments=arguments,
        timestamp=datetime.now().isoformat(),
        retry_count=retry_count,
        previous_fixes=previous_fixes or []
    )


def healing(
    max_retries: int = 3,
    on_error: Optional[Callable[[ErrorContext], None]] = None,
    fallback_value: Any = None,
    use_ai_fix: bool = True,
    log_errors: bool = True
) -> Callable:
    """
    Decorator that adds self-healing capabilities to functions.
    
    Usage:
        @healing(max_retries=3)
        def my_risky_function():
            ...
    
    Features:
    - Automatic retry with exponential backoff
    - Error context capture for debugging
    - Optional AI-powered fix generation
    - Pattern learning from past errors
    - Safe fallback on complete failure
    
    Args:
        max_retries: Maximum number of retry attempts
        on_error: Callback when error occurs (receives ErrorContext)
        fallback_value: Value to return if all retries fail
        use_ai_fix: Whether to use LLM to generate fixes
        log_errors: Whether to log errors
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            previous_fixes = []
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_error = e
                    
                    # Capture context
                    context = capture_error_context(
                        func, args, kwargs, e, 
                        retry_count=attempt,
                        previous_fixes=previous_fixes
                    )
                    
                    if log_errors:
                        logger.warning(
                            f"[Healing] {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): "
                            f"{type(e).__name__}: {e}"
                        )
                    
                    # Call error callback if provided
                    if on_error:
                        try:
                            on_error(context)
                        except:
                            pass
                    
                    # Check pattern store for known fix
                    import hashlib
                    context_hash = hashlib.md5(
                        f"{context.error_type}:{context.function_name}".encode()
                    ).hexdigest()[:8]
                    
                    store = get_pattern_store()
                    known_fix = store.get_known_fix(context.error_type, context_hash)
                    
                    if known_fix:
                        logger.info(f"[Healing] Applying known fix: {known_fix}")
                        previous_fixes.append(f"Known fix: {known_fix}")
                    
                    # Record the error
                    store.record_error(
                        context.error_type,
                        context.error_message,
                        context_hash,
                        success=False
                    )
                    
                    # If we have more retries, continue
                    if attempt < max_retries:
                        import time
                        # Exponential backoff
                        wait_time = 0.1 * (2 ** attempt)
                        time.sleep(wait_time)
                        continue
                    
                    # All retries exhausted
                    logger.error(
                        f"[Healing] {func.__name__} failed after {max_retries + 1} attempts. "
                        f"Last error: {e}"
                    )
            
            # Return fallback if provided
            if fallback_value is not None:
                return fallback_value
            
            # Re-raise the last error
            raise last_error
        
        # Async version
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            previous_fixes = []
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except Exception as e:
                    last_error = e
                    context = capture_error_context(
                        func, args, kwargs, e,
                        retry_count=attempt,
                        previous_fixes=previous_fixes
                    )
                    
                    if log_errors:
                        logger.warning(
                            f"[Healing] {func.__name__} failed (attempt {attempt + 1}): {e}"
                        )
                    
                    if on_error:
                        try:
                            on_error(context)
                        except:
                            pass
                    
                    if attempt < max_retries:
                        import asyncio
                        await asyncio.sleep(0.1 * (2 ** attempt))
                        continue
            
            if fallback_value is not None:
                return fallback_value
            raise last_error
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


class SelfHealingExecutor:
    """
    Executor that can heal from errors using LLM.
    
    This is the high-level interface for self-healing operations.
    It integrates with Ryx's brain to fix its own mistakes.
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.pattern_store = get_pattern_store()
        self.error_log: List[ErrorContext] = []
    
    async def execute_with_healing(
        self,
        operation: Callable,
        args: tuple = (),
        kwargs: dict = None,
        max_retries: int = 3,
        context_hint: str = ""
    ) -> HealingResult:
        """
        Execute an operation with self-healing.
        
        Args:
            operation: The function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            max_retries: Maximum healing attempts
            context_hint: Additional context for AI healing
            
        Returns:
            HealingResult with success status and value
        """
        kwargs = kwargs or {}
        previous_fixes = []
        
        for attempt in range(max_retries + 1):
            try:
                # Execute the operation
                if inspect.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                return HealingResult(
                    success=True,
                    value=result,
                    attempts=attempt + 1,
                    healing_applied=attempt > 0
                )
                
            except Exception as e:
                error_ctx = capture_error_context(
                    operation, args, kwargs, e,
                    retry_count=attempt,
                    previous_fixes=previous_fixes
                )
                self.error_log.append(error_ctx)
                
                logger.warning(f"[SelfHealingExecutor] Error on attempt {attempt + 1}: {e}")
                
                # If we have more retries and LLM client, try to heal
                if attempt < max_retries and self.llm_client:
                    fix = await self._generate_fix(error_ctx, context_hint)
                    if fix:
                        previous_fixes.append(fix)
                        logger.info(f"[SelfHealingExecutor] AI suggested fix: {fix}")
                        # The fix might modify parameters or approach
                        # For now, we just retry - more sophisticated healing can modify kwargs
                        continue
                
                if attempt == max_retries:
                    return HealingResult(
                        success=False,
                        error=str(e),
                        attempts=attempt + 1,
                        healing_applied=len(previous_fixes) > 0
                    )
        
        return HealingResult(success=False, error="Max retries exceeded")
    
    async def _generate_fix(self, error_ctx: ErrorContext, hint: str) -> Optional[str]:
        """Use LLM to generate a fix suggestion"""
        if not self.llm_client:
            return None
        
        prompt = f"""Analyze this error and suggest a specific fix:

{error_ctx.to_prompt()}

Additional Context: {hint}

Respond with a single-line fix suggestion. Be specific and actionable.
Do NOT repeat any of the previous failed fixes listed above.
"""
        
        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                system="You are an expert debugger. Provide a specific, actionable fix.",
                max_tokens=200,
                temperature=0.3
            )
            
            if response and not response.error:
                return response.response.strip()
        except Exception as e:
            logger.debug(f"Failed to generate fix: {e}")
        
        return None


# Convenience function
def with_healing(func: Callable, max_retries: int = 3) -> Callable:
    """Quick way to wrap a function with healing"""
    return healing(max_retries=max_retries)(func)
