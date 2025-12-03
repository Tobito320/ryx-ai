"""
Ryx AI - Resolution Tracker

Track successful task resolutions to learn from experience.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
import json
import sqlite3
import hashlib
import logging

logger = logging.getLogger(__name__)


class ResolutionType(Enum):
    """Types of task resolutions"""
    CODE_FIX = "code_fix"           # Bug fix
    CODE_FEATURE = "code_feature"    # New feature
    CODE_REFACTOR = "code_refactor"  # Refactoring
    FILE_OP = "file_op"             # File operations
    SHELL_CMD = "shell_cmd"          # Shell commands
    CONFIG = "config"                # Configuration
    DOCS = "docs"                    # Documentation
    TEST = "test"                    # Test-related
    OTHER = "other"


@dataclass
class Resolution:
    """A successful task resolution"""
    id: str
    task_description: str
    resolution_type: ResolutionType
    
    # What was done
    files_modified: List[str] = field(default_factory=list)
    commands_run: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    
    # Context
    language: str = ""
    framework: str = ""
    error_pattern: Optional[str] = None
    
    # Result
    success: bool = True
    confidence: float = 0.8
    user_rating: Optional[int] = None  # 1-5 stars
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    duration_seconds: int = 0
    model_used: str = ""
    
    # Learning
    keywords: List[str] = field(default_factory=list)
    solution_pattern: str = ""


class ResolutionTracker:
    """
    Track successful task resolutions for learning.
    
    Features:
    - Store successful resolutions
    - Find similar past resolutions
    - Learn from patterns
    - Export learnings
    
    Usage:
    ```python
    tracker = ResolutionTracker()
    
    # Record a successful resolution
    tracker.record(Resolution(
        task_description="Fix login button",
        resolution_type=ResolutionType.CODE_FIX,
        files_modified=["auth.py"],
        tools_used=["apply_diff"]
    ))
    
    # Find similar resolutions
    similar = tracker.find_similar("authentication not working")
    ```
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path:
            self.db_path = db_path
        else:
            from core.paths import get_data_dir
            self.db_path = get_data_dir() / "resolutions.db"
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize the database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS resolutions (
                id TEXT PRIMARY KEY,
                task_description TEXT,
                resolution_type TEXT,
                files_modified TEXT,
                commands_run TEXT,
                tools_used TEXT,
                language TEXT,
                framework TEXT,
                error_pattern TEXT,
                success INTEGER,
                confidence REAL,
                user_rating INTEGER,
                timestamp TEXT,
                duration_seconds INTEGER,
                model_used TEXT,
                keywords TEXT,
                solution_pattern TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_type 
            ON resolutions(resolution_type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_success 
            ON resolutions(success)
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS resolution_fts 
            USING fts5(id, task_description, keywords, solution_pattern)
        """)
        conn.commit()
        conn.close()
    
    def record(self, resolution: Resolution) -> str:
        """Record a successful resolution"""
        if not resolution.id:
            resolution.id = self._generate_id(resolution)
        
        conn = sqlite3.connect(self.db_path)
        
        conn.execute("""
            INSERT OR REPLACE INTO resolutions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            resolution.id,
            resolution.task_description,
            resolution.resolution_type.value,
            json.dumps(resolution.files_modified),
            json.dumps(resolution.commands_run),
            json.dumps(resolution.tools_used),
            resolution.language,
            resolution.framework,
            resolution.error_pattern,
            1 if resolution.success else 0,
            resolution.confidence,
            resolution.user_rating,
            resolution.timestamp.isoformat(),
            resolution.duration_seconds,
            resolution.model_used,
            json.dumps(resolution.keywords),
            resolution.solution_pattern
        ))
        
        # Update FTS index
        conn.execute("""
            INSERT OR REPLACE INTO resolution_fts VALUES (?, ?, ?, ?)
        """, (
            resolution.id,
            resolution.task_description,
            ' '.join(resolution.keywords),
            resolution.solution_pattern
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Recorded resolution: {resolution.id}")
        return resolution.id
    
    def find_similar(
        self,
        query: str,
        limit: int = 5,
        min_confidence: float = 0.5
    ) -> List[Resolution]:
        """Find similar past resolutions"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # FTS search
        cursor = conn.execute("""
            SELECT r.* FROM resolutions r
            JOIN resolution_fts fts ON r.id = fts.id
            WHERE resolution_fts MATCH ?
            AND r.success = 1
            AND r.confidence >= ?
            ORDER BY rank
            LIMIT ?
        """, (query, min_confidence, limit))
        
        results = [self._row_to_resolution(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def find_by_type(
        self,
        resolution_type: ResolutionType,
        limit: int = 10
    ) -> List[Resolution]:
        """Find resolutions by type"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT * FROM resolutions 
            WHERE resolution_type = ? AND success = 1
            ORDER BY timestamp DESC
            LIMIT ?
        """, (resolution_type.value, limit))
        
        results = [self._row_to_resolution(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def find_by_error(
        self,
        error_pattern: str,
        limit: int = 5
    ) -> List[Resolution]:
        """Find resolutions for similar errors"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT * FROM resolutions 
            WHERE error_pattern LIKE ? AND success = 1
            ORDER BY confidence DESC, timestamp DESC
            LIMIT ?
        """, (f"%{error_pattern}%", limit))
        
        results = [self._row_to_resolution(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def rate_resolution(self, resolution_id: str, rating: int) -> bool:
        """Add user rating to a resolution"""
        if rating < 1 or rating > 5:
            return False
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE resolutions SET user_rating = ? WHERE id = ?
        """, (rating, resolution_id))
        conn.commit()
        
        updated = conn.total_changes > 0
        conn.close()
        
        return updated
    
    def get_stats(self) -> Dict[str, Any]:
        """Get resolution statistics"""
        conn = sqlite3.connect(self.db_path)
        
        # Total counts
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                AVG(confidence) as avg_confidence,
                AVG(user_rating) as avg_rating
            FROM resolutions
        """)
        row = cursor.fetchone()
        
        total = row[0] if row else 0
        successful = row[1] if row else 0
        avg_confidence = row[2] if row else 0
        avg_rating = row[3] if row else 0
        
        # By type
        cursor = conn.execute("""
            SELECT resolution_type, COUNT(*) 
            FROM resolutions 
            GROUP BY resolution_type
        """)
        by_type = dict(cursor.fetchall())
        
        # By language
        cursor = conn.execute("""
            SELECT language, COUNT(*) 
            FROM resolutions 
            WHERE language != ''
            GROUP BY language
        """)
        by_language = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_resolutions": total,
            "successful": successful,
            "success_rate": successful / total if total > 0 else 0,
            "avg_confidence": round(avg_confidence or 0, 2),
            "avg_user_rating": round(avg_rating or 0, 1),
            "by_type": by_type,
            "by_language": by_language
        }
    
    def get_top_patterns(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most common successful patterns"""
        conn = sqlite3.connect(self.db_path)
        
        cursor = conn.execute("""
            SELECT 
                solution_pattern,
                COUNT(*) as count,
                AVG(confidence) as avg_confidence,
                GROUP_CONCAT(DISTINCT tools_used) as tools
            FROM resolutions
            WHERE success = 1 AND solution_pattern != ''
            GROUP BY solution_pattern
            ORDER BY count DESC, avg_confidence DESC
            LIMIT ?
        """, (limit,))
        
        patterns = []
        for row in cursor.fetchall():
            patterns.append({
                "pattern": row[0],
                "count": row[1],
                "confidence": round(row[2], 2),
                "tools": row[3].split(',') if row[3] else []
            })
        
        conn.close()
        return patterns
    
    def _generate_id(self, resolution: Resolution) -> str:
        """Generate unique ID for resolution"""
        content = f"{resolution.task_description}{resolution.timestamp.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]
    
    def _row_to_resolution(self, row: sqlite3.Row) -> Resolution:
        """Convert database row to Resolution"""
        return Resolution(
            id=row["id"],
            task_description=row["task_description"],
            resolution_type=ResolutionType(row["resolution_type"]),
            files_modified=json.loads(row["files_modified"] or "[]"),
            commands_run=json.loads(row["commands_run"] or "[]"),
            tools_used=json.loads(row["tools_used"] or "[]"),
            language=row["language"],
            framework=row["framework"],
            error_pattern=row["error_pattern"],
            success=bool(row["success"]),
            confidence=row["confidence"],
            user_rating=row["user_rating"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            duration_seconds=row["duration_seconds"],
            model_used=row["model_used"],
            keywords=json.loads(row["keywords"] or "[]"),
            solution_pattern=row["solution_pattern"]
        )
