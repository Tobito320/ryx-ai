#!/usr/bin/env python3
"""
Ryx AI - Database Optimizer
Optimizes all databases with proper indexes and schema improvements
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from core.paths import get_data_dir


def optimize_rag_database():
    """Optimize RAG knowledge database"""
    db_path = get_data_dir() / "rag_knowledge.db"

    if not db_path.exists():
        print(f"⚠ RAG database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Optimizing RAG database...")

    # Add indexes for faster lookups
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prompt_hash ON quick_responses(prompt_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_use_count ON quick_responses(use_count DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON quick_responses(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_hash ON knowledge(query_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_type ON knowledge(file_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_count ON knowledge(access_count DESC)")
        print("  ✓ Added indexes")
    except Exception as e:
        print(f"  ⚠ Index creation failed: {e}")

    # VACUUM to reclaim space
    try:
        cursor.execute("VACUUM")
        print("  ✓ Vacuumed database")
    except Exception as e:
        print(f"  ⚠ VACUUM failed: {e}")

    # ANALYZE for query optimization
    try:
        cursor.execute("ANALYZE")
        print("  ✓ Analyzed tables")
    except Exception as e:
        print(f"  ⚠ ANALYZE failed: {e}")

    conn.commit()
    conn.close()

    # Show size
    size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"  Database size: {size_mb:.2f} MB")


def optimize_metrics_database():
    """Optimize metrics database"""
    db_path = get_data_dir() / "metrics.db"

    if not db_path.exists():
        print(f"⚠ Metrics database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\nOptimizing metrics database...")

    # Add indexes
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON query_metrics(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_type ON query_metrics(query_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_model ON query_metrics(model_used)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON resource_snapshots(timestamp DESC)")
        print("  ✓ Added indexes")
    except Exception as e:
        print(f"  ⚠ Index creation failed: {e}")

    # VACUUM
    try:
        cursor.execute("VACUUM")
        print("  ✓ Vacuumed database")
    except Exception as e:
        print(f"  ⚠ VACUUM failed: {e}")

    # ANALYZE
    try:
        cursor.execute("ANALYZE")
        print("  ✓ Analyzed tables")
    except Exception as e:
        print(f"  ⚠ ANALYZE failed: {e}")

    conn.commit()
    conn.close()

    size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"  Database size: {size_mb:.2f} MB")


def optimize_meta_learning_database():
    """Optimize meta learning database"""
    db_path = get_data_dir() / "meta_learning.db"

    if not db_path.exists():
        print(f"⚠ Meta learning database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\nOptimizing meta learning database...")

    # Add indexes
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pref_category ON preferences(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pref_confidence ON preferences(confidence DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_model ON interactions(model_used)")
        print("  ✓ Added indexes")
    except Exception as e:
        print(f"  ⚠ Index creation failed: {e}")

    # VACUUM
    try:
        cursor.execute("VACUUM")
        print("  ✓ Vacuumed database")
    except Exception as e:
        print(f"  ⚠ VACUUM failed: {e}")

    # ANALYZE
    try:
        cursor.execute("ANALYZE")
        print("  ✓ Analyzed tables")
    except Exception as e:
        print(f"  ⚠ ANALYZE failed: {e}")

    conn.commit()
    conn.close()

    size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"  Database size: {size_mb:.2f} MB")


def optimize_all_databases():
    """Optimize all Ryx AI databases"""
    print("=" * 50)
    print("Ryx AI - Database Optimization")
    print("=" * 50)
    print()

    optimize_rag_database()
    optimize_metrics_database()
    optimize_meta_learning_database()

    print()
    print("=" * 50)
    print("✓ All databases optimized")
    print("=" * 50)


if __name__ == "__main__":
    optimize_all_databases()
