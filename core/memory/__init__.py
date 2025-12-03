"""
Ryx AI - Memory Package

Experience-based learning and pattern recognition.

Components:
- ExperienceMemory: Store and retrieve past experiences
- PatternMatch: Similar experience lookup
- Experience types: SUCCESS, FAILURE, FIXED, LEARNED

Usage:
    from core.memory import get_memory, ExperienceType
    
    memory = get_memory()
    
    # Store successful approach
    memory.store_success(
        task="Parse JSON safely",
        approach="Used try/except with json.loads",
        result="def parse_safe(s): ..."
    )
    
    # Find similar past experiences
    matches = memory.find_similar("Parse config file")
    for m in matches:
        print(f"{m.similarity:.2f}: {m.relevant_insight}")
"""

from .experience import (
    ExperienceMemory,
    Experience,
    ExperienceType,
    PatternMatch,
    get_memory,
)

__all__ = [
    'ExperienceMemory',
    'Experience',
    'ExperienceType',
    'PatternMatch',
    'get_memory',
]
