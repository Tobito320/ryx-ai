"""
Ryx AI - Cache Validation and Health Check System
Automatically checks, validates, and corrects the RAG knowledge cache
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from core.paths import get_project_root, get_data_dir


class CacheValidator:
    """
    Validates and corrects RAG cache entries

    Features:
    - Checks cache health and accuracy
    - Validates file locations still exist
    - Detects and removes stale entries
    - Fixes incorrect cached responses
    - Reports cache statistics
    """

    def __init__(self):
        self.db_path = get_data_dir() / "rag_knowledge.db"
        self.issues_found = []
        self.fixes_applied = []

    def validate_all(self, auto_fix: bool = True, verbose: bool = True) -> Dict:
        """
        Run complete cache validation

        Returns:
            {
                "total_entries": int,
                "issues_found": int,
                "fixes_applied": int,
                "cache_health": float (0-1),
                "issues": list,
                "fixes": list
            }
        """
        if verbose:
            self._print_header()

        results = {
            "total_entries": 0,
            "issues_found": 0,
            "fixes_applied": 0,
            "cache_health": 1.0,
            "issues": [],
            "fixes": []
        }

        # 1. Check database exists
        if not self.db_path.exists():
            if verbose:
                print(f"\033[1;33m⚠\033[0m No cache database found at {self.db_path}")
            return results

        conn = sqlite3.connect(self.db_path)

        # 2. Validate file_knowledge table
        file_results = self._validate_file_knowledge(conn, auto_fix, verbose)
        results["total_entries"] += file_results["total"]
        results["issues_found"] += file_results["issues"]
        results["fixes_applied"] += file_results["fixes"]
        results["issues"].extend(file_results["issue_list"])
        results["fixes"].extend(file_results["fix_list"])

        # 3. Validate knowledge table (cached file locations)
        knowledge_results = self._validate_knowledge(conn, auto_fix, verbose)
        results["total_entries"] += knowledge_results["total"]
        results["issues_found"] += knowledge_results["issues"]
        results["fixes_applied"] += knowledge_results["fixes"]
        results["issues"].extend(knowledge_results["issue_list"])
        results["fixes"].extend(knowledge_results["fix_list"])

        # 4. Validate quick_responses cache
        quick_results = self._validate_quick_responses(conn, auto_fix, verbose)
        results["total_entries"] += quick_results["total"]
        results["issues_found"] += quick_results["issues"]
        results["fixes_applied"] += quick_results["fixes"]
        results["issues"].extend(quick_results["issue_list"])
        results["fixes"].extend(quick_results["fix_list"])

        # 5. Calculate cache health score
        if results["total_entries"] > 0:
            results["cache_health"] = 1.0 - (results["issues_found"] / results["total_entries"])

        conn.close()

        if verbose:
            self._print_summary(results)

        return results

    def _validate_file_knowledge(self, conn, auto_fix: bool, verbose: bool) -> Dict:
        """Validate file_knowledge table entries"""
        cursor = conn.cursor()
        results = {"total": 0, "issues": 0, "fixes": 0, "issue_list": [], "fix_list": []}

        try:
            cursor.execute("SELECT file_path, file_type, access_count FROM file_knowledge")
            rows = cursor.fetchall()
            results["total"] = len(rows)

            if verbose and rows:
                print(f"\n\033[1;36m▸\033[0m Checking file_knowledge ({len(rows)} entries)...")

            for file_path, file_type, access_count in rows:
                # Check if file still exists
                path = Path(file_path).expanduser()
                if not path.exists():
                    issue = f"File no longer exists: {file_path}"
                    results["issues"] += 1
                    results["issue_list"].append(issue)

                    if auto_fix:
                        cursor.execute("DELETE FROM file_knowledge WHERE file_path = ?", (file_path,))
                        fix = f"Removed stale entry: {file_path}"
                        results["fixes"] += 1
                        results["fix_list"].append(fix)
                        if verbose:
                            print(f"  \033[1;33m✗\033[0m {issue}")
                            print(f"    \033[1;32m✓\033[0m {fix}")

            if auto_fix:
                conn.commit()

        except sqlite3.OperationalError:
            # Table doesn't exist yet
            pass

        return results

    def _validate_knowledge(self, conn, auto_fix: bool, verbose: bool) -> Dict:
        """Validate knowledge table (file location cache)"""
        cursor = conn.cursor()
        results = {"total": 0, "issues": 0, "fixes": 0, "issue_list": [], "fix_list": []}

        try:
            cursor.execute("SELECT query_hash, file_type, file_path, confidence FROM knowledge")
            rows = cursor.fetchall()
            results["total"] = len(rows)

            if verbose and rows:
                print(f"\n\033[1;36m▸\033[0m Checking knowledge cache ({len(rows)} entries)...")

            for query_hash, file_type, file_path, confidence in rows:
                # Check if file still exists
                path = Path(file_path).expanduser()
                if not path.exists():
                    issue = f"Cached file missing: {file_path} (type: {file_type})"
                    results["issues"] += 1
                    results["issue_list"].append(issue)

                    if auto_fix:
                        cursor.execute("DELETE FROM knowledge WHERE query_hash = ?", (query_hash,))
                        fix = f"Removed invalid cache: {file_type}"
                        results["fixes"] += 1
                        results["fix_list"].append(fix)
                        if verbose:
                            print(f"  \033[1;33m✗\033[0m {issue}")
                            print(f"    \033[1;32m✓\033[0m {fix}")

                # Check confidence is reasonable
                elif confidence < 0.5:
                    issue = f"Low confidence entry ({confidence}): {file_path}"
                    results["issues"] += 1
                    results["issue_list"].append(issue)

                    if auto_fix:
                        cursor.execute("DELETE FROM knowledge WHERE query_hash = ?", (query_hash,))
                        fix = f"Removed low-confidence entry: {file_type}"
                        results["fixes"] += 1
                        results["fix_list"].append(fix)
                        if verbose:
                            print(f"  \033[1;33m⚠\033[0m {issue}")
                            print(f"    \033[1;32m✓\033[0m {fix}")

            if auto_fix:
                conn.commit()

        except sqlite3.OperationalError:
            # Table doesn't exist yet
            pass

        return results

    def _validate_quick_responses(self, conn, auto_fix: bool, verbose: bool) -> Dict:
        """Validate quick_responses cache"""
        cursor = conn.cursor()
        results = {"total": 0, "issues": 0, "fixes": 0, "issue_list": [], "fix_list": []}

        try:
            cursor.execute("SELECT prompt_hash, created_at, ttl_seconds, use_count FROM quick_responses")
            rows = cursor.fetchall()
            results["total"] = len(rows)

            if verbose and rows:
                print(f"\n\033[1;36m▸\033[0m Checking quick_responses cache ({len(rows)} entries)...")

            now = datetime.now()

            for prompt_hash, created_at, ttl_seconds, use_count in rows:
                # Check if entry is expired
                created = datetime.fromisoformat(created_at)
                age_seconds = (now - created).total_seconds()

                if age_seconds > ttl_seconds:
                    issue = f"Expired cache entry (age: {int(age_seconds/86400)} days)"
                    results["issues"] += 1
                    results["issue_list"].append(issue)

                    if auto_fix:
                        cursor.execute("DELETE FROM quick_responses WHERE prompt_hash = ?", (prompt_hash,))
                        fix = f"Removed expired entry"
                        results["fixes"] += 1
                        results["fix_list"].append(fix)
                        if verbose:
                            print(f"  \033[1;33m⚠\033[0m {issue}")
                            print(f"    \033[1;32m✓\033[0m {fix}")

                # Check for very old unused entries
                elif use_count == 1 and age_seconds > 604800:  # 7 days, only used once
                    issue = f"Stale single-use entry (age: {int(age_seconds/86400)} days)"
                    results["issues"] += 1
                    results["issue_list"].append(issue)

                    if auto_fix:
                        cursor.execute("DELETE FROM quick_responses WHERE prompt_hash = ?", (prompt_hash,))
                        fix = f"Removed stale entry"
                        results["fixes"] += 1
                        results["fix_list"].append(fix)
                        if verbose:
                            print(f"  \033[1;33m⚠\033[0m {issue}")
                            print(f"    \033[1;32m✓\033[0m {fix}")

            if auto_fix:
                conn.commit()

        except sqlite3.OperationalError:
            # Table doesn't exist yet
            pass

        return results

    def _print_header(self):
        """Print validation header"""
        print()
        print("\033[1;36m╭──────────────────────────────────────────╮\033[0m")
        print("\033[1;36m│  🔍 Cache Validation & Health Check     │\033[0m")
        print("\033[1;36m╰──────────────────────────────────────────╯\033[0m")

    def _print_summary(self, results: Dict):
        """Print validation summary"""
        health_pct = results["cache_health"] * 100

        print()
        print("\033[1;36m" + "─" * 44 + "\033[0m")
        print("\033[1;37mValidation Summary:\033[0m")
        print(f"  Total entries:   {results['total_entries']}")
        print(f"  Issues found:    {results['issues_found']}")
        print(f"  Fixes applied:   {results['fixes_applied']}")

        # Health score with color
        if health_pct >= 90:
            color = "\033[1;32m"  # Green
            status = "Excellent"
        elif health_pct >= 75:
            color = "\033[1;33m"  # Yellow
            status = "Good"
        elif health_pct >= 50:
            color = "\033[1;31m"  # Red
            status = "Fair"
        else:
            color = "\033[1;31m"  # Red
            status = "Poor"

        print(f"  Cache health:    {color}{health_pct:.1f}% ({status})\033[0m")
        print("\033[1;36m" + "─" * 44 + "\033[0m")

        if results["cache_health"] >= 0.9:
            print(f"\n\033[1;32m✓\033[0m Cache is healthy!")
        elif results["cache_health"] >= 0.75:
            print(f"\n\033[1;33m⚠\033[0m Cache has some issues but is mostly functional")
        else:
            print(f"\n\033[1;31m✗\033[0m Cache needs attention")

        print()

    def get_statistics(self) -> Dict:
        """Get cache statistics"""
        if not self.db_path.exists():
            return {"error": "No cache database found"}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        stats = {}

        # File knowledge stats
        try:
            cursor.execute("SELECT COUNT(*), AVG(access_count) FROM file_knowledge")
            count, avg_access = cursor.fetchone()
            stats["file_knowledge"] = {
                "count": count or 0,
                "avg_access": round(avg_access or 0, 2)
            }
        except:
            stats["file_knowledge"] = {"count": 0, "avg_access": 0}

        # Knowledge cache stats
        try:
            cursor.execute("SELECT COUNT(*), AVG(confidence) FROM knowledge")
            count, avg_conf = cursor.fetchone()
            stats["knowledge_cache"] = {
                "count": count or 0,
                "avg_confidence": round(avg_conf or 0, 2)
            }
        except:
            stats["knowledge_cache"] = {"count": 0, "avg_confidence": 0}

        # Quick responses stats
        try:
            cursor.execute("SELECT COUNT(*), AVG(use_count), SUM(use_count) FROM quick_responses")
            count, avg_use, total_hits = cursor.fetchone()
            stats["quick_responses"] = {
                "count": count or 0,
                "avg_use": round(avg_use or 0, 2),
                "total_hits": total_hits or 0
            }
        except:
            stats["quick_responses"] = {"count": 0, "avg_use": 0, "total_hits": 0}

        conn.close()
        return stats


def run_cache_check(auto_fix: bool = True, verbose: bool = True):
    """Convenience function to run cache validation"""
    validator = CacheValidator()
    return validator.validate_all(auto_fix=auto_fix, verbose=verbose)


def show_cache_stats():
    """Show cache statistics"""
    validator = CacheValidator()
    stats = validator.get_statistics()

    print()
    print("\033[1;36m╭──────────────────────────────────────────╮\033[0m")
    print("\033[1;36m│  📊 Cache Statistics                    │\033[0m")
    print("\033[1;36m╰──────────────────────────────────────────╯\033[0m")
    print()

    if "error" in stats:
        print(f"\033[1;31m✗\033[0m {stats['error']}")
        return

    # File Knowledge
    print("\033[1;37mFile Knowledge:\033[0m")
    print(f"  Cached files:    {stats['file_knowledge']['count']}")
    print(f"  Avg access:      {stats['file_knowledge']['avg_access']}")
    print()

    # Knowledge Cache
    print("\033[1;37mLocation Cache:\033[0m")
    print(f"  Cached locations: {stats['knowledge_cache']['count']}")
    print(f"  Avg confidence:   {stats['knowledge_cache']['avg_confidence']:.2f}")
    print()

    # Quick Responses
    print("\033[1;37mQuick Responses:\033[0m")
    print(f"  Cached responses: {stats['quick_responses']['count']}")
    print(f"  Avg use count:    {stats['quick_responses']['avg_use']}")
    print(f"  Total cache hits: {stats['quick_responses']['total_hits']}")
    print()
