"""
Ryx AI - Metrics Collector
Collects and reports performance metrics
"""

import os
import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class QueryMetric:
    """Metric for a single query"""
    timestamp: str
    query_type: str  # 'cache_hit', 'model_query', 'command_exec'
    latency_ms: int
    model_used: Optional[str]
    success: bool
    memory_mb: Optional[float] = None


class MetricsCollector:
    """
    Collects and reports performance metrics

    Features:
    - Response time tracking for every query
    - Cache hit rate monitoring
    - Memory usage (RAM/VRAM) tracking
    - Model switching frequency
    - Export metrics to JSON
    - Terminal display of stats
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / "ryx-ai" / "data" / "metrics.db"
        self._init_db()

        # In-memory counters for fast access
        self._session_metrics = {
            'queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_latency_ms': 0,
            'errors': 0,
            'model_switches': 0,
            'session_start': datetime.now().isoformat()
        }
        self._current_model: Optional[str] = None

    def _init_db(self):
        """Initialize metrics database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Query metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query_type TEXT NOT NULL,
                latency_ms INTEGER NOT NULL,
                model_used TEXT,
                success INTEGER NOT NULL,
                memory_mb REAL
            )
        """)

        # Hourly aggregates for efficient querying
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hourly_aggregates (
                hour TEXT PRIMARY KEY,
                total_queries INTEGER DEFAULT 0,
                cache_hits INTEGER DEFAULT 0,
                avg_latency_ms REAL DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                model_switches INTEGER DEFAULT 0
            )
        """)

        # Resource snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resource_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ram_percent REAL,
                ram_used_mb REAL,
                vram_used_mb REAL,
                cpu_percent REAL
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_timestamp
            ON query_metrics(timestamp)
        """)

        conn.commit()
        conn.close()

    def record_query(self,
                     query_type: str,
                     latency_ms: int,
                     success: bool,
                     model_used: Optional[str] = None):
        """Record a query metric"""
        # Update session counters
        self._session_metrics['queries'] += 1
        self._session_metrics['total_latency_ms'] += latency_ms

        if query_type == 'cache_hit':
            self._session_metrics['cache_hits'] += 1
        elif query_type == 'model_query':
            self._session_metrics['cache_misses'] += 1

        if not success:
            self._session_metrics['errors'] += 1

        # Track model switches
        if model_used and model_used != self._current_model:
            if self._current_model is not None:
                self._session_metrics['model_switches'] += 1
            self._current_model = model_used

        # Get memory usage
        memory_mb = self._get_memory_usage()

        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO query_metrics
            (timestamp, query_type, latency_ms, model_used, success, memory_mb)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            query_type,
            latency_ms,
            model_used,
            1 if success else 0,
            memory_mb
        ))

        conn.commit()
        conn.close()

        # Update hourly aggregate
        self._update_hourly_aggregate(query_type, latency_ms, success)

    def _update_hourly_aggregate(self, query_type: str, latency_ms: int, success: bool):
        """Update hourly aggregate"""
        hour = datetime.now().strftime("%Y-%m-%d %H:00")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get or create aggregate
        cursor.execute("""
            INSERT OR IGNORE INTO hourly_aggregates (hour)
            VALUES (?)
        """, (hour,))

        # Update aggregate
        cursor.execute("""
            UPDATE hourly_aggregates
            SET total_queries = total_queries + 1,
                cache_hits = cache_hits + ?,
                avg_latency_ms = (avg_latency_ms * total_queries + ?) / (total_queries + 1),
                error_count = error_count + ?
            WHERE hour = ?
        """, (
            1 if query_type == 'cache_hit' else 0,
            latency_ms,
            0 if success else 1,
            hour
        ))

        conn.commit()
        conn.close()

    def record_resource_snapshot(self):
        """Record current resource usage"""
        try:
            import psutil

            # RAM
            memory = psutil.virtual_memory()
            ram_percent = memory.percent
            ram_used_mb = memory.used / (1024 * 1024)

            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # VRAM (AMD GPU)
            vram_used_mb = self._get_vram_usage()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO resource_snapshots
                (timestamp, ram_percent, ram_used_mb, vram_used_mb, cpu_percent)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                ram_percent,
                ram_used_mb,
                vram_used_mb,
                cpu_percent
            ))

            conn.commit()
            conn.close()
        except ImportError:
            pass  # psutil not installed
        except Exception:
            pass  # Ignore errors in monitoring

    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except:
            return None

    def _get_vram_usage(self) -> Optional[float]:
        """Get VRAM usage for AMD GPU"""
        try:
            import subprocess
            result = subprocess.run(
                ['rocm-smi', '--showmemuse'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Parse output to get VRAM usage
                for line in result.stdout.split('\n'):
                    if 'GPU Memory' in line:
                        # Extract MB value
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if 'MB' in part or part.isdigit():
                                try:
                                    return float(parts[i-1] if 'MB' in part else part)
                                except:
                                    pass
            return None
        except:
            return None

    def get_session_metrics(self) -> Dict[str, Any]:
        """Get current session metrics"""
        queries = self._session_metrics['queries']

        return {
            'queries': queries,
            'cache_hits': self._session_metrics['cache_hits'],
            'cache_misses': self._session_metrics['cache_misses'],
            'cache_hit_rate': (self._session_metrics['cache_hits'] / queries * 100) if queries > 0 else 0,
            'avg_latency_ms': (self._session_metrics['total_latency_ms'] / queries) if queries > 0 else 0,
            'errors': self._session_metrics['errors'],
            'error_rate': (self._session_metrics['errors'] / queries * 100) if queries > 0 else 0,
            'model_switches': self._session_metrics['model_switches'],
            'current_model': self._current_model,
            'session_start': self._session_metrics['session_start']
        }

    def get_all_time_metrics(self) -> Dict[str, Any]:
        """Get all-time metrics from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        metrics = {}

        # Total queries
        cursor.execute("SELECT COUNT(*) FROM query_metrics")
        metrics['total_queries'] = cursor.fetchone()[0]

        # Cache hit rate
        cursor.execute("SELECT COUNT(*) FROM query_metrics WHERE query_type = 'cache_hit'")
        cache_hits = cursor.fetchone()[0]
        metrics['cache_hits'] = cache_hits
        metrics['cache_hit_rate'] = (cache_hits / metrics['total_queries'] * 100) if metrics['total_queries'] > 0 else 0

        # Average latency
        cursor.execute("SELECT AVG(latency_ms) FROM query_metrics WHERE success = 1")
        avg = cursor.fetchone()[0]
        metrics['avg_latency_ms'] = round(avg, 2) if avg else 0

        # Cached vs uncached latency
        cursor.execute("SELECT AVG(latency_ms) FROM query_metrics WHERE query_type = 'cache_hit'")
        cached = cursor.fetchone()[0]
        metrics['cached_avg_latency_ms'] = round(cached, 2) if cached else 0

        cursor.execute("SELECT AVG(latency_ms) FROM query_metrics WHERE query_type = 'model_query'")
        uncached = cursor.fetchone()[0]
        metrics['uncached_avg_latency_ms'] = round(uncached, 2) if uncached else 0

        # Error rate
        cursor.execute("SELECT COUNT(*) FROM query_metrics WHERE success = 0")
        errors = cursor.fetchone()[0]
        metrics['errors'] = errors
        metrics['error_rate'] = (errors / metrics['total_queries'] * 100) if metrics['total_queries'] > 0 else 0

        # Model usage
        cursor.execute("""
            SELECT model_used, COUNT(*) as count
            FROM query_metrics
            WHERE model_used IS NOT NULL
            GROUP BY model_used
            ORDER BY count DESC
        """)
        metrics['model_usage'] = {row[0]: row[1] for row in cursor.fetchall()}

        # Percentile latencies
        cursor.execute("""
            SELECT latency_ms FROM query_metrics
            WHERE success = 1
            ORDER BY latency_ms
        """)
        latencies = [row[0] for row in cursor.fetchall()]

        if latencies:
            metrics['p50_latency_ms'] = latencies[len(latencies) // 2]
            metrics['p95_latency_ms'] = latencies[int(len(latencies) * 0.95)]
            metrics['p99_latency_ms'] = latencies[int(len(latencies) * 0.99)]
        else:
            metrics['p50_latency_ms'] = 0
            metrics['p95_latency_ms'] = 0
            metrics['p99_latency_ms'] = 0

        conn.close()
        return metrics

    def get_recent_resource_usage(self, minutes: int = 60) -> Dict[str, Any]:
        """Get resource usage for last N minutes"""
        cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT AVG(ram_percent), AVG(ram_used_mb), AVG(vram_used_mb), AVG(cpu_percent)
            FROM resource_snapshots
            WHERE timestamp > ?
        """, (cutoff,))

        row = cursor.fetchone()

        conn.close()

        if row and row[0]:
            return {
                'avg_ram_percent': round(row[0], 1),
                'avg_ram_mb': round(row[1], 1),
                'avg_vram_mb': round(row[2], 1) if row[2] else None,
                'avg_cpu_percent': round(row[3], 1)
            }
        return {}

    def get_hourly_trends(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly trends"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM hourly_aggregates
            ORDER BY hour DESC
            LIMIT ?
        """, (hours,))

        trends = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return trends

    def export_metrics(self, output_path: Path) -> int:
        """Export all metrics to JSON"""
        data = {
            'exported_at': datetime.now().isoformat(),
            'all_time': self.get_all_time_metrics(),
            'session': self.get_session_metrics(),
            'resource_usage': self.get_recent_resource_usage(),
            'hourly_trends': self.get_hourly_trends()
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        return len(json.dumps(data))

    def cleanup_old_metrics(self, days: int = 30) -> int:
        """Delete metrics older than specified days"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM query_metrics WHERE timestamp < ?", (cutoff,))
        deleted = cursor.rowcount

        cursor.execute("DELETE FROM resource_snapshots WHERE timestamp < ?", (cutoff,))
        deleted += cursor.rowcount

        conn.commit()
        conn.close()

        return deleted

    def format_metrics_for_display(self) -> str:
        """Format metrics for terminal display"""
        all_time = self.get_all_time_metrics()
        session = self.get_session_metrics()

        lines = []
        lines.append("")
        lines.append("\033[1;36m╭──────────────────────────────────────────╮\033[0m")
        lines.append("\033[1;36m│  Performance Metrics                     │\033[0m")
        lines.append("\033[1;36m╰──────────────────────────────────────────╯\033[0m")
        lines.append("")

        # Session metrics
        lines.append("\033[1;33mThis Session:\033[0m")
        lines.append(f"  Queries: {session['queries']}")
        lines.append(f"  Cache Hit Rate: {session['cache_hit_rate']:.1f}%")
        lines.append(f"  Avg Latency: {session['avg_latency_ms']:.1f}ms")
        if session['current_model']:
            lines.append(f"  Current Model: {session['current_model']}")
        lines.append("")

        # All-time metrics
        lines.append("\033[1;33mAll Time:\033[0m")
        lines.append(f"  Total Queries: {all_time['total_queries']}")
        lines.append(f"  Cache Hit Rate: {all_time['cache_hit_rate']:.1f}%")
        lines.append(f"  Avg Latency: {all_time['avg_latency_ms']:.1f}ms")
        lines.append("")

        # Latency percentiles
        lines.append("\033[1;33mLatency Percentiles:\033[0m")
        lines.append(f"  P50: {all_time['p50_latency_ms']}ms")
        lines.append(f"  P95: {all_time['p95_latency_ms']}ms")
        lines.append(f"  P99: {all_time['p99_latency_ms']}ms")
        lines.append("")

        # Cache vs uncached
        lines.append("\033[1;33mCache Performance:\033[0m")
        lines.append(f"  Cached: {all_time['cached_avg_latency_ms']:.1f}ms avg")
        lines.append(f"  Uncached: {all_time['uncached_avg_latency_ms']:.1f}ms avg")

        speedup = all_time['uncached_avg_latency_ms'] / all_time['cached_avg_latency_ms'] if all_time['cached_avg_latency_ms'] > 0 else 0
        if speedup > 1:
            lines.append(f"  \033[1;32mSpeedup: {speedup:.1f}x\033[0m")
        lines.append("")

        # Model usage
        if all_time['model_usage']:
            lines.append("\033[1;33mModel Usage:\033[0m")
            for model, count in all_time['model_usage'].items():
                lines.append(f"  {model}: {count} queries")
            lines.append("")

        return "\n".join(lines)


# Global metrics instance for easy access
_metrics_instance: Optional[MetricsCollector] = None

def get_metrics() -> MetricsCollector:
    """Get global metrics instance"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance
