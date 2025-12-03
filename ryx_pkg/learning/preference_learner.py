"""
Ryx AI - Preference Learner

Learn user preferences from interactions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)


@dataclass
class UserPreference:
    """A learned user preference"""
    category: str  # coding_style, ui, workflow, model
    key: str
    value: Any
    confidence: float = 0.5
    occurrences: int = 1
    last_seen: datetime = field(default_factory=datetime.now)


class PreferenceLearner:
    """
    Learn and track user preferences.
    
    Categories:
    - coding_style: Indentation, naming, comments
    - ui: Theme, verbosity, display preferences
    - workflow: Preferred tools, patterns, shortcuts
    - model: Model preferences for different tasks
    
    Usage:
    ```python
    learner = PreferenceLearner()
    
    # Record observations
    learner.observe("coding_style", "indent", "4_spaces")
    learner.observe("workflow", "test_command", "pytest -v")
    
    # Get learned preference
    indent = learner.get("coding_style", "indent")
    ```
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path:
            self.db_path = db_path
        else:
            from core.paths import get_data_dir
            self.db_path = get_data_dir() / "preferences.db"
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        # In-memory cache
        self._cache: Dict[str, UserPreference] = {}
        self._load_cache()
    
    def _init_db(self):
        """Initialize the database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                category TEXT,
                key TEXT,
                value TEXT,
                confidence REAL,
                occurrences INTEGER,
                last_seen TEXT,
                PRIMARY KEY (category, key)
            )
        """)
        conn.commit()
        conn.close()
    
    def _load_cache(self):
        """Load preferences into memory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("SELECT * FROM preferences")
        
        for row in cursor.fetchall():
            cache_key = f"{row['category']}.{row['key']}"
            self._cache[cache_key] = UserPreference(
                category=row["category"],
                key=row["key"],
                value=json.loads(row["value"]),
                confidence=row["confidence"],
                occurrences=row["occurrences"],
                last_seen=datetime.fromisoformat(row["last_seen"])
            )
        
        conn.close()
    
    def observe(
        self,
        category: str,
        key: str,
        value: Any,
        weight: float = 1.0
    ):
        """
        Record an observation of user preference.
        
        Multiple observations of the same value increase confidence.
        """
        cache_key = f"{category}.{key}"
        
        if cache_key in self._cache:
            pref = self._cache[cache_key]
            
            if pref.value == value:
                # Same value - increase confidence
                pref.occurrences += 1
                pref.confidence = min(1.0, pref.confidence + 0.1 * weight)
            else:
                # Different value - may need to update
                if weight > pref.confidence:
                    # New preference is stronger
                    pref.value = value
                    pref.confidence = weight
                    pref.occurrences = 1
                else:
                    # Decrease confidence in old value
                    pref.confidence = max(0.1, pref.confidence - 0.1)
            
            pref.last_seen = datetime.now()
        else:
            # New preference
            pref = UserPreference(
                category=category,
                key=key,
                value=value,
                confidence=0.5 * weight,
                occurrences=1
            )
            self._cache[cache_key] = pref
        
        # Persist
        self._save_preference(pref)
    
    def get(
        self,
        category: str,
        key: str,
        default: Any = None
    ) -> Any:
        """Get a learned preference"""
        cache_key = f"{category}.{key}"
        pref = self._cache.get(cache_key)
        
        if pref and pref.confidence >= 0.3:
            return pref.value
        return default
    
    def get_preference(
        self,
        category: str,
        key: str
    ) -> Optional[UserPreference]:
        """Get full preference object"""
        cache_key = f"{category}.{key}"
        return self._cache.get(cache_key)
    
    def get_category(self, category: str) -> Dict[str, Any]:
        """Get all preferences in a category"""
        result = {}
        
        for cache_key, pref in self._cache.items():
            if pref.category == category and pref.confidence >= 0.3:
                result[pref.key] = pref.value
        
        return result
    
    def set(
        self,
        category: str,
        key: str,
        value: Any,
        confidence: float = 1.0
    ):
        """Explicitly set a preference (user-defined)"""
        cache_key = f"{category}.{key}"
        
        pref = UserPreference(
            category=category,
            key=key,
            value=value,
            confidence=confidence,
            occurrences=1
        )
        
        self._cache[cache_key] = pref
        self._save_preference(pref)
    
    def forget(self, category: str, key: str):
        """Remove a preference"""
        cache_key = f"{category}.{key}"
        
        if cache_key in self._cache:
            del self._cache[cache_key]
        
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "DELETE FROM preferences WHERE category = ? AND key = ?",
            (category, key)
        )
        conn.commit()
        conn.close()
    
    def _save_preference(self, pref: UserPreference):
        """Save preference to database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO preferences VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pref.category,
            pref.key,
            json.dumps(pref.value),
            pref.confidence,
            pref.occurrences,
            pref.last_seen.isoformat()
        ))
        conn.commit()
        conn.close()
    
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Get all preferences organized by category"""
        result: Dict[str, Dict[str, Any]] = {}
        
        for pref in self._cache.values():
            if pref.category not in result:
                result[pref.category] = {}
            result[pref.category][pref.key] = {
                "value": pref.value,
                "confidence": pref.confidence,
                "occurrences": pref.occurrences
            }
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get preference statistics"""
        categories: Dict[str, int] = {}
        total = 0
        high_confidence = 0
        
        for pref in self._cache.values():
            total += 1
            categories[pref.category] = categories.get(pref.category, 0) + 1
            if pref.confidence >= 0.7:
                high_confidence += 1
        
        return {
            "total_preferences": total,
            "high_confidence": high_confidence,
            "by_category": categories
        }
    
    def export(self) -> Dict[str, Any]:
        """Export all preferences for backup"""
        return {
            "version": 1,
            "exported_at": datetime.now().isoformat(),
            "preferences": [
                {
                    "category": p.category,
                    "key": p.key,
                    "value": p.value,
                    "confidence": p.confidence,
                    "occurrences": p.occurrences
                }
                for p in self._cache.values()
            ]
        }
    
    def import_preferences(self, data: Dict[str, Any]):
        """Import preferences from backup"""
        for pref_data in data.get("preferences", []):
            self.set(
                category=pref_data["category"],
                key=pref_data["key"],
                value=pref_data["value"],
                confidence=pref_data.get("confidence", 0.8)
            )


# Common preference categories and keys
PREFERENCES = {
    "coding_style": {
        "indent": ["2_spaces", "4_spaces", "tabs"],
        "quotes": ["single", "double"],
        "line_length": [80, 100, 120],
        "trailing_comma": [True, False],
        "docstring_style": ["google", "numpy", "sphinx"]
    },
    "ui": {
        "theme": ["dracula", "nord", "catppuccin", "monokai"],
        "verbosity": ["minimal", "normal", "verbose"],
        "show_tokens": [True, False],
        "show_timing": [True, False]
    },
    "workflow": {
        "auto_commit": [True, False],
        "auto_test": [True, False],
        "branch_per_task": [True, False],
        "confirm_changes": [True, False]
    },
    "model": {
        "preferred_code_model": ["qwen2.5-coder:14b", "deepseek-coder:6.7b"],
        "preferred_chat_model": ["gemma2:9b", "llama3.1:8b"],
        "use_council": [True, False]
    }
}
