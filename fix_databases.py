#!/usr/bin/env python3
"""
Ryx AI Database Fix Script
Fixes schema mismatches and rebuilds corrupted databases
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

def backup_database(db_path: Path) -> Path:
    """Create a backup of a database file"""
    if not db_path.exists():
        print(f"  Database {db_path.name} does not exist, skipping backup")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    print(f"  ✓ Backed up to {backup_path.name}")
    return backup_path

def check_table_schema(db_path: Path, table_name: str, expected_columns: list) -> bool:
    """Check if a table has the expected columns"""
    if not db_path.exists():
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        # Check if all expected columns exist
        return all(col in columns for col in expected_columns)
    except sqlite3.Error as e:
        print(f"  Error checking schema: {e}")
        return False

def fix_meta_learning_db():
    """Fix meta_learning.db schema if needed"""
    print("\n[1] Checking meta_learning.db...")
    db_path = Path("/home/user/ryx-ai/data/meta_learning.db")

    # Expected schema for preferences table
    expected_columns = ["category", "value", "confidence", "learned_from", "learned_at", "times_applied"]

    if not db_path.exists():
        print(f"  Database does not exist, will be created on first use")
        return True

    is_valid = check_table_schema(db_path, "preferences", expected_columns)

    if is_valid:
        print(f"  ✓ Schema is valid, no fix needed")
        return True

    print(f"  ✗ Schema mismatch detected, rebuilding database...")
    backup_database(db_path)
    db_path.unlink()
    print(f"  ✓ Old database removed, will be recreated with correct schema")
    return True

def fix_rag_knowledge_db():
    """Fix rag_knowledge.db if needed"""
    print("\n[2] Checking rag_knowledge.db...")
    db_path = Path("/home/user/ryx-ai/data/rag_knowledge.db")

    expected_columns = ["prompt_hash", "response", "model_used", "use_count", "created_at", "last_used", "ttl_seconds"]

    if not db_path.exists():
        print(f"  Database does not exist, will be created on first use")
        return True

    is_valid = check_table_schema(db_path, "quick_responses", expected_columns)

    if is_valid:
        print(f"  ✓ Schema is valid, no fix needed")
        return True

    print(f"  ✗ Schema mismatch detected, rebuilding database...")
    backup_database(db_path)
    db_path.unlink()
    print(f"  ✓ Old database removed, will be recreated with correct schema")
    return True

def fix_health_monitor_db():
    """Fix health_monitor.db if needed"""
    print("\n[3] Checking health_monitor.db...")
    db_path = Path("/home/user/ryx-ai/data/health_monitor.db")

    if not db_path.exists():
        print(f"  Database does not exist, will be created on first use")
        return True

    # Health monitor can recreate itself safely
    print(f"  ✓ Exists, assuming valid")
    return True

def fix_task_manager_db():
    """Fix task_manager.db if needed"""
    print("\n[4] Checking task_manager.db...")
    db_path = Path("/home/user/ryx-ai/data/task_manager.db")

    if not db_path.exists():
        print(f"  Database does not exist, will be created on first use")
        return True

    print(f"  ✓ Exists, assuming valid")
    return True

def fix_model_performance_db():
    """Fix model_performance.db if needed"""
    print("\n[5] Checking model_performance.db...")
    db_path = Path("/home/user/ryx-ai/data/model_performance.db")

    if not db_path.exists():
        print(f"  Database does not exist, will be created on first use")
        return True

    print(f"  ✓ Exists, assuming valid")
    return True

def main():
    print("=" * 60)
    print("Ryx AI Database Fix Script")
    print("=" * 60)
    print("\nThis script will check and fix database schema mismatches.")
    print("Old databases will be backed up before removal.")

    results = []
    results.append(("meta_learning.db", fix_meta_learning_db()))
    results.append(("rag_knowledge.db", fix_rag_knowledge_db()))
    results.append(("health_monitor.db", fix_health_monitor_db()))
    results.append(("task_manager.db", fix_task_manager_db()))
    results.append(("model_performance.db", fix_model_performance_db()))

    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for db_name, success in results:
        status = "✓ OK" if success else "✗ FAILED"
        print(f"  {status}: {db_name}")

    all_ok = all(success for _, success in results)
    if all_ok:
        print("\n✓ All databases are ready!")
        print("\nNext step: Install dependencies with:")
        print("  pip install -r requirements.txt")
    else:
        print("\n✗ Some databases had issues. Please check the logs above.")

    return 0 if all_ok else 1

if __name__ == "__main__":
    exit(main())
