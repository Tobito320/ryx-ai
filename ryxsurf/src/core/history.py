"""
RyxSurf History Manager

SQLite-based browsing history with:
- URL tracking with timestamps
- Visit counts
- URL bar autocomplete suggestions
- History search
"""

import sqlite3
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager
import threading


@dataclass
class HistoryEntry:
    """A single history entry"""
    id: int
    url: str
    title: str
    visit_count: int
    last_visit: datetime
    first_visit: datetime


class HistoryManager:
    """
    Manages browsing history in SQLite.
    
    Thread-safe with connection pooling.
    Stored in ~/.config/ryxsurf/history.db
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / ".config" / "ryxsurf" / "history.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()
        
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        """Get a cursor with auto-commit"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def _init_db(self):
        """Initialize the database schema"""
        with self._cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    title TEXT DEFAULT '',
                    visit_count INTEGER DEFAULT 1,
                    first_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index for fast URL lookups and autocomplete
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_url 
                ON history(url)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_last_visit 
                ON history(last_visit DESC)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_visit_count 
                ON history(visit_count DESC)
            """)
            
    def add_visit(self, url: str, title: str = ""):
        """Record a URL visit"""
        if not url or url.startswith("about:") or url.startswith("data:"):
            return
            
        with self._cursor() as cur:
            # Try to update existing entry
            cur.execute("""
                UPDATE history 
                SET visit_count = visit_count + 1,
                    last_visit = CURRENT_TIMESTAMP,
                    title = CASE WHEN ? != '' THEN ? ELSE title END
                WHERE url = ?
            """, (title, title, url))
            
            # If no update, insert new
            if cur.rowcount == 0:
                cur.execute("""
                    INSERT INTO history (url, title, visit_count, first_visit, last_visit)
                    VALUES (?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (url, title))
                
    def update_title(self, url: str, title: str):
        """Update title for a URL"""
        if not title:
            return
            
        with self._cursor() as cur:
            cur.execute("""
                UPDATE history SET title = ? WHERE url = ?
            """, (title, url))
            
    def get_suggestions(self, query: str, limit: int = 10) -> List[HistoryEntry]:
        """
        Get autocomplete suggestions for URL bar.
        
        Prioritizes:
        1. Frequent visits
        2. Recent visits
        3. URL/title match
        """
        if not query:
            return self.get_recent(limit)
            
        pattern = f"%{query}%"
        
        with self._cursor() as cur:
            cur.execute("""
                SELECT id, url, title, visit_count, first_visit, last_visit
                FROM history
                WHERE url LIKE ? OR title LIKE ?
                ORDER BY 
                    visit_count DESC,
                    last_visit DESC
                LIMIT ?
            """, (pattern, pattern, limit))
            
            return [self._row_to_entry(row) for row in cur.fetchall()]
            
    def get_recent(self, limit: int = 20) -> List[HistoryEntry]:
        """Get most recent history entries"""
        with self._cursor() as cur:
            cur.execute("""
                SELECT id, url, title, visit_count, first_visit, last_visit
                FROM history
                ORDER BY last_visit DESC
                LIMIT ?
            """, (limit,))
            
            return [self._row_to_entry(row) for row in cur.fetchall()]
            
    def get_frequent(self, limit: int = 20) -> List[HistoryEntry]:
        """Get most frequently visited URLs"""
        with self._cursor() as cur:
            cur.execute("""
                SELECT id, url, title, visit_count, first_visit, last_visit
                FROM history
                ORDER BY visit_count DESC
                LIMIT ?
            """, (limit,))
            
            return [self._row_to_entry(row) for row in cur.fetchall()]
            
    def search(self, query: str, limit: int = 50) -> List[HistoryEntry]:
        """Search history by URL or title"""
        pattern = f"%{query}%"
        
        with self._cursor() as cur:
            cur.execute("""
                SELECT id, url, title, visit_count, first_visit, last_visit
                FROM history
                WHERE url LIKE ? OR title LIKE ?
                ORDER BY last_visit DESC
                LIMIT ?
            """, (pattern, pattern, limit))
            
            return [self._row_to_entry(row) for row in cur.fetchall()]
            
    def delete_entry(self, url: str):
        """Delete a single history entry"""
        with self._cursor() as cur:
            cur.execute("DELETE FROM history WHERE url = ?", (url,))
            
    def delete_range(self, start: datetime, end: datetime):
        """Delete history entries in a time range"""
        with self._cursor() as cur:
            cur.execute("""
                DELETE FROM history 
                WHERE last_visit BETWEEN ? AND ?
            """, (start.isoformat(), end.isoformat()))
            
    def clear_all(self):
        """Clear all history"""
        with self._cursor() as cur:
            cur.execute("DELETE FROM history")
            
    def get_stats(self) -> dict:
        """Get history statistics"""
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) as count, SUM(visit_count) as visits FROM history")
            row = cur.fetchone()
            return {
                "total_urls": row["count"] or 0,
                "total_visits": row["visits"] or 0
            }
            
    def _row_to_entry(self, row: sqlite3.Row) -> HistoryEntry:
        """Convert database row to HistoryEntry"""
        return HistoryEntry(
            id=row["id"],
            url=row["url"],
            title=row["title"] or "",
            visit_count=row["visit_count"],
            first_visit=datetime.fromisoformat(row["first_visit"]) if row["first_visit"] else datetime.now(),
            last_visit=datetime.fromisoformat(row["last_visit"]) if row["last_visit"] else datetime.now()
        )
        
    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
