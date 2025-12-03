"""
Ryx AI - Self-Healing Decorator

@self_healing decorator that makes functions automatically fix themselves.

Usage:
    from core.healing import self_healing
    
    @self_healing(max_retries=3)
    def risky_function(x, y):
        return x / y  # Will auto-fix if ZeroDivisionError
    
    # Now calling risky_function(10, 0) will:
    # 1. Catch the exception
    # 2. Analyze the error
    # 3. Generate a fix
    # 4. Apply the fix (if possible)
    # 5. Retry with the fix
"""

import functools
import asyncio
import logging
import importlib
import sys
from typing import Optional, Callable, Any, TypeVar
from dataclasses import dataclass, field
from datetime import datetime

from .exception_handler import (
    ExceptionHandler, ExceptionContext, AIFixer, 
    FixResult, CodeReplacer
)

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


@dataclass
class HealingAttempt:
    """Record of a healing attempt"""
    timestamp: str
    exception_type: str
    exception_message: str
    fix_generated: bool
    fix_applied: bool
    retry_succeeded: bool
    explanation: Optional[str] = None


@dataclass
class HealingStats:
    """Statistics for healing attempts"""
    total_exceptions: int = 0
    fixes_generated: int = 0
    fixes_applied: int = 0
    retries_succeeded: int = 0
    attempts: list = field(default_factory=list)
    
    def add_attempt(self, attempt: HealingAttempt):
        self.attempts.append(attempt)
        self.total_exceptions += 1
        if attempt.fix_generated:
            self.fixes_generated += 1
        if attempt.fix_applied:
            self.fixes_applied += 1
        if attempt.retry_succeeded:
            self.retries_succeeded += 1
    
    @property
    def success_rate(self) -> float:
        if self.total_exceptions == 0:
            return 1.0
        return self.retries_succeeded / self.total_exceptions


class SelfHealingConfig:
    """Configuration for self-healing behavior"""
    
    def __init__(
        self,
        max_retries: int = 3,
        auto_apply: bool = False,  # If True, applies fixes without confirmation
        hot_reload: bool = False,  # If True, reloads module after fix
        log_attempts: bool = True,
        llm_client: Any = None,
    ):
        self.max_retries = max_retries
        self.auto_apply = auto_apply
        self.hot_reload = hot_reload
        self.log_attempts = log_attempts
        self.llm_client = llm_client


# Global config and stats
_config = SelfHealingConfig()
_stats = HealingStats()


def configure_healing(
    max_retries: int = 3,
    auto_apply: bool = False,
    hot_reload: bool = False,
    llm_client: Any = None,
):
    """Configure the self-healing system"""
    global _config
    _config = SelfHealingConfig(
        max_retries=max_retries,
        auto_apply=auto_apply,
        hot_reload=hot_reload,
        llm_client=llm_client,
    )


def get_healing_stats() -> HealingStats:
    """Get healing statistics"""
    return _stats


def self_healing(
    max_retries: Optional[int] = None,
    auto_apply: Optional[bool] = None,
) -> Callable[[F], F]:
    """
    Decorator that makes a function self-healing.
    
    Args:
        max_retries: Maximum retry attempts (default from config)
        auto_apply: Whether to auto-apply fixes (default from config)
    
    Example:
        @self_healing(max_retries=2)
        def my_function():
            ...
    """
    def decorator(func: F) -> F:
        handler = ExceptionHandler()
        fixer = AIFixer(_config.llm_client)
        replacer = CodeReplacer()
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            retries = max_retries or _config.max_retries
            should_auto_apply = auto_apply if auto_apply is not None else _config.auto_apply
            
            last_exception = None
            
            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    if attempt >= retries:
                        # Out of retries
                        logger.error(f"Function {func.__name__} failed after {retries} retries")
                        raise
                    
                    # Capture context
                    context = handler.capture(e)
                    
                    logger.warning(
                        f"Exception in {func.__name__}: {e}. "
                        f"Attempting heal (try {attempt + 1}/{retries})"
                    )
                    
                    # Try to generate fix
                    if _config.llm_client:
                        # Need to run async fix in sync context
                        loop = asyncio.new_event_loop()
                        try:
                            fix_result = loop.run_until_complete(
                                fixer.generate_fix(context)
                            )
                        finally:
                            loop.close()
                        
                        # Record attempt
                        healing_attempt = HealingAttempt(
                            timestamp=datetime.now().isoformat(),
                            exception_type=context.exception_type,
                            exception_message=context.exception_message,
                            fix_generated=fix_result.success,
                            fix_applied=False,
                            retry_succeeded=False,
                            explanation=fix_result.explanation,
                        )
                        
                        if fix_result.success and should_auto_apply:
                            # Apply the fix
                            if context.file_path and context.function_name:
                                success, error = replacer.replace_function(
                                    context.file_path,
                                    context.function_name,
                                    fix_result.fixed_code
                                )
                                
                                if success:
                                    healing_attempt.fix_applied = True
                                    
                                    # Hot reload if enabled
                                    if _config.hot_reload:
                                        _hot_reload_module(context.file_path)
                                else:
                                    logger.warning(f"Could not apply fix: {error}")
                        
                        _stats.add_attempt(healing_attempt)
                    
                    # Continue to next retry
                    continue
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            retries = max_retries or _config.max_retries
            should_auto_apply = auto_apply if auto_apply is not None else _config.auto_apply
            
            last_exception = None
            
            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    if attempt >= retries:
                        logger.error(f"Async function {func.__name__} failed after {retries} retries")
                        raise
                    
                    context = handler.capture(e)
                    
                    logger.warning(
                        f"Exception in {func.__name__}: {e}. "
                        f"Attempting heal (try {attempt + 1}/{retries})"
                    )
                    
                    if _config.llm_client:
                        fix_result = await fixer.generate_fix(context)
                        
                        healing_attempt = HealingAttempt(
                            timestamp=datetime.now().isoformat(),
                            exception_type=context.exception_type,
                            exception_message=context.exception_message,
                            fix_generated=fix_result.success,
                            fix_applied=False,
                            retry_succeeded=False,
                            explanation=fix_result.explanation,
                        )
                        
                        if fix_result.success and should_auto_apply:
                            if context.file_path and context.function_name:
                                success, error = replacer.replace_function(
                                    context.file_path,
                                    context.function_name,
                                    fix_result.fixed_code
                                )
                                
                                if success:
                                    healing_attempt.fix_applied = True
                                    if _config.hot_reload:
                                        _hot_reload_module(context.file_path)
                        
                        _stats.add_attempt(healing_attempt)
                    
                    continue
            
            if last_exception:
                raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def _hot_reload_module(file_path: str):
    """Hot reload a module after code changes"""
    try:
        # Find the module
        for name, module in sys.modules.items():
            if hasattr(module, '__file__') and module.__file__ == file_path:
                importlib.reload(module)
                logger.info(f"Hot-reloaded module: {name}")
                return
        
        logger.warning(f"Could not find module to reload for: {file_path}")
    except Exception as e:
        logger.error(f"Failed to hot-reload module: {e}")


# Convenience function for manual healing
async def heal_exception(
    exception: Exception,
    llm_client: Any,
    auto_apply: bool = False,
) -> FixResult:
    """
    Manually trigger healing for an exception.
    
    Usage:
        try:
            risky_code()
        except Exception as e:
            fix = await heal_exception(e, llm_client)
            if fix.success:
                print(f"Fix found: {fix.explanation}")
                print(fix.fixed_code)
    """
    handler = ExceptionHandler()
    fixer = AIFixer(llm_client)
    
    context = handler.capture(exception)
    fix_result = await fixer.generate_fix(context)
    
    if fix_result.success and auto_apply:
        replacer = CodeReplacer()
        if context.file_path and context.function_name:
            success, error = replacer.replace_function(
                context.file_path,
                context.function_name,
                fix_result.fixed_code
            )
            fix_result.applied = success
    
    return fix_result
