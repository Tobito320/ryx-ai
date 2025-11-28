#!/usr/bin/env python3
"""
Ryx AI - Database Maintenance
Comprehensive database maintenance and optimization tool
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any

from core.paths import get_data_dir


class DatabaseMaintenance:
    """Database maintenance and optimization"""

    def __init__(self) -> None:
        """Initialize database maintenance tool"""
        self.data_dir = get_data_dir()
        self.databases = {
            'rag': self.data_dir / 'rag_knowledge.db',
            'metrics': self.data_dir / 'metrics.db',
            'meta_learning': self.data_dir / 'meta_learning.db',
            'health_monitor': self.data_dir / 'health_monitor.db',
            'task_manager': self.data_dir / 'task_manager.db'
        }

    def analyze_all_databases(self) -> Dict[str, Any]:
        """Analyze all databases"""
        print("\n\033[1;36m" + "=" * 60 + "\033[0m")
        print("\033[1;36mRyx AI - Database Analysis\033[0m")
        print("\033[1;36m" + "=" * 60 + "\033[0m\n")

        analysis = {}

        for name, db_path in self.databases.items():
            if not db_path.exists():
                print(f"\033[1;33m⚠\033[0m {name}: Not initialized")
                continue

            print(f"\n\033[1;33mAnalyzing {name}...\033[0m")
            stats = self._analyze_database(db_path)
            analysis[name] = stats

            print(f"  Size: {stats['size_mb']:.2f} MB")
            print(f"  Tables: {len(stats['tables'])}")
            print(f"  Total rows: {stats['total_rows']:,}")

            if stats.get('fragmentation_pct', 0) > 10:
                print(f"  \033[1;33m⚠\033[0m Fragmentation: {stats['fragmentation_pct']:.1f}%")
            else:
                print(f"  \033[1;32m✓\033[0m Fragmentation: {stats['fragmentation_pct']:.1f}%")

        print("\n\033[1;36m" + "=" * 60 + "\033[0m\n")

        return analysis

    def _analyze_database(self, db_path: Path) -> Dict[str, Any]:
        """Analyze a single database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        stats = {
            'size_mb': db_path.stat().st_size / (1024 * 1024),
            'tables': [],
            'total_rows': 0,
            'fragmentation_pct': 0.0
        }

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        stats['tables'] = tables

        # Count rows in each table
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                stats['total_rows'] += count
            except sqlite3.Error:
                pass

        # Check fragmentation (page count vs optimal)
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]

        cursor.execute("PRAGMA freelist_count")
        freelist_count = cursor.fetchone()[0]

        if page_count > 0:
            stats['fragmentation_pct'] = (freelist_count / page_count) * 100

        conn.close()

        return stats

    def optimize_all_databases(self) -> Dict[str, Any]:
        """Optimize all databases"""
        print("\n\033[1;36m" + "=" * 60 + "\033[0m")
        print("\033[1;36mRyx AI - Database Optimization\033[0m")
        print("\033[1;36m" + "=" * 60 + "\033[0m\n")

        results = {}

        for name, db_path in self.databases.items():
            if not db_path.exists():
                continue

            print(f"\n\033[1;33mOptimizing {name}...\033[0m")

            size_before = db_path.stat().st_size / (1024 * 1024)
            result = self._optimize_database(db_path)
            size_after = db_path.stat().st_size / (1024 * 1024)

            result['size_before_mb'] = size_before
            result['size_after_mb'] = size_after
            result['space_saved_mb'] = size_before - size_after

            results[name] = result

            print(f"  \033[1;32m✓\033[0m Optimized")
            print(f"  Before: {size_before:.2f} MB")
            print(f"  After: {size_after:.2f} MB")
            if result['space_saved_mb'] > 0:
                print(f"  \033[1;32m→\033[0m Saved: {result['space_saved_mb']:.2f} MB")

        total_saved = sum(r['space_saved_mb'] for r in results.values())
        print(f"\n\033[1;32m✓\033[0m Total space saved: {total_saved:.2f} MB")

        print("\n\033[1;36m" + "=" * 60 + "\033[0m\n")

        return results

    def _optimize_database(self, db_path: Path) -> Dict[str, Any]:
        """Optimize a single database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        result = {
            'vacuum': False,
            'analyze': False,
            'reindex': False
        }

        try:
            # VACUUM - Rebuild database, reclaim space
            cursor.execute("VACUUM")
            result['vacuum'] = True

            # ANALYZE - Update query planner statistics
            cursor.execute("ANALYZE")
            result['analyze'] = True

            # REINDEX - Rebuild all indexes
            cursor.execute("REINDEX")
            result['reindex'] = True

            conn.commit()

        except sqlite3.Error as e:
            print(f"  \033[1;31m✗\033[0m Error: {e}")

        finally:
            conn.close()

        return result

    def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """Clean up old data from databases"""
        print("\n\033[1;36m" + "=" * 60 + "\033[0m")
        print(f"\033[1;36mRyx AI - Cleanup Data Older Than {days} Days\033[0m")
        print("\033[1;36m" + "=" * 60 + "\033[0m\n")

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        results = {}

        # Clean RAG cache
        rag_db = self.data_dir / 'rag_knowledge.db'
        if rag_db.exists():
            print("\033[1;33mCleaning RAG cache...\033[0m")
            deleted = self._cleanup_rag_cache(rag_db, cutoff)
            results['rag_cache'] = deleted
            print(f"  \033[1;32m✓\033[0m Removed {deleted} old entries")

        # Clean metrics
        metrics_db = self.data_dir / 'metrics.db'
        if metrics_db.exists():
            print("\n\033[1;33mCleaning metrics...\033[0m")
            deleted = self._cleanup_metrics(metrics_db, cutoff)
            results['metrics'] = deleted
            print(f"  \033[1;32m✓\033[0m Removed {deleted} old entries")

        # Clean health incidents
        health_db = self.data_dir / 'health_monitor.db'
        if health_db.exists():
            print("\n\033[1;33mCleaning health incidents...\033[0m")
            deleted = self._cleanup_health_incidents(health_db, cutoff)
            results['health_incidents'] = deleted
            print(f"  \033[1;32m✓\033[0m Removed {deleted} old entries")

        print("\n\033[1;36m" + "=" * 60 + "\033[0m\n")

        return results

    def _cleanup_rag_cache(self, db_path: Path, cutoff: str) -> int:
        """Clean old RAG cache entries"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM quick_responses
            WHERE created_at < ? AND use_count < 3
        """, (cutoff,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    def _cleanup_metrics(self, db_path: Path, cutoff: str) -> int:
        """Clean old metrics"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM query_metrics
            WHERE timestamp < ?
        """, (cutoff,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    def _cleanup_health_incidents(self, db_path: Path, cutoff: str) -> int:
        """Clean old health incidents"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM incidents
            WHERE detected_at < ? AND resolved_at IS NOT NULL
        """, (cutoff,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted


def main():
    """Run database maintenance"""
    import argparse

    parser = argparse.ArgumentParser(description='Ryx AI Database Maintenance')
    parser.add_argument('action', choices=['analyze', 'optimize', 'cleanup', 'all'],
                        help='Maintenance action to perform')
    parser.add_argument('--days', type=int, default=30,
                        help='Days threshold for cleanup (default: 30)')

    args = parser.parse_args()

    maintenance = DatabaseMaintenance()

    if args.action == 'analyze':
        maintenance.analyze_all_databases()
    elif args.action == 'optimize':
        maintenance.optimize_all_databases()
    elif args.action == 'cleanup':
        maintenance.cleanup_old_data(args.days)
    elif args.action == 'all':
        maintenance.analyze_all_databases()
        maintenance.cleanup_old_data(args.days)
        maintenance.optimize_all_databases()


if __name__ == "__main__":
    main()
