"""
Ryx AI - Meta Learner
Learns user preferences, patterns, and continuously improves system behavior
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Preference:
    """A learned user preference"""
    key: str
    value: Any
    confidence: float  # 0.0-1.0
    learned_from: str  # "explicit", "pattern", "correction"
    timestamp: str
    usage_count: int = 0


@dataclass
class Pattern:
    """A learned behavioral pattern"""
    pattern_type: str
    trigger: str
    expected_behavior: str
    confidence: float
    occurrences: int


class MetaLearner:
    """
    Learns from user interactions to improve system behavior:
    - Explicit preferences (user says "use nvim")
    - Pattern recognition (user always does X after Y)
    - Corrections (user fixes AI suggestions)
    - Model performance per task type
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.home() / "ryx-ai"
        self.db_path = self.project_root / "data" / "meta_learning.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache
        self.preferences: Dict[str, Preference] = {}
        self.patterns: List[Pattern] = []
        self.interaction_history: List[Dict] = []
        
        self._init_database()
        self._load_from_database()
    
    def _init_database(self):
        """Initialize meta-learning database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                confidence REAL,
                learned_from TEXT,
                timestamp TEXT,
                usage_count INTEGER DEFAULT 0
            )
        ''')
        
        # Patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT,
                trigger TEXT,
                expected_behavior TEXT,
                confidence REAL,
                occurrences INTEGER
            )
        ''')
        
        # Interaction history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                query TEXT,
                model_used TEXT,
                tier_used TEXT,
                latency_ms INTEGER,
                success INTEGER,
                user_satisfied INTEGER
            )
        ''')
        
        # Model performance tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_performance (
                model_name TEXT,
                task_type TEXT,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                avg_latency_ms REAL,
                PRIMARY KEY (model_name, task_type)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_from_database(self):
        """Load learned data from database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Load preferences
        cursor.execute('SELECT * FROM preferences')
        for row in cursor.fetchall():
            key, value_json, confidence, learned_from, timestamp, usage_count = row
            try:
                value = json.loads(value_json)
            except:
                value = value_json
            
            self.preferences[key] = Preference(
                key=key,
                value=value,
                confidence=confidence,
                learned_from=learned_from,
                timestamp=timestamp,
                usage_count=usage_count
            )
        
        # Load patterns
        cursor.execute('SELECT * FROM patterns')
        for row in cursor.fetchall():
            _, pattern_type, trigger, expected_behavior, confidence, occurrences = row
            self.patterns.append(Pattern(
                pattern_type=pattern_type,
                trigger=trigger,
                expected_behavior=expected_behavior,
                confidence=confidence,
                occurrences=occurrences
            ))
        
        conn.close()
        logger.info(f"Loaded {len(self.preferences)} preferences and {len(self.patterns)} patterns")
    
    def learn_preference(self, key: str, value: Any, source: str = "explicit", confidence: float = 1.0):
        """
        Learn a user preference
        
        Args:
            key: Preference key (e.g., "editor", "shell", "theme")
            value: Preference value (e.g., "nvim", "bash", "dracula")
            source: How we learned it ("explicit", "pattern", "correction")
            confidence: How confident we are (0.0-1.0)
        """
        pref = Preference(
            key=key,
            value=value,
            confidence=confidence,
            learned_from=source,
            timestamp=datetime.now().isoformat(),
            usage_count=0
        )
        
        self.preferences[key] = pref
        
        # Save to database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO preferences
            (key, value, confidence, learned_from, timestamp, usage_count)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            key,
            json.dumps(value),
            confidence,
            source,
            pref.timestamp,
            pref.usage_count
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Learned preference: {key}={value} (confidence: {confidence:.2f}, source: {source})")
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a learned preference"""
        if key in self.preferences:
            pref = self.preferences[key]
            
            # Increment usage count
            pref.usage_count += 1
            
            # Update in database
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE preferences SET usage_count = ? WHERE key = ?',
                (pref.usage_count, key)
            )
            conn.commit()
            conn.close()
            
            return pref.value
        
        return default
    
    def detect_preference_from_query(self, query: str, response: str = None) -> List[Tuple[str, Any]]:
        """
        Detect preferences from user query

        Examples:
        - "use nvim not nano" -> ("editor", "nvim")
        - "I prefer bash over zsh" -> ("shell", "bash")
        - "always use dark theme" -> ("theme", "dark")
        """
        detected = []
        query_lower = query.lower()

        # Editor preferences
        if 'nvim' in query_lower or 'neovim' in query_lower:
            detected.append(('editor', 'nvim'))
        elif 'vim' in query_lower and 'nvim' not in query_lower:
            detected.append(('editor', 'vim'))
        elif 'nano' in query_lower and ('not' in query_lower or "don't" in query_lower):
            detected.append(('editor', 'nvim'))  # User doesn't want nano
        
        # Shell preferences
        if 'shell' in query_lower or 'terminal' in query_lower:
            if 'bash' in query_lower:
                detected.append(('shell', 'bash'))
            elif 'zsh' in query_lower:
                detected.append(('shell', 'zsh'))
            elif 'fish' in query_lower:
                detected.append(('shell', 'fish'))
        
        # Theme preferences
        if 'theme' in query_lower or 'color' in query_lower:
            if 'dark' in query_lower:
                detected.append(('theme', 'dark'))
            elif 'light' in query_lower:
                detected.append(('theme', 'light'))
        
        # File manager preferences
        if 'file manager' in query_lower or 'files' in query_lower:
            if 'ranger' in query_lower:
                detected.append(('file_manager', 'ranger'))
            elif 'thunar' in query_lower:
                detected.append(('file_manager', 'thunar'))
        
        # Learn detected preferences
        for key, value in detected:
            self.learn_preference(key, value, source="pattern", confidence=0.8)
        
        return detected
    
    def learn_pattern(self, pattern_type: str, trigger: str, behavior: str, confidence: float = 0.5):
        """
        Learn a behavioral pattern
        
        Args:
            pattern_type: Type of pattern ("sequence", "correction", "preference")
            trigger: What triggers the pattern
            behavior: Expected behavior
            confidence: Initial confidence
        """
        # Check if pattern exists
        for pattern in self.patterns:
            if pattern.trigger == trigger and pattern.pattern_type == pattern_type:
                # Strengthen existing pattern
                pattern.occurrences += 1
                pattern.confidence = min(1.0, pattern.confidence + 0.1)
                self._save_pattern(pattern)
                return
        
        # New pattern
        pattern = Pattern(
            pattern_type=pattern_type,
            trigger=trigger,
            expected_behavior=behavior,
            confidence=confidence,
            occurrences=1
        )
        
        self.patterns.append(pattern)
        self._save_pattern(pattern)
        
        logger.info(f"Learned pattern: {pattern_type} - {trigger} -> {behavior}")
    
    def _save_pattern(self, pattern: Pattern):
        """Save pattern to database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO patterns
            (pattern_type, trigger, expected_behavior, confidence, occurrences)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            pattern.pattern_type,
            pattern.trigger,
            pattern.expected_behavior,
            pattern.confidence,
            pattern.occurrences
        ))
        
        conn.commit()
        conn.close()
    
    def record_interaction(self, 
                          query: str,
                          model_used: str,
                          tier_used: str,
                          latency_ms: int,
                          success: bool,
                          user_satisfied: Optional[bool] = None):
        """Record an interaction for learning"""
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'model_used': model_used,
            'tier_used': tier_used,
            'latency_ms': latency_ms,
            'success': success,
            'user_satisfied': user_satisfied
        }
        
        self.interaction_history.append(interaction)
        
        # Keep last 1000 in memory
        if len(self.interaction_history) > 1000:
            self.interaction_history = self.interaction_history[-1000:]
        
        # Save to database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO interactions
            (timestamp, query, model_used, tier_used, latency_ms, success, user_satisfied)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            interaction['timestamp'],
            query,
            model_used,
            tier_used,
            latency_ms,
            1 if success else 0,
            1 if user_satisfied else (0 if user_satisfied is False else None)
        ))
        
        conn.commit()
        conn.close()
        
        # Detect preferences from query
        self.detect_preference_from_query(query)
    
    def update_model_performance(self, model_name: str, task_type: str, 
                                 success: bool, latency_ms: int):
        """Update model performance statistics"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get current stats
        cursor.execute('''
            SELECT success_count, failure_count, avg_latency_ms
            FROM model_performance
            WHERE model_name = ? AND task_type = ?
        ''', (model_name, task_type))
        
        row = cursor.fetchone()
        
        if row:
            success_count, failure_count, avg_latency = row
            
            if success:
                success_count += 1
            else:
                failure_count += 1
            
            # Update average latency
            total_count = success_count + failure_count
            avg_latency = (avg_latency * (total_count - 1) + latency_ms) / total_count
            
            cursor.execute('''
                UPDATE model_performance
                SET success_count = ?, failure_count = ?, avg_latency_ms = ?
                WHERE model_name = ? AND task_type = ?
            ''', (success_count, failure_count, avg_latency, model_name, task_type))
        else:
            cursor.execute('''
                INSERT INTO model_performance
                (model_name, task_type, success_count, failure_count, avg_latency_ms)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                model_name,
                task_type,
                1 if success else 0,
                0 if success else 1,
                latency_ms
            ))
        
        conn.commit()
        conn.close()
    
    def get_model_recommendations(self, task_type: str) -> List[Tuple[str, float]]:
        """Get recommended models for a task type based on performance"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT model_name, 
                   CAST(success_count AS FLOAT) / (success_count + failure_count) as success_rate,
                   avg_latency_ms
            FROM model_performance
            WHERE task_type = ? AND (success_count + failure_count) >= 3
            ORDER BY success_rate DESC, avg_latency_ms ASC
        ''', (task_type,))
        
        results = [(row[0], row[1]) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_stats(self) -> Dict:
        """Get meta-learning statistics"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Interaction stats
        cursor.execute('SELECT COUNT(*) FROM interactions')
        total_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM interactions WHERE success = 1')
        successful_interactions = cursor.fetchone()[0]
        
        # Most used preferences
        top_prefs = sorted(
            self.preferences.values(),
            key=lambda p: p.usage_count,
            reverse=True
        )[:5]
        
        conn.close()
        
        return {
            'total_interactions': total_interactions,
            'successful_interactions': successful_interactions,
            'success_rate': successful_interactions / total_interactions if total_interactions > 0 else 0,
            'learned_preferences': len(self.preferences),
            'learned_patterns': len(self.patterns),
            'top_preferences': [
                {'key': p.key, 'value': p.value, 'usage_count': p.usage_count}
                for p in top_prefs
            ]
        }
    
    def apply_preferences_to_response(self, response: str) -> str:
        """Apply learned preferences to modify a response"""
        modified = response
        
        # Replace editor mentions
        editor = self.get_preference('editor')
        if editor:
            # Replace common editor mentions
            modified = modified.replace('nano ', f'{editor} ')
            modified = modified.replace('nano\n', f'{editor}\n')
            modified = modified.replace('vim ', f'{editor} ')
            
        return modified
