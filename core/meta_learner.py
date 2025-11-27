"""
Ryx AI V2 - Meta Learner
Learns user preferences, patterns, and behaviors to provide personalized assistance
"""

import re
import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

@dataclass
class Preference:
    """A learned user preference"""
    category: str  # e.g., "editor", "shell", "theme"
    value: str  # e.g., "nvim", "zsh", "dark"
    confidence: float  # 0.0 - 1.0
    learned_from: str  # Original query
    learned_at: datetime
    times_applied: int = 0

@dataclass
class Pattern:
    """A detected behavioral pattern"""
    pattern_type: str  # e.g., "frequent_query", "time_of_day", "command_sequence"
    description: str
    occurrences: int = 0
    last_seen: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class MetaLearner:
    """
    Learns from user interactions to provide personalized assistance

    Features:
    - Preference Detection: Automatically detects preferences from queries
    - Pattern Recognition: Identifies behavioral patterns
    - Auto-Apply: Applies learned preferences without asking
    - Interaction History: Tracks all interactions for learning
    - Model Performance Tracking: Learns which models work best for which tasks
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.home() / "ryx-ai" / "data" / "meta_learning.db"

        self.db_path = db_path
        self.preferences: Dict[str, Preference] = {}
        self.patterns: Dict[str, Pattern] = {}

        self._init_db()
        self._load_preferences()
        self._load_patterns()

        # Preference detection patterns
        self.preference_patterns = {
            "editor": {
                "keywords": ["editor", "edit", "open", "vim", "nvim", "nano", "emacs", "code", "vscode"],
                "extractors": [
                    (r"use (\w+) (not|instead of)", 1),  # "use nvim not nano"
                    (r"prefer (\w+)", 1),  # "prefer nvim"
                    (r"always use (\w+)", 1),  # "always use nvim"
                    (r"open .* with (\w+)", 1),  # "open file with nvim"
                    (r"my editor is (\w+)", 1),  # "my editor is nvim"
                ]
            },
            "shell": {
                "keywords": ["shell", "bash", "zsh", "fish"],
                "extractors": [
                    (r"use (\w+) shell", 1),
                    (r"my shell is (\w+)", 1),
                    (r"switch to (\w+)", 1),
                ]
            },
            "theme": {
                "keywords": ["theme", "color", "dark", "light"],
                "extractors": [
                    (r"use (dark|light) theme", 1),
                    (r"prefer (dark|light) mode", 1),
                ]
            },
            "file_manager": {
                "keywords": ["file manager", "ranger", "nnn", "lf"],
                "extractors": [
                    (r"use (\w+) for files", 1),
                    (r"file manager: (\w+)", 1),
                ]
            }
        }

    def _init_db(self):
        """Initialize meta learning database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                category TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                learned_from TEXT,
                learned_at TEXT,
                times_applied INTEGER DEFAULT 0
            )
        """)

        # Patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                description TEXT,
                occurrences INTEGER DEFAULT 0,
                last_seen TEXT,
                metadata TEXT
            )
        """)

        # Interaction history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query TEXT NOT NULL,
                response TEXT,
                model_used TEXT,
                latency_ms INTEGER,
                complexity REAL,
                preferences_applied TEXT,
                user_feedback TEXT
            )
        """)

        # Command frequency tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_frequency (
                command TEXT PRIMARY KEY,
                count INTEGER DEFAULT 0,
                last_used TEXT,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

    def _load_preferences(self):
        """Load saved preferences from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM preferences")

        for row in cursor.fetchall():
            self.preferences[row["category"]] = Preference(
                category=row["category"],
                value=row["value"],
                confidence=row["confidence"],
                learned_from=row["learned_from"],
                learned_at=datetime.fromisoformat(row["learned_at"]),
                times_applied=row["times_applied"]
            )

        conn.close()

    def _load_patterns(self):
        """Load detected patterns from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM patterns")

        for row in cursor.fetchall():
            self.patterns[row["pattern_id"]] = Pattern(
                pattern_type=row["pattern_type"],
                description=row["description"],
                occurrences=row["occurrences"],
                last_seen=datetime.fromisoformat(row["last_seen"]) if row["last_seen"] else None,
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )

        conn.close()

    def detect_preferences_from_query(self, query: str) -> List[Preference]:
        """
        Detect preferences from user query

        Examples:
        - "use nvim not nano" -> editor: nvim
        - "always use zsh" -> shell: zsh
        - "prefer dark theme" -> theme: dark
        """
        detected = []
        query_lower = query.lower()

        for category, config in self.preference_patterns.items():
            # Check if query is related to this category
            if not any(kw in query_lower for kw in config["keywords"]):
                continue

            # Try to extract value using patterns
            for pattern, group_idx in config["extractors"]:
                match = re.search(pattern, query_lower)
                if match:
                    value = match.group(group_idx)

                    # Create preference
                    pref = Preference(
                        category=category,
                        value=value,
                        confidence=0.9,  # High confidence for explicit statements
                        learned_from=query,
                        learned_at=datetime.now()
                    )

                    detected.append(pref)
                    self._save_preference(pref)
                    break

        return detected

    def infer_preferences_from_interaction(self, query: str, commands_executed: List[str]):
        """
        Infer preferences from executed commands

        Example:
        - User always uses "nvim" in responses -> infer editor preference
        - User frequently uses "ranger" -> infer file manager preference
        """
        # Track editor usage
        editor_commands = ["nvim", "vim", "nano", "emacs", "code"]
        for cmd in commands_executed:
            for editor in editor_commands:
                if editor in cmd:
                    self._increment_command_frequency(editor)

                    # If used frequently, infer preference
                    freq = self._get_command_frequency(editor)
                    if freq >= 3 and "editor" not in self.preferences:
                        pref = Preference(
                            category="editor",
                            value=editor,
                            confidence=0.7,  # Medium confidence for inferred
                            learned_from=f"Inferred from {freq} uses",
                            learned_at=datetime.now()
                        )
                        self._save_preference(pref)

    def apply_preferences(self, response: str) -> str:
        """
        Apply learned preferences to AI response

        Example:
        - Response contains "nano config.txt"
        - User prefers nvim
        - Result: "nvim config.txt"
        """
        modified_response = response

        # Apply editor preference
        if "editor" in self.preferences:
            preferred_editor = self.preferences["editor"].value

            # Replace other editors with preferred one
            other_editors = ["nano", "vim", "nvim", "emacs", "vi", "code", "gedit", "kate"]
            if preferred_editor in other_editors:
                other_editors.remove(preferred_editor)

            for other_editor in other_editors:
                # Replace standalone editor commands (more aggressive matching)
                # Match with word boundaries and in command contexts
                patterns = [
                    r'\b' + other_editor + r'\b',  # Standalone
                    r'\b' + other_editor + r'\s+',  # With space after
                ]

                for pattern in patterns:
                    modified_response = re.sub(pattern, preferred_editor + ' ', modified_response, flags=re.IGNORECASE)

            # Clean up any double spaces
            modified_response = re.sub(r'  +', ' ', modified_response)

            # Increment usage counter
            self.preferences["editor"].times_applied += 1
            self._update_preference_usage("editor")

        # Apply shell preference
        if "shell" in self.preferences:
            preferred_shell = self.preferences["shell"].value
            # Replace shell references
            for shell in ["bash", "zsh", "fish", "sh"]:
                if shell != preferred_shell:
                    modified_response = modified_response.replace(f"#!/bin/{shell}", f"#!/bin/{preferred_shell}")

        return modified_response

    def get_preferences(self) -> Dict[str, str]:
        """Get all current preferences as simple dict"""
        return {
            category: pref.value
            for category, pref in self.preferences.items()
        }

    def record_interaction(self,
                          query: str,
                          response: str,
                          model_used: str,
                          latency_ms: int,
                          complexity: float,
                          preferences_applied: Optional[Dict] = None):
        """Record an interaction for learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO interactions
            (timestamp, query, response, model_used, latency_ms, complexity, preferences_applied)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            query,
            response,
            model_used,
            latency_ms,
            complexity,
            json.dumps(preferences_applied) if preferences_applied else None
        ))

        conn.commit()
        conn.close()

        # Detect preferences from this interaction
        self.detect_preferences_from_query(query)

        # Detect patterns
        self._detect_patterns(query, response)

    def _detect_patterns(self, query: str, response: str):
        """Detect behavioral patterns"""
        query_lower = query.lower()

        # Pattern: Frequent config queries
        if "config" in query_lower:
            pattern_id = "frequent_config_queries"
            if pattern_id in self.patterns:
                self.patterns[pattern_id].occurrences += 1
                self.patterns[pattern_id].last_seen = datetime.now()
            else:
                self.patterns[pattern_id] = Pattern(
                    pattern_type="frequent_query",
                    description="User frequently queries about configs",
                    occurrences=1,
                    last_seen=datetime.now()
                )
            self._save_pattern(self.patterns[pattern_id], pattern_id)

        # Pattern: Code-related queries
        if any(kw in query_lower for kw in ["code", "function", "script", "debug"]):
            pattern_id = "code_focused"
            if pattern_id in self.patterns:
                self.patterns[pattern_id].occurrences += 1
                self.patterns[pattern_id].last_seen = datetime.now()
            else:
                self.patterns[pattern_id] = Pattern(
                    pattern_type="frequent_query",
                    description="User frequently works with code",
                    occurrences=1,
                    last_seen=datetime.now()
                )
            self._save_pattern(self.patterns[pattern_id], pattern_id)

    def _save_preference(self, pref: Preference):
        """Save preference to database"""
        self.preferences[pref.category] = pref

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO preferences
            (category, value, confidence, learned_from, learned_at, times_applied)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pref.category,
            pref.value,
            pref.confidence,
            pref.learned_from,
            pref.learned_at.isoformat(),
            pref.times_applied
        ))

        conn.commit()
        conn.close()

    def _update_preference_usage(self, category: str):
        """Update preference usage counter"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE preferences
            SET times_applied = times_applied + 1
            WHERE category = ?
        """, (category,))

        conn.commit()
        conn.close()

    def _save_pattern(self, pattern: Pattern, pattern_id: str):
        """Save pattern to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO patterns
            (pattern_id, pattern_type, description, occurrences, last_seen, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pattern_id,
            pattern.pattern_type,
            pattern.description,
            pattern.occurrences,
            pattern.last_seen.isoformat() if pattern.last_seen else None,
            json.dumps(pattern.metadata)
        ))

        conn.commit()
        conn.close()

    def _increment_command_frequency(self, command: str):
        """Increment command usage frequency"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO command_frequency (command, count, last_used)
            VALUES (?, 1, ?)
            ON CONFLICT(command) DO UPDATE SET
                count = count + 1,
                last_used = ?
        """, (command, datetime.now().isoformat(), datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def _get_command_frequency(self, command: str) -> int:
        """Get command usage frequency"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT count FROM command_frequency WHERE command = ?", (command,))
        row = cursor.fetchone()

        conn.close()

        return row[0] if row else 0

    def get_insights(self) -> Dict[str, Any]:
        """Get learning insights and statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total interactions
        cursor.execute("SELECT COUNT(*) FROM interactions")
        total_interactions = cursor.fetchone()[0]

        # Most common queries
        cursor.execute("""
            SELECT query, COUNT(*) as count
            FROM interactions
            GROUP BY query
            ORDER BY count DESC
            LIMIT 5
        """)
        common_queries = cursor.fetchall()

        # Model usage
        cursor.execute("""
            SELECT model_used, COUNT(*) as count
            FROM interactions
            GROUP BY model_used
            ORDER BY count DESC
        """)
        model_usage = cursor.fetchall()

        conn.close()

        return {
            "total_interactions": total_interactions,
            "preferences": {
                cat: {"value": pref.value, "confidence": pref.confidence, "times_applied": pref.times_applied}
                for cat, pref in self.preferences.items()
            },
            "patterns": {
                pid: {"type": pat.pattern_type, "occurrences": pat.occurrences}
                for pid, pat in self.patterns.items()
            },
            "common_queries": common_queries,
            "model_usage": model_usage
        }

    def suggest_optimizations(self) -> List[str]:
        """Suggest optimizations based on learned patterns"""
        suggestions = []

        # Check for frequent config queries
        if "frequent_config_queries" in self.patterns:
            occurrences = self.patterns["frequent_config_queries"].occurrences
            if occurrences > 10:
                suggestions.append(
                    "Consider caching config file locations for faster access"
                )

        # Check for code patterns
        if "code_focused" in self.patterns:
            occurrences = self.patterns["code_focused"].occurrences
            if occurrences > 5:
                suggestions.append(
                    "Consider keeping code-focused models loaded for better performance"
                )

        return suggestions

    # ===== Compatibility methods for ai_engine_v2.py =====

    def apply_preferences_to_response(self, response: str) -> str:
        """Alias for apply_preferences (for compatibility)"""
        return self.apply_preferences(response)

    def detect_preference_from_query(self, query: str, response: str = "") -> Optional[Dict]:
        """
        Detect preferences from query and response

        Returns dict of detected preferences or None
        """
        detected_prefs = self.detect_preferences_from_query(query)

        if detected_prefs:
            return {
                pref.category: pref.value
                for pref in detected_prefs
            }
        return None

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a specific preference value"""
        if key in self.preferences:
            return self.preferences[key].value
        return default

    def learn_preference(self, key: str, value: str, source: str = "explicit", confidence: float = 1.0):
        """
        Learn a preference explicitly

        Args:
            key: Preference category (e.g., "editor", "shell")
            value: Preference value (e.g., "nvim", "zsh")
            source: Source of learning
            confidence: Confidence level (0.0 - 1.0)
        """
        pref = Preference(
            category=key,
            value=value,
            confidence=confidence,
            learned_from=source,
            learned_at=datetime.now()
        )
        self._save_preference(pref)

    def get_stats(self) -> Dict[str, Any]:
        """Alias for get_insights (for compatibility)"""
        return self.get_insights()
