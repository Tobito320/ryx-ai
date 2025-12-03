"""
Ryx AI - Self-Healing Package

Provides automatic error recovery and self-fixing capabilities.

Components:
- ExceptionHandler: Captures full context when errors occur
- AIFixer: Uses LLM to generate fixes
- CodeReplacer: Safely applies code patches
- @self_healing: Decorator for self-healing functions

Usage:
    from core.healing import self_healing, heal_exception, configure_healing
    
    # Configure with LLM client
    configure_healing(
        max_retries=3,
        auto_apply=False,  # Set True to auto-apply fixes
        llm_client=my_llm_client
    )
    
    # Use decorator
    @self_healing()
    def my_function():
        ...
    
    # Or manually heal
    try:
        risky_code()
    except Exception as e:
        fix = await heal_exception(e, llm_client)
"""

from .exception_handler import (
    ExceptionHandler,
    ExceptionContext,
    AIFixer,
    FixResult,
    CodeReplacer,
    get_exception_handler,
    get_ai_fixer,
    get_code_replacer,
)

from .decorator import (
    self_healing,
    heal_exception,
    configure_healing,
    get_healing_stats,
    HealingAttempt,
    HealingStats,
    SelfHealingConfig,
)

__all__ = [
    # Exception handling
    'ExceptionHandler',
    'ExceptionContext',
    'AIFixer',
    'FixResult',
    'CodeReplacer',
    
    # Singleton getters
    'get_exception_handler',
    'get_ai_fixer',
    'get_code_replacer',
    
    # Decorator and config
    'self_healing',
    'heal_exception',
    'configure_healing',
    'get_healing_stats',
    
    # Data classes
    'HealingAttempt',
    'HealingStats',
    'SelfHealingConfig',
]
