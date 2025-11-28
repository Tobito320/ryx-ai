"""
Ryx AI - Cleanup Manager
Handles cache optimization, cleanup, and automatic maintenance
"""

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging
from core.paths import get_project_root, get_data_dir, get_config_dir, get_runtime_dir

logger = logging.getLogger(__name__)


class CleanupManager:
    """
    Manages cleanup and optimization of Ryx AI

    Features:
    - Cache optimization (remove old/unused entries)
    - Database vacuuming
    - Log rotation
    - Temporary file cleanup
    - Automatic cleanup scheduling
    - Docker cleanup integration
    """

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or get_project_root()
        self.data_dir = self.project_root / "data"
        self.cache_dir = Path.home() / ".cache" / "ryx-ai"
        self.log_dir = self.project_root / "logs"

    def cleanup_all(self, aggressive: bool = False) -> Dict[str, Any]:
        """
        Run complete cleanup

        Args:
            aggressive: If True, removes more data (be careful!)

        Returns:
            Dict with cleanup statistics
        """
        stats = {
            'cache_cleaned': 0,
            'databases_optimized': 0,
            'logs_rotated': 0,
            'temp_files_removed': 0,
            'space_freed_mb': 0,
            'errors': []
        }

        logger.info("Starting comprehensive cleanup...")

        # Clean caches
        try:
            cache_result = self.cleanup_caches(aggressive=aggressive)
            stats['cache_cleaned'] = cache_result['entries_removed']
            stats['space_freed_mb'] += cache_result['space_freed_mb']
        except Exception as e:
            stats['errors'].append(f"Cache cleanup failed: {e}")
            logger.error(f"Cache cleanup failed: {e}")

        # Optimize databases
        try:
            db_result = self.optimize_databases()
            stats['databases_optimized'] = db_result['databases_optimized']
            stats['space_freed_mb'] += db_result['space_freed_mb']
        except Exception as e:
            stats['errors'].append(f"Database optimization failed: {e}")
            logger.error(f"Database optimization failed: {e}")

        # Rotate logs
        try:
            log_result = self.rotate_logs(keep_days=30)
            stats['logs_rotated'] = log_result['logs_rotated']
            stats['space_freed_mb'] += log_result['space_freed_mb']
        except Exception as e:
            stats['errors'].append(f"Log rotation failed: {e}")
            logger.error(f"Log rotation failed: {e}")

        # Clean temp files
        try:
            temp_result = self.cleanup_temp_files()
            stats['temp_files_removed'] = temp_result['files_removed']
            stats['space_freed_mb'] += temp_result['space_freed_mb']
        except Exception as e:
            stats['errors'].append(f"Temp cleanup failed: {e}")
            logger.error(f"Temp cleanup failed: {e}")

        logger.info(f"Cleanup complete: {stats['space_freed_mb']:.2f}MB freed")
        return stats

    def cleanup_caches(self, aggressive: bool = False) -> Dict[str, Any]:
        """
        Clean up cache databases

        Args:
            aggressive: Remove more entries (older than 7 days vs 30 days)

        Returns:
            Cleanup statistics
        """
        stats = {
            'entries_removed': 0,
            'space_freed_mb': 0,
            'databases_cleaned': []
        }

        # Determine age threshold
        days = 7 if aggressive else 30
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        # Clean RAG cache
        rag_db = self.data_dir / "rag_knowledge.db"
        if rag_db.exists():
            size_before = rag_db.stat().st_size

            conn = sqlite3.connect(rag_db)
            cursor = conn.cursor()

            # Remove old cached responses with low use count
            cursor.execute("""
                DELETE FROM quick_responses
                WHERE created_at < ? AND use_count < 3
            """, (cutoff,))
            removed = cursor.rowcount
            stats['entries_removed'] += removed

            # Remove old knowledge entries
            cursor.execute("""
                DELETE FROM knowledge
                WHERE last_accessed < ? AND access_count < 2
            """, (cutoff,))
            stats['entries_removed'] += cursor.rowcount

            conn.commit()
            conn.close()

            # Calculate space freed
            size_after = rag_db.stat().st_size
            stats['space_freed_mb'] += (size_before - size_after) / (1024 * 1024)
            stats['databases_cleaned'].append('rag_knowledge.db')

        # Clean metrics database
        metrics_db = self.data_dir / "metrics.db"
        if metrics_db.exists():
            size_before = metrics_db.stat().st_size

            conn = sqlite3.connect(metrics_db)
            cursor = conn.cursor()

            # Remove old metrics
            cursor.execute("""
                DELETE FROM query_metrics
                WHERE timestamp < ?
            """, (cutoff,))
            stats['entries_removed'] += cursor.rowcount

            cursor.execute("""
                DELETE FROM resource_snapshots
                WHERE timestamp < ?
            """, (cutoff,))
            stats['entries_removed'] += cursor.rowcount

            conn.commit()
            conn.close()

            size_after = metrics_db.stat().st_size
            stats['space_freed_mb'] += (size_before - size_after) / (1024 * 1024)
            stats['databases_cleaned'].append('metrics.db')

        return stats

    def optimize_databases(self) -> Dict[str, Any]:
        """
        Vacuum and optimize all databases

        Returns:
            Optimization statistics
        """
        stats = {
            'databases_optimized': 0,
            'space_freed_mb': 0,
            'databases': []
        }

        # Find all database files
        db_files = list(self.data_dir.glob("*.db"))

        for db_file in db_files:
            try:
                size_before = db_file.stat().st_size

                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()

                # Vacuum to reclaim space
                cursor.execute("VACUUM")

                # Analyze for query optimization
                cursor.execute("ANALYZE")

                conn.close()

                size_after = db_file.stat().st_size
                freed = (size_before - size_after) / (1024 * 1024)

                stats['databases_optimized'] += 1
                stats['space_freed_mb'] += freed
                stats['databases'].append({
                    'name': db_file.name,
                    'freed_mb': round(freed, 2)
                })

            except Exception as e:
                logger.warning(f"Failed to optimize {db_file.name}: {e}")

        return stats

    def rotate_logs(self, keep_days: int = 30) -> Dict[str, Any]:
        """
        Rotate and compress old logs

        Args:
            keep_days: Keep logs newer than this many days

        Returns:
            Rotation statistics
        """
        stats = {
            'logs_rotated': 0,
            'space_freed_mb': 0,
            'log_files': []
        }

        if not self.log_dir.exists():
            return stats

        cutoff_time = datetime.now() - timedelta(days=keep_days)

        for log_file in self.log_dir.glob("*.log"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)

                if mtime < cutoff_time:
                    size = log_file.stat().st_size
                    log_file.unlink()

                    stats['logs_rotated'] += 1
                    stats['space_freed_mb'] += size / (1024 * 1024)
                    stats['log_files'].append(log_file.name)

            except Exception as e:
                logger.warning(f"Failed to rotate {log_file.name}: {e}")

        return stats

    def cleanup_temp_files(self) -> Dict[str, Any]:
        """
        Remove temporary files and caches

        Returns:
            Cleanup statistics
        """
        stats = {
            'files_removed': 0,
            'space_freed_mb': 0,
            'paths_cleaned': []
        }

        # Python cache
        pycache_dirs = list(self.project_root.rglob("__pycache__"))
        for cache_dir in pycache_dirs:
            try:
                size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
                shutil.rmtree(cache_dir)

                stats['files_removed'] += 1
                stats['space_freed_mb'] += size / (1024 * 1024)
                stats['paths_cleaned'].append(str(cache_dir))

            except Exception as e:
                logger.warning(f"Failed to remove {cache_dir}: {e}")

        # .pyc files
        pyc_files = list(self.project_root.rglob("*.pyc"))
        for pyc_file in pyc_files:
            try:
                size = pyc_file.stat().st_size
                pyc_file.unlink()

                stats['files_removed'] += 1
                stats['space_freed_mb'] += size / (1024 * 1024)

            except Exception as e:
                logger.warning(f"Failed to remove {pyc_file}: {e}")

        # Cache directory
        if self.cache_dir.exists():
            try:
                size = sum(f.stat().st_size for f in self.cache_dir.rglob("*") if f.is_file())
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)

                stats['files_removed'] += 1
                stats['space_freed_mb'] += size / (1024 * 1024)
                stats['paths_cleaned'].append(str(self.cache_dir))

            except Exception as e:
                logger.warning(f"Failed to clean cache dir: {e}")

        return stats

    def cleanup_docker(self) -> Dict[str, Any]:
        """
        Clean up Docker resources (if Docker is available)

        Returns:
            Cleanup statistics
        """
        stats = {
            'containers_removed': 0,
            'images_removed': 0,
            'volumes_removed': 0,
            'space_freed_mb': 0,
            'success': False
        }

        try:
            import subprocess

            # Check if docker is available
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                timeout=5
            )

            if result.returncode != 0:
                return stats

            # Remove stopped containers
            result = subprocess.run(
                ["docker", "container", "prune", "-f"],
                capture_output=True,
                timeout=30
            )

            # Remove unused images
            result = subprocess.run(
                ["docker", "image", "prune", "-a", "-f"],
                capture_output=True,
                timeout=30
            )

            # Remove unused volumes
            result = subprocess.run(
                ["docker", "volume", "prune", "-f"],
                capture_output=True,
                timeout=30
            )

            # Get disk usage
            result = subprocess.run(
                ["docker", "system", "df"],
                capture_output=True,
                timeout=10,
                text=True
            )

            stats['success'] = True

        except FileNotFoundError:
            logger.info("Docker not available, skipping Docker cleanup")
        except Exception as e:
            logger.warning(f"Docker cleanup failed: {e}")

        return stats

    def get_disk_usage(self) -> Dict[str, Any]:
        """
        Get disk usage statistics for Ryx AI

        Returns:
            Disk usage info
        """
        usage = {
            'total_mb': 0,
            'databases_mb': 0,
            'logs_mb': 0,
            'cache_mb': 0,
            'breakdown': {}
        }

        # Calculate database sizes
        if self.data_dir.exists():
            for db_file in self.data_dir.glob("*.db"):
                size_mb = db_file.stat().st_size / (1024 * 1024)
                usage['databases_mb'] += size_mb
                usage['breakdown'][db_file.name] = round(size_mb, 2)

        # Calculate log sizes
        if self.log_dir.exists():
            log_size = sum(f.stat().st_size for f in self.log_dir.rglob("*") if f.is_file())
            usage['logs_mb'] = log_size / (1024 * 1024)

        # Calculate cache sizes
        if self.cache_dir.exists():
            cache_size = sum(f.stat().st_size for f in self.cache_dir.rglob("*") if f.is_file())
            usage['cache_mb'] = cache_size / (1024 * 1024)

        usage['total_mb'] = usage['databases_mb'] + usage['logs_mb'] + usage['cache_mb']

        return usage

    def schedule_automatic_cleanup(self, days_interval: int = 7) -> bool:
        """
        Schedule automatic cleanup using cron (Linux)

        Args:
            days_interval: Run cleanup every N days

        Returns:
            Success status
        """
        try:
            import subprocess

            # Create cleanup script
            cleanup_script = self.project_root / "scripts" / "auto_cleanup.sh"
            cleanup_script.parent.mkdir(parents=True, exist_ok=True)

            script_content = f"""#!/bin/bash
# Auto-generated Ryx AI cleanup script

cd {self.project_root}
source .venv/bin/activate
python -c "from core.cleanup_manager import CleanupManager; CleanupManager().cleanup_all()" >> {self.log_dir}/cleanup.log 2>&1
"""

            cleanup_script.write_text(script_content)
            cleanup_script.chmod(0o755)

            logger.info(f"Cleanup script created at {cleanup_script}")
            logger.info(f"To enable automatic cleanup, add to crontab:")
            logger.info(f"0 2 */{days_interval} * * {cleanup_script}")

            return True

        except Exception as e:
            logger.error(f"Failed to schedule automatic cleanup: {e}")
            return False

    def format_cleanup_report(self, stats: Dict[str, Any]) -> str:
        """Format cleanup statistics for display"""
        lines = []
        lines.append("")
        lines.append("\033[1;36m╭──────────────────────────────────────────╮\033[0m")
        lines.append("\033[1;36m│  Cleanup Report                          │\033[0m")
        lines.append("\033[1;36m╰──────────────────────────────────────────╯\033[0m")
        lines.append("")

        lines.append(f"  \033[1;32m✓\033[0m Cache entries removed: {stats['cache_cleaned']}")
        lines.append(f"  \033[1;32m✓\033[0m Databases optimized: {stats['databases_optimized']}")
        lines.append(f"  \033[1;32m✓\033[0m Logs rotated: {stats['logs_rotated']}")
        lines.append(f"  \033[1;32m✓\033[0m Temp files removed: {stats['temp_files_removed']}")
        lines.append("")
        lines.append(f"  \033[1;33mTotal space freed:\033[0m {stats['space_freed_mb']:.2f} MB")

        if stats['errors']:
            lines.append("")
            lines.append("  \033[1;31mErrors:\033[0m")
            for error in stats['errors']:
                lines.append(f"    • {error}")

        lines.append("")
        return "\n".join(lines)
