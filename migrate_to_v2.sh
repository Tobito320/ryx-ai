#!/bin/bash
# Ryx AI - Migration to V2
# Safely upgrades from V1 to V2 with full backup

set -e

echo "🚀 Ryx AI V2 Migration"
echo "====================="
echo ""

RYX_DIR="$HOME/ryx-ai"
BACKUP_DIR="$HOME/ryx-ai.backup.$(date +%s)"

# Check if Ryx exists
if [ ! -d "$RYX_DIR" ]; then
    echo "❌ Ryx AI not found at $RYX_DIR"
    echo "Install fresh with: git clone ... or setup script"
    exit 1
fi

echo "📦 Step 1: Backing up current system"
echo "======================================"
echo "Backup location: $BACKUP_DIR"
echo ""

cp -r "$RYX_DIR" "$BACKUP_DIR"
echo "✅ Backup complete"
echo ""

echo "📥 Step 2: Verifying new components"
echo "===================================="
echo ""

# Check new core components
components=(
    "core/model_orchestrator.py"
    "core/meta_learner.py"
    "core/health_monitor.py"
    "core/task_manager.py"
)

for component in "${components[@]}"; do
    if [ -f "$RYX_DIR/$component" ]; then
        echo "✅ $component"
    else
        echo "❌ Missing: $component"
        echo "Restore from backup: mv $BACKUP_DIR $RYX_DIR"
        exit 1
    fi
done

echo ""
echo "✅ All new components present"
echo ""

echo "🗄️  Step 3: Setting up databases"
echo "================================"
echo ""

# Create database directories
mkdir -p "$RYX_DIR/data"

# Initialize new databases
cd "$RYX_DIR"

# Model performance database
python3 << 'EOF'
import sqlite3
from pathlib import Path

db_path = Path.home() / "ryx-ai" / "data" / "model_performance.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_performance (
        model_name TEXT PRIMARY KEY,
        total_queries INTEGER DEFAULT 0,
        successful_queries INTEGER DEFAULT 0,
        failed_queries INTEGER DEFAULT 0,
        avg_latency_ms REAL DEFAULT 0.0,
        total_latency_ms REAL DEFAULT 0.0,
        last_used TEXT,
        complexity_data TEXT
    )
""")

conn.commit()
conn.close()
print("✅ Model performance database initialized")
EOF

# Meta learning database
python3 << 'EOF'
import sqlite3
from pathlib import Path

db_path = Path.home() / "ryx-ai" / "data" / "meta_learning.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

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
print("✅ Meta learning database initialized")
EOF

# Health monitor database
python3 << 'EOF'
import sqlite3
from pathlib import Path

db_path = Path.home() / "ryx-ai" / "data" / "health_monitor.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS health_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        component TEXT NOT NULL,
        status TEXT NOT NULL,
        message TEXT,
        timestamp TEXT NOT NULL,
        details TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        incident_id TEXT PRIMARY KEY,
        component TEXT NOT NULL,
        severity TEXT NOT NULL,
        description TEXT,
        detected_at TEXT NOT NULL,
        resolved_at TEXT,
        auto_fixed INTEGER DEFAULT 0,
        fix_attempts INTEGER DEFAULT 0,
        resolution TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS resource_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        cpu_percent REAL,
        memory_percent REAL,
        disk_percent REAL,
        vram_used_mb INTEGER,
        ollama_responsive INTEGER
    )
""")

conn.commit()
conn.close()
print("✅ Health monitor database initialized")
EOF

# Task manager database
python3 << 'EOF'
import sqlite3
from pathlib import Path

db_path = Path.home() / "ryx-ai" / "data" / "task_manager.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        description TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        started_at TEXT,
        completed_at TEXT,
        paused_at TEXT,
        current_step_index INTEGER DEFAULT 0,
        metadata TEXT,
        result TEXT,
        error TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        step_id TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT,
        completed_at TEXT,
        result TEXT,
        error TEXT,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id)
    )
""")

conn.commit()
conn.close()
print("✅ Task manager database initialized")
EOF

echo ""
echo "✅ All databases initialized"
echo ""

echo "🤖 Step 4: Installing AI models"
echo "================================"
echo ""

# Check if install_models.sh exists
if [ -f "$RYX_DIR/install_models.sh" ]; then
    bash "$RYX_DIR/install_models.sh"
else
    echo "⚠️  install_models.sh not found"
    echo "You can install models manually later with:"
    echo "  ollama pull qwen2.5:1.5b"
    echo "  ollama pull deepseek-coder:6.7b"
    echo "  ollama pull qwen2.5-coder:14b"
fi

echo ""
echo "🧪 Step 5: Testing V2 System"
echo "============================="
echo ""

# Test import
python3 << 'EOF'
try:
    from core.model_orchestrator import ModelOrchestrator
    from core.meta_learner import MetaLearner
    from core.health_monitor import HealthMonitor
    from core.task_manager import TaskManager
    from core.ai_engine import AIEngine
    print("✅ All V2 components import successfully")
except Exception as e:
    print(f"❌ Import error: {e}")
    exit(1)
EOF

echo ""

# Test AI Engine initialization
python3 << 'EOF'
try:
    from core.ai_engine import AIEngine
    engine = AIEngine()
    print("✅ AI Engine initializes successfully")

    # Test health check
    status = engine.get_status()
    print(f"✅ System status: {status['health']['overall_status']}")

    # Cleanup
    engine.cleanup()
except Exception as e:
    print(f"❌ Initialization error: {e}")
    exit(1)
EOF

echo ""
echo "✅ V2 Migration Complete!"
echo ""
echo "========================="
echo "What's New in V2:"
echo "========================="
echo ""
echo "1. 🤖 Model Orchestrator"
echo "   - Lazy loading (only 1.5B on startup)"
echo "   - Dynamic model selection"
echo "   - Auto-unload after 5min idle"
echo ""
echo "2. 🧠 Meta Learner"
echo "   - Learns your preferences (editor, shell, etc.)"
echo "   - Auto-applies preferences"
echo "   - Pattern recognition"
echo ""
echo "3. 🏥 Health Monitor"
echo "   - Continuous monitoring"
echo "   - Auto-healing (Ollama 404, DB issues, etc.)"
echo "   - Incident tracking"
echo ""
echo "4. 📋 Task Manager"
echo "   - State persistence"
echo "   - Graceful Ctrl+C handling"
echo "   - Resume interrupted tasks"
echo ""
echo "5. 🚀 Enhanced RAG System"
echo "   - Fixed stats bug"
echo "   - Semantic similarity matching"
echo "   - Better caching"
echo ""
echo "========================="
echo "New Commands:"
echo "========================="
echo ""
echo "  ryx ::health       - Show system health"
echo "  ryx ::status       - Show comprehensive status"
echo "  ryx ::models       - Show loaded models"
echo "  ryx ::preferences  - Show learned preferences"
echo "  ryx ::resume       - Resume paused task"
echo ""
echo "========================="
echo ""
echo "🎉 You're all set! Try: ryx ::status"
echo ""
echo "Backup saved at: $BACKUP_DIR"
echo "Remove backup: rm -rf $BACKUP_DIR"
echo ""
