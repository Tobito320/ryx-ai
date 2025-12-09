"""
Ryx AI - Memory Package

Experience-based learning and pattern recognition with persistent storage.

Components:
- ExperienceMemory: Store and retrieve past experiences
- PersistentMemory: Encrypted, persistent memory with preferences
- PatternMatch: Similar experience lookup
- Experience types: SUCCESS, FAILURE, FIXED, LEARNED
- Memory types: FACT, PREFERENCE, SESSION, SKILL, ERROR

Usage:
    from core.memory import get_memory, get_persistent_memory, ExperienceType
    
    # Experience-based memory
    memory = get_memory()
    memory.store_success(
        task="Parse JSON safely",
        approach="Used try/except with json.loads",
        result="def parse_safe(s): ..."
    )
    
    # Persistent memory with preferences
    pmem = get_persistent_memory()
    pmem.store_fact("user_name", "Tobi")
    prefs = pmem.get_preferences()
    prefs.language = "de"
    pmem.save_preferences(prefs)
"""

from .experience import (
    ExperienceMemory,
    Experience,
    ExperienceType,
    PatternMatch,
    get_memory,
)

from .persistent_memory import (
    PersistentMemory,
    MemoryEntry,
    MemoryType,
    UserPreferences,
    get_persistent_memory,
)

__all__ = [
    # Experience memory
    'ExperienceMemory',
    'Experience',
    'ExperienceType',
    'PatternMatch',
    'get_memory',
    # Persistent memory
    'PersistentMemory',
    'MemoryEntry',
    'MemoryType',
    'UserPreferences',
    'get_persistent_memory',
]
